from __future__ import annotations

import tkinter as tk

from ads1292_studio.gui_state import format_log_entries


def log_tab_is_visible(*, selected_workspace_tab: str, log_tab: object | None) -> bool:
    return log_tab is not None and selected_workspace_tab == str(log_tab)


def trim_log_text(log_text: tk.Text, *, max_lines: int) -> None:
    line_count = int(log_text.index("end-1c").split(".", maxsplit=1)[0])
    if line_count <= max_lines:
        return
    log_text.delete("1.0", f"{line_count - max_lines + 1}.0")


def append_log_messages(
    log_text: tk.Text,
    messages: tuple[str, ...],
    *,
    stamp: str,
    max_lines: int,
    autoscroll: bool,
) -> None:
    if not messages:
        return
    log_text.insert(tk.END, format_log_entries(messages, stamp))
    trim_log_text(log_text, max_lines=max_lines)
    if autoscroll:
        log_text.see(tk.END)
