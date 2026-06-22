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
        assert win.tabs.count() == 6
        assert win.tabs.tabText(0) == "Live ECG"
        assert "Info" in [win.tabs.tabText(i) for i in range(win.tabs.count())]
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


def test_finalize_writes_csv_json_and_xlsx(tmp_path) -> None:
    """A finalized recording produces all three artifacts (csv kept; json+xlsx added)."""
    from ads1292_studio.acquisition import build_acquisition_provenance
    from ads1292_studio.calibration import Calibration
    from ads1292_studio.csv_io import CsvRecorder
    from ads1292_studio.ui_qt.controller import AcquisitionController, DrainOutcome

    csv_path = tmp_path / "live" / "2026-06-21-000000-000000-ads1292-studio.csv"
    csv_path.parent.mkdir(parents=True)
    with CsvRecorder(csv_path) as rec:
        for i in range(60):
            rec.write(
                StreamSample(
                    timestamp=i / 500.0,
                    ch1=100 + i,
                    ch2=200 - i,
                    board_heart_rate=72,
                    board_respiration_rate=15,
                    status_byte=0,
                    sample_index=i,
                )
            )

    from ads1292_studio.events import EventMarker
    from ads1292_studio.recording_bundle import events_from_bundle, read_recording_bundle

    ctrl = AcquisitionController()
    ctrl.recording_path = csv_path
    ctrl.event_markers = [EventMarker(timestamp_seconds=0.05, label="motion", notes="step").normalized()]
    ctrl._record_provenance = build_acquisition_provenance(
        csv_path=csv_path,
        acquisition_mode="live",
        port="/dev/test",
        sample_rate_hz=500.0,
        calibration=Calibration(),
        live_calibration=None,
        started_at="2026-06-21T00:00:00",
    )
    ctrl._finalization_pending = True

    out = DrainOutcome()
    ctrl._finalize_recording(out)

    assert csv_path.exists(), "CSV kept (load-bearing for Export Package/Report)"
    assert csv_path.with_suffix(".json").exists(), "JSON bundle written"
    assert csv_path.with_suffix(".xlsx").exists(), "XLSX written"
    manifest = csv_path.with_suffix(".manifest.json")
    assert manifest.exists(), "SHA-256 manifest written"
    assert "sha256" in manifest.read_text(), "manifest carries checksums"
    assert ctrl.has_pending_recording is False
    assert any("XLSX written" in line for line in out.logs)

    # events are persisted into the JSON bundle
    bundle = read_recording_bundle(csv_path.with_suffix(".json"))
    events = events_from_bundle(bundle)
    assert len(events) == 1 and events[0].label == "motion"


def test_export_report_writes_files_from_loaded_recording(qapp, tmp_path, monkeypatch) -> None:
    """The Export Report archive action reuses the core exporter and writes output."""
    from pathlib import Path

    from PySide6.QtWidgets import QMessageBox

    from ads1292_studio.csv_io import read_recording_csv

    # archive handlers pop modal dialogs; stub them so the test does not block
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))

    src = Path("recordings/2026-06-18-221342-ads1292-studio.csv")
    if not src.exists():
        pytest.skip("baseline recording not available")

    win = _make_window(qapp)
    try:
        win.controller.loaded_samples = read_recording_csv(src).samples
        win._ECG_ROOT = tmp_path
        win._on_export_report()
        out = tmp_path / "reports"
        assert out.exists() and any(out.iterdir()), "report files were written"
    finally:
        win.deleteLater()


def test_recording_renderers_registry_renders_all_panels(qapp) -> None:
    """_show_recording drives every registered RecordingRenderer and switches to Review."""
    from pathlib import Path

    from ads1292_studio.csv_io import read_recording_csv

    src = Path("recordings/2026-06-18-221342-ads1292-studio.csv")
    if not src.exists():
        pytest.skip("baseline recording not available")

    win = _make_window(qapp)
    try:
        # every registered panel exposes the uniform interface
        for panel in win._recording_renderers:
            assert hasattr(panel, "render_recording")
        win._show_recording(read_recording_csv(src))
        assert win.tabs.tabText(win.tabs.currentIndex()) == "Review CSV"
    finally:
        win.deleteLater()


