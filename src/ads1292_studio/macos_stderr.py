from __future__ import annotations

import atexit
from dataclasses import dataclass
import os
import sys
import threading


MACOS_GUI_NOISE_MARKERS = (
    "IMKCFRunLoopWakeUpReliable",
    "TISFileInterrogator updateSystemInputSources",
    "com.apple.hiservices-xpcservice",
    "Error received in message reply handler: Connection invalid",
    "Keyboard Layouts: duplicate keyboard layout identifier",
    "Keyboard Layouts: keyboard layout identifier",
    "scheduleApplicationNotification(LSNotificationCode, NSWorkspaceNotificationCenter *)",
    # benign Qt warning emitted when pyqtgraph imports (QStyleHints theme probe)
    "QObject::connect(QStyleHints",
)
SHOW_IMK_WARNINGS_ENV = "ADS1292_STUDIO_SHOW_IMK_WARNINGS"

_active_filter: StderrLineFilter | None = None


def should_suppress_stderr_line(line: str) -> bool:
    return any(marker in line for marker in MACOS_GUI_NOISE_MARKERS)


def install_macos_stderr_filter() -> StderrLineFilter | None:
    global _active_filter
    if sys.platform != "darwin" or _show_imk_warnings():
        return None
    if _active_filter is not None:
        return _active_filter
    try:
        stderr_filter = StderrLineFilter.install()
    except OSError:
        return None
    _active_filter = stderr_filter
    atexit.register(stderr_filter.restore)
    return stderr_filter


def _show_imk_warnings() -> bool:
    value = os.environ.get(SHOW_IMK_WARNINGS_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


@dataclass
class StderrLineFilter:
    read_fd: int
    original_stderr_fd: int
    thread: threading.Thread
    restored: bool = False

    @classmethod
    def install(cls) -> StderrLineFilter:
        original_stderr_fd = os.dup(2)
        read_fd, write_fd = os.pipe()
        write_fd_open = True
        try:
            os.set_inheritable(original_stderr_fd, False)
            os.set_inheritable(read_fd, False)
            os.set_inheritable(write_fd, False)
            placeholder_thread = threading.Thread()
            stderr_filter = cls(read_fd, original_stderr_fd, placeholder_thread)
            thread = threading.Thread(target=stderr_filter._forward_lines, name="ads1292-stderr-filter", daemon=True)
            stderr_filter.thread = thread
            os.dup2(write_fd, 2)
            os.close(write_fd)
            write_fd_open = False
            thread.start()
        except Exception:
            os.dup2(original_stderr_fd, 2)
            _close_fd(original_stderr_fd)
            _close_fd(read_fd)
            if write_fd_open:
                _close_fd(write_fd)
            raise
        return stderr_filter

    def restore(self) -> None:
        if self.restored:
            return
        self.restored = True
        try:
            os.dup2(self.original_stderr_fd, 2)
        finally:
            os.close(self.original_stderr_fd)

    def _forward_lines(self) -> None:
        pending = b""
        try:
            while True:
                chunk = os.read(self.read_fd, 4096)
                if not chunk:
                    break
                pending += chunk
                pending = self._flush_complete_lines(pending)
            if pending:
                self._forward_line(pending)
        except OSError:
            return
        finally:
            _close_fd(self.read_fd)

    def _flush_complete_lines(self, pending: bytes) -> bytes:
        while b"\n" in pending:
            line, pending = pending.split(b"\n", 1)
            self._forward_line(line + b"\n")
        return pending

    def _forward_line(self, line: bytes) -> None:
        text = line.decode(errors="replace")
        if should_suppress_stderr_line(text):
            return
        try:
            os.write(self.original_stderr_fd, line)
        except OSError:
            return


def _close_fd(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass
