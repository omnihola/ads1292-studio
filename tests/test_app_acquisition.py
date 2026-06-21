import inspect
import json
from pathlib import Path
from types import SimpleNamespace

from ads1292_studio.acquisition import build_acquisition_provenance, read_acquisition_json, write_acquisition_json
from ads1292_studio.app import App
from ads1292_studio.calibration import Calibration
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.models import StreamSample


def test_start_updates_acquisition_summary_when_recording_csv() -> None:
    source = inspect.getsource(App.start)

    assert "write_acquisition_json" in source
    assert "acquisition_var.set(format_acquisition_summary" in source


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
    fake = SimpleNamespace(
        recording_path=csv_path,
        acquisition_var=SimpleNamespace(set=lambda value: logs.append(("summary", value))),
        _acquisition_path=lambda path: path.with_suffix(".acquisition.json"),
        _write_current_sidecars=lambda: logs.append(("sidecars", "")),
        _log=lambda message: logs.append(("log", message)),
    )

    App._finalize_recording_sidecars(
        fake,
        ended_at="2026-06-21T12:00:02",
        finalized_at="2026-06-21T12:00:03",
    )

    loaded = read_acquisition_json(csv_path.with_suffix(".acquisition.json"))
    assert loaded.completion["status"] == "finalized"
    assert loaded.completion["sample_count"] == 5
    assert loaded.completion["first_timestamp_seconds"] == 0.0
    assert loaded.completion["last_timestamp_seconds"] == 0.008
    assert loaded.completion["sample_span_seconds"] == 0.008
    manifest = json.loads(csv_path.with_suffix(".manifest.json").read_text())
    assert manifest["source_csv"] == "recording.csv"
    assert manifest["recording"]["sample_count"] == 5
    assert manifest["acquisition"]["completion_audit"] == "pass"
    assert any(kind == "sidecars" for kind, _ in logs)
    assert any("finalized" in message for kind, message in logs if kind == "summary")


def test_finalize_recording_sidecars_clears_pending_when_acquisition_sidecar_missing(
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
    fake = SimpleNamespace(
        recording_path=csv_path,
        recording_finalization_pending=True,
        _acquisition_path=lambda path: path.with_suffix(".acquisition.json"),
        _write_current_sidecars=lambda: logs.append(("sidecars", "")),
        _log=lambda message: logs.append(("log", message)),
    )

    App._finalize_recording_sidecars(fake)

    assert fake.recording_finalization_pending is False
    assert any("missing acquisition sidecar" in message for kind, message in logs if kind == "log")
