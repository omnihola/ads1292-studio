"""Acquisition controller for the Qt front-end.

Owns the reused :class:`LiveWorker`, the inter-thread queues, and the
connect/start/stop/calibrate logic. UI code calls these methods and polls
:meth:`drain_results` / :meth:`drain_samples` from a QTimer — the exact
queue-drain pattern proven in the Tk app, so the threading model is unchanged.
"""
from __future__ import annotations

import queue
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ads1292_studio.calibration import Calibration
from ads1292_studio.device import Ads1x9xDevice
from ads1292_studio.gui_state import GuiState
from ads1292_studio.gui_workers import ConnectResult
from ads1292_studio.models import StreamSample, StreamStartResult
from ads1292_studio.recording_paths import recording_csv_path
from ads1292_studio.workers import AcquisitionMode, LiveWorker

MAX_SAMPLES_PER_DRAIN = 1000


@dataclass
class DrainOutcome:
    """Side effects produced by draining the result queues during one tick."""

    logs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    state_changed: bool = False


class AcquisitionController:
    def __init__(self) -> None:
        self.samples: queue.Queue[StreamSample] = queue.Queue()
        self.logs: queue.Queue[str] = queue.Queue()
        self.connect_results: queue.Queue[ConnectResult] = queue.Queue()
        self.stream_start_results: queue.Queue[StreamStartResult] = queue.Queue()
        self.worker = LiveWorker(self.samples, self.logs, self.stream_start_results)

        self.connected_port: str | None = None
        self.selected_port: str = ""
        self.recording_path: Path | None = None
        self.is_connecting = False
        self.is_starting = False
        self.is_streaming = False
        self.has_data = False

    # ---- state snapshot (drives the whole UI via gui_state) ----
    def snapshot(self) -> GuiState:
        return GuiState(
            connected=self.connected_port is not None,
            streaming=self.is_streaming,
            has_data=self.has_data,
            has_recording_path=self.recording_path is not None,
            has_port=bool(self.selected_port.strip()),
            selected_port=self.selected_port,
            connecting=self.is_connecting,
            starting=self.is_starting,
        )

    # ---- connect ----
    def connect(self, port: str) -> None:
        if self.is_connecting or not port:
            return
        self.selected_port = port
        self.is_connecting = True
        threading.Thread(target=self._connect_bg, args=(port,), daemon=True).start()

    def _connect_bg(self, port: str) -> None:
        try:
            with Ads1x9xDevice(port) as device:
                firmware = device.query_firmware()
            self.connect_results.put(ConnectResult(port=port, detail=f"firmware {firmware}"))
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            self.connect_results.put(ConnectResult(port=port, error=str(exc)))

    # ---- start / stop ----
    def start(self, port: str, *, save_csv: bool, mode: AcquisitionMode = AcquisitionMode.LIVE) -> None:
        if self.connected_port != port or self.is_streaming:
            return
        csv_path = None
        if save_csv:
            csv_path = recording_csv_path(started_at=datetime.now(), acquisition_mode=mode)
            self.recording_path = csv_path
        self.is_starting = True
        self.worker.start(port, csv_path, mode=mode, calibration=Calibration())

    def stop(self) -> None:
        self.worker.stop()
        self.is_streaming = False

    # ---- per-tick draining ----
    def drain_results(self) -> DrainOutcome:
        out = DrainOutcome()
        while True:
            try:
                msg = self.logs.get_nowait()
            except queue.Empty:
                break
            out.logs.append(msg)
        while True:
            try:
                res = self.connect_results.get_nowait()
            except queue.Empty:
                break
            self.is_connecting = False
            out.state_changed = True
            if res.error:
                self.connected_port = None
                out.errors.append(f"Connect failed: {res.error}")
            else:
                self.connected_port = res.port
                out.logs.append(f"Connected to {res.port}: {res.detail}")
        while True:
            try:
                res = self.stream_start_results.get_nowait()
            except queue.Empty:
                break
            self.is_starting = False
            out.state_changed = True
            if res.ok:
                self.is_streaming = True
            else:
                self.is_streaming = False
                out.errors.append(f"Start failed: {res.error or 'unknown error'}")
        return out

    def drain_samples(self, limit: int = MAX_SAMPLES_PER_DRAIN) -> list[StreamSample]:
        drained: list[StreamSample] = []
        for _ in range(limit):
            try:
                drained.append(self.samples.get_nowait())
            except queue.Empty:
                break
        if drained:
            self.has_data = True
        return drained
