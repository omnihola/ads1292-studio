import inspect
import json
from pathlib import Path
from types import SimpleNamespace

from ads1292_studio.acquisition import build_acquisition_provenance, read_acquisition_json, write_acquisition_json
from ads1292_studio.app import App
from ads1292_studio.calibration import Calibration
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.models import StreamSample
from ads1292_studio.processing import build_processing_settings
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.recording_bundle import acquisition_from_bundle, read_recording_bundle, write_recording_bundle


def test_start_updates_acquisition_summary_when_recording_csv() -> None:
    source = inspect.getsource(App.start)

    assert "_write_current_sidecars" in source
    assert "recording_bundle_path" in source
    assert "acquisition_var.set(format_acquisition_summary" in source


def test_start_and_finalize_persist_processing_bundle() -> None:
    start_source = inspect.getsource(App.start)
    current_sidecars_source = inspect.getsource(App._write_current_sidecars)
    load_source = inspect.getsource(App._finish_csv_load)

    assert "_write_current_sidecars" in start_source
    assert "write_recording_bundle" in current_sidecars_source
    assert "processing=self._processing_settings()" in current_sidecars_source
    assert "self._load_recording_bundle(result.path)" in load_source
    assert "self._load_processing_sidecar(result.path)" in load_source


def test_finalize_recording_sidecars_uses_csv_sample_span(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    samples = tuple(
        StreamSample(
            timestamp=index / 500.0,
            ch1=0,
            ch2=1000,
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index in range(5)
    )
    write_recording_csv(csv_path, samples)
    write_acquisition_json(
        csv_path.with_suffix(".acquisition.json"),
        build_acquisition_provenance(
            csv_path=csv_path,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem214301",
            sample_rate_hz=500.0,
            calibration=Calibration(),
            live_calibration=None,
            started_at="2026-06-21T12:00:00",
        ),
    )
    logs = []
    def write_bundle(**kwargs):
        write_recording_bundle(
            csv_path,
            metadata=SessionMetadata(session_id="test"),
            events=tuple(),
            calibration=Calibration(),
            acquisition=kwargs["acquisition"],
            protocol=TestProtocol(),
            quality_gate=QualityGate(),
            processing=build_processing_settings(),
        )
        logs.append(("bundle", ""))

    fake = SimpleNamespace(
        recording_path=csv_path,
        acquisition_var=SimpleNamespace(set=lambda value: logs.append(("summary", value))),
        _acquisition_path=lambda path: path.with_suffix(".acquisition.json"),
        _acquisition_for_recording_bundle=lambda _path: build_acquisition_provenance(
            csv_path=csv_path,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem214301",
            sample_rate_hz=500.0,
            calibration=Calibration(),
            live_calibration=None,
            started_at="2026-06-21T12:00:00",
        ),
        _write_current_sidecars=write_bundle,
        _write_recording_xlsx_if_ready=lambda: logs.append(("xlsx", "")) or None,
        _log=lambda message: logs.append(("log", message)),
    )

    App._finalize_recording_sidecars(
        fake,
        ended_at="2026-06-21T12:00:02",
        finalized_at="2026-06-21T12:00:03",
    )

    loaded = acquisition_from_bundle(read_recording_bundle(csv_path))
    assert loaded.completion["status"] == "finalized"
    assert loaded.completion["sample_count"] == 5
    assert loaded.completion["first_timestamp_seconds"] == 0.0
    assert loaded.completion["last_timestamp_seconds"] == 0.008
    assert loaded.completion["sample_span_seconds"] == 0.008
    assert any(kind == "bundle" for kind, _ in logs)
    assert any(kind == "xlsx" for kind, _ in logs)
    assert any("finalized" in message for kind, message in logs if kind == "summary")


def test_finalize_recording_sidecars_creates_bundle_when_legacy_acquisition_sidecar_missing(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "recording.csv"
    write_recording_csv(
        csv_path,
        (
            StreamSample(
                timestamp=0.0,
                ch1=0,
                ch2=1000,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            ),
        ),
    )
    logs = []
    def write_bundle(**kwargs):
        write_recording_bundle(
            csv_path,
            metadata=SessionMetadata(session_id="test"),
            events=tuple(),
            calibration=Calibration(),
            acquisition=kwargs["acquisition"],
            protocol=TestProtocol(),
            quality_gate=QualityGate(),
            processing=build_processing_settings(),
        )
        logs.append(("bundle", ""))

    fake = SimpleNamespace(
        recording_path=csv_path,
        recording_finalization_pending=True,
        acquisition_var=SimpleNamespace(set=lambda value: logs.append(("summary", value))),
        _acquisition_path=lambda path: path.with_suffix(".acquisition.json"),
        _acquisition_for_recording_bundle=lambda _path: build_acquisition_provenance(
            csv_path=csv_path,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem214301",
            sample_rate_hz=500.0,
            calibration=Calibration(),
            live_calibration=None,
            started_at="2026-06-21T12:00:00",
        ),
        _write_current_sidecars=write_bundle,
        _write_recording_xlsx_if_ready=lambda: None,
        _log=lambda message: logs.append(("log", message)),
    )

    App._finalize_recording_sidecars(fake)

    assert fake.recording_finalization_pending is False
    assert acquisition_from_bundle(read_recording_bundle(csv_path)).completion["status"] == "finalized"


def test_start_finalizes_pending_previous_recording_before_reset() -> None:
    # Regression: restarting must finalize a still-pending recording first, else
    # the previous recording is orphaned (CSV + non-finalized bundle).
    source = inspect.getsource(App.start)
    assert "recording_finalization_pending" in source
    assert "_finalize_recording_sidecars()" in source
    # the finalize must happen BEFORE the state is reset to None
    assert source.index("_finalize_recording_sidecars()") < source.index("self.recording_path = None")


def test_tick_reschedules_even_on_error() -> None:
    # Regression: an exception in the tick body must not kill the polling loop.
    source = inspect.getsource(App._tick)
    assert "finally:" in source
    assert "_schedule_tick" in source
    # reschedule lives in the finally so it always runs
    assert source.index("finally:") < source.rindex("_schedule_tick")