def test_sidebar_forms_build_quality_gate_and_protocol(qapp) -> None:
    from ads1292_studio.protocol import TestProtocol
    from ads1292_studio.quality_gate import QualityGate

    win = _make_window(qapp)
    try:
        gate = win.sidebar.quality_gate()
        assert isinstance(gate, QualityGate)
        assert gate.min_duration_seconds == 8.0 and gate.require_qrs_clear is True
        proto = win.sidebar.protocol()
        assert isinstance(proto, TestProtocol)
        assert len(proto.steps) == 3 and proto.name
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


def test_live_panel_set_calibration_switches_ylabel(qapp) -> None:
    from ads1292_studio.ui_qt.live_panel import LivePanel

    panel = LivePanel()
    try:
        assert "counts" in panel.ax_ecg.get_ylabel().lower()
        panel.set_calibration(2.5)
        assert "µV" in panel.ax_ecg.get_ylabel() or "uV" in panel.ax_ecg.get_ylabel()
        panel.set_calibration(None)
        assert "counts" in panel.ax_ecg.get_ylabel().lower()
    finally:
        panel.deleteLater()


def test_live_panel_update_traces_scales_by_calibration(qapp) -> None:
    from ads1292_studio.ui_qt.live_panel import LivePanel

    panel = LivePanel()
    try:
        panel.set_calibration(2.0)
        panel.update_traces([0.0, 1.0], [10.0, 20.0], [0.0, 1.0], [5.0, 15.0])
        ecg_y = panel._ecg_line.get_ydata()
        resp_y = panel._resp_line.get_ydata()
        assert list(ecg_y) == [20.0, 40.0], f"expected scaled ECG, got {ecg_y}"
        assert list(resp_y) == [10.0, 30.0], f"expected scaled resp, got {resp_y}"
    finally:
        panel.deleteLater()


def test_info_panel_shows_uv_when_calibration_set(qapp) -> None:
    from ads1292_studio.ui_qt.analysis_panels import RecordingInfoPanel
    from ads1292_studio.models import StreamSample
    import time

    panel = RecordingInfoPanel()
    samples = [
        StreamSample(timestamp=i / 500.0, ch1=100, ch2=200,
                     board_heart_rate=0, board_respiration_rate=0, status_byte=0)
        for i in range(600)
    ]
    panel.set_calibration(2.0)
    panel.render_recording(samples, 500.0)
    text = panel.toPlainText()
    assert "µV" in text, "calibrated info panel should show µV"
    assert "2.0 µV/ct" in text or "2 µV/ct" in text, "calibration factor should appear"

    panel.set_calibration(None)
    panel.render_recording(samples, 500.0)
    text2 = panel.toPlainText()
    assert "not applied" in text2, "uncalibrated panel should say 'not applied'"


def test_filter_buttons_change_hint_label(qapp) -> None:
    win = _make_window(qapp)
    try:
        assert "raw" in win._filter_hint.text()
        win._filter_btns["Notch"].setChecked(True)
        assert "Notch" in win._filter_hint.text()
        win._filter_btns["HP"].setChecked(True)
        assert "HP" in win._filter_hint.text()
        win._filter_btns["Notch"].setChecked(False)
        win._filter_btns["HP"].setChecked(False)
        assert "raw" in win._filter_hint.text()
    finally:
        win.deleteLater()


def test_filter_settings_reflected_in_current_filter_settings(qapp) -> None:
    win = _make_window(qapp)
    try:
        fs = win._current_filter_settings()
        assert not fs.notch_enabled
        assert not fs.highpass_enabled
        win._filter_btns["Notch"].setChecked(True)
        win._filter_btns["HP"].setChecked(True)
        fs2 = win._current_filter_settings()
        assert fs2.notch_enabled
        assert fs2.highpass_enabled
        assert not fs2.lowpass_enabled
        assert not fs2.bandpass_enabled
    finally:
        win.deleteLater()


