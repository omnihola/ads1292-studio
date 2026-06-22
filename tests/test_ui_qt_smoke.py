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
