"""Offscreen smoke test for the PySide6 main window (Phase 44.1 MVP).

Runs headless via QT_QPA_PLATFORM=offscreen so it works in CI without a display.
Verifies the window constructs, control gating matches gui_state, and the tick
loop processes connect/start results and live samples without error.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from ads1292_studio.gui_workers import ConnectResult  # noqa: E402
from ads1292_studio.models import StreamSample, StreamStartResult  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _make_window(qapp):
    from ads1292_studio.ui_qt.main_window import MainWindow

    return MainWindow()


def test_window_constructs_with_expected_widgets(qapp) -> None:
    win = _make_window(qapp)
    try:
        for name in ("Connect", "Start", "Stop", "Calibrate Live", "Refresh"):
            assert name in win.controls, f"missing control: {name}"
        assert win.live_panel is not None
        assert win.event_console is not None
        assert win.status_panel is not None
        assert win.tabs.count() == 5
        assert win.tabs.tabText(0) == "Live ECG"
    finally:
        win.deleteLater()


def test_initial_state_disables_start_and_stop(qapp) -> None:
    win = _make_window(qapp)
    try:
        assert win.controls["Stop"].isEnabled() is False
        assert win.controls["Start"].isEnabled() is False  # not connected yet
    finally:
        win.deleteLater()


def test_connect_then_start_then_samples_flow(qapp) -> None:
    win = _make_window(qapp)
    try:
        win.controller.selected_port = "/dev/cu.usbmodemTEST"
        # simulate a successful connect result arriving on the queue
        win.controller.is_connecting = True
        win.controller.connect_results.put(ConnectResult(port="/dev/cu.usbmodemTEST", detail="firmware 1.0"))
        win._tick()
        assert win.controller.connected_port == "/dev/cu.usbmodemTEST"
        assert win.controls["Start"].isEnabled() is True
        assert win.controls["Stop"].isEnabled() is False

        # simulate the worker confirming the stream started
        win.controller.is_starting = True
        win.controller.stream_start_results.put(StreamStartResult(ok=True))
        # and a batch of live samples
        for i in range(20):
            win.controller.samples.put(
                StreamSample(
                    timestamp=float(i) / 500.0,
                    ch1=100 + i,
                    ch2=200 - i,
                    board_heart_rate=72,
                    board_respiration_rate=15,
                    status_byte=0,
                    sample_index=i,
                )
            )
        win._tick()
        assert win.controller.is_streaming is True
        assert win.controls["Stop"].isEnabled() is True
        assert len(win._ch2) == 20  # samples reached the plot buffer

        # stop returns to a connected, non-streaming state
        win._on_stop()
        assert win.controller.is_streaming is False
        assert win.controls["Stop"].isEnabled() is False
        assert win.controls["Start"].isEnabled() is True
    finally:
        win.deleteLater()


def test_connect_failure_surfaces_without_crashing(qapp) -> None:
    win = _make_window(qapp)
    try:
        win.controller.is_connecting = True
        win.controller.connect_results.put(ConnectResult(port="/dev/bad", error="no such device"))
        outcome = win.controller.drain_results()
        assert any("Connect failed" in e for e in outcome.errors)
        assert win.controller.connected_port is None
    finally:
        win.deleteLater()