def test_control_buttons_use_no_focus_to_avoid_macos_focus_glow(qapp) -> None:
    from PySide6.QtCore import Qt

    win = _make_window(qapp)
    try:
        for name in ("Connect", "Start", "Stop", "Refresh", "Calibrate Live"):
            assert win.controls[name].focusPolicy() == Qt.FocusPolicy.NoFocus, (
                f"{name} should not retain click focus (macOS focus glow)"
            )
    finally:
        win.deleteLater()


def test_disabled_start_button_is_dimmed_not_saturated_green(qapp) -> None:
    from ads1292_studio.ui_qt.theme import apply_theme

    apply_theme(qapp, "light")
    win = _make_window(qapp)
    try:
        win.show()
        qapp.processEvents()
        # streaming -> Start disabled; it must not stay the saturated 'ok' green
        win.controller.connected_port = "/dev/x"
        win.controller.is_streaming = True
        win._refresh_state()
        qapp.processEvents()
        start = win.controls["Start"]
        assert start.isEnabled() is False
        img = start.grab().toImage()
        c = img.pixelColor(img.width() // 2, img.height() // 2)
        # ok green is #2E9E6B (46,158,107). A properly disabled button must differ.
        is_green = abs(c.red() - 46) < 30 and abs(c.green() - 158) < 30 and abs(c.blue() - 107) < 30
        assert not is_green, f"disabled Start still green: #{c.red():02X}{c.green():02X}{c.blue():02X}"
    finally:
        win.deleteLater()


def test_lead_off_updates_contact_indicator_without_creating_events(qapp) -> None:
    # Lead-off is surfaced as a non-intrusive indicator only; it must NOT
    # auto-create event markers (that painted spurious yellow spans over the
    # whole recording when the board reports lead-off bits from the start).
    win = _make_window(qapp)
    try:
        n_before = len(win.controller.event_markers)
        win._sample_count = 0
        win._process_lead_off(0x00)
        assert "Contact OK" in win.event_console.contact_value.text()
        win._sample_count = 1000
        win._process_lead_off(0x02)  # RA off
        assert "RA" in win.event_console.contact_value.text()
        win._sample_count = 2000
        win._process_lead_off(0x00)  # restored
        assert "Contact OK" in win.event_console.contact_value.text()
        # no event markers were created by lead-off transitions
        assert len(win.controller.event_markers) == n_before
    finally:
        win.deleteLater()


def test_invert_ecg_button_flips_live_traces(qapp) -> None:
    from collections import deque

    win = _make_window(qapp)
    try:
        # seed the live deques with known values
        win._ch2.extend([100.0, 200.0, 300.0])
        win._ch1.extend([10.0, 20.0, 30.0])
        win._sample_count = 3
        win._invert_btn.setChecked(False)
        win._redraw_live()
        y_normal = list(win.live_panel._ecg_line.get_ydata())

        win._invert_btn.setChecked(True)
        win._redraw_live()
        y_inverted = list(win.live_panel._ecg_line.get_ydata())

        assert y_inverted == pytest.approx([-v for v in y_normal], abs=1e-6)
        assert "inv" in win._filter_hint.text()
    finally:
        win.deleteLater()


def test_main_window_calibration_syncs_to_live_panel(qapp) -> None:
    from ads1292_studio.calibration import LiveStreamCalibration

    win = _make_window(qapp)
    try:
        assert win.live_panel._uv_per_count is None
        win.controller.live_calibration = LiveStreamCalibration(
            mean_uv_per_count=3.2, std_uv_per_count=0.1, cv_percent=1.5,
            runs=5, test_signal_pp_uv=2016.7,
        )
        win._refresh_state()
        assert win.live_panel._uv_per_count == pytest.approx(3.2)
        win.controller.live_calibration = None
        win._refresh_state()
        assert win.live_panel._uv_per_count is None
    finally:
        win.deleteLater()
