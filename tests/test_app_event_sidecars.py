from pathlib import Path
from types import SimpleNamespace

from ads1292_studio import app as app_module
from ads1292_studio.app import App
from ads1292_studio.events import EventMarker, write_events_csv


def test_start_initializes_recording_bundle() -> None:
    import inspect

    source = inspect.getsource(App.start)

    assert "_write_current_sidecars" in source
    assert "recording_bundle_path(csv_path)" in source


def test_event_bundle_writes_use_app_sample_rate() -> None:
    import inspect

    start_source = inspect.getsource(App.start)
    save_source = inspect.getsource(App._save_event_sidecar)
    current_sidecars_source = inspect.getsource(App._write_current_sidecars)

    assert "_write_current_sidecars" in start_source
    assert "_write_current_sidecars()" in save_source
    assert "write_recording_bundle" in current_sidecars_source
    assert "sample_rate_hz=SAMPLE_RATE_HZ" in current_sidecars_source


def test_save_event_sidecar_updates_bundle_and_xlsx() -> None:
    calls = []
    fake = SimpleNamespace(
        recording_path=Path("recording.csv"),
        event_markers=(EventMarker(1.0, label="motion"),),
        _write_current_sidecars=lambda: calls.append("bundle"),
        _write_recording_xlsx_if_ready=lambda: calls.append("xlsx"),
    )

    App._save_event_sidecar(fake)

    assert calls == ["bundle", "xlsx"]


def test_save_event_sidecar_refreshes_existing_recording_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = []
    csv_path = tmp_path / "recording.csv"
    csv_path.with_suffix(".manifest.json").write_text("{}\n")

    monkeypatch.setattr(
        app_module,
        "write_recording_manifest",
        lambda path: calls.append(Path(path)) or Path(path).with_suffix(".manifest.json"),
    )
    fake = SimpleNamespace(
        recording_path=csv_path,
        event_markers=(EventMarker(1.0, label="motion"),),
        _write_current_sidecars=lambda: calls.append("bundle"),
        _write_recording_xlsx_if_ready=lambda: calls.append("xlsx"),
        _log=lambda message: calls.append(message),
    )

    App._save_event_sidecar(fake)

    assert csv_path in calls
    assert any("Recording manifest refreshed" in str(call) for call in calls)


def test_save_event_sidecar_does_not_create_manifest_before_finalization(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = []
    csv_path = tmp_path / "recording.csv"

    monkeypatch.setattr(app_module, "write_recording_manifest", lambda path: calls.append(Path(path)))
    fake = SimpleNamespace(
        recording_path=csv_path,
        event_markers=(EventMarker(1.0, label="motion"),),
        _write_current_sidecars=lambda: calls.append("bundle"),
        _write_recording_xlsx_if_ready=lambda: calls.append("xlsx"),
        _log=lambda message: calls.append(message),
    )

    App._save_event_sidecar(fake)

    assert calls == ["bundle", "xlsx"]


def test_load_event_sidecar_falls_back_to_events_csv(tmp_path: Path) -> None:
    calls = []
    csv_path = tmp_path / "recording.csv"
    write_events_csv(
        csv_path.with_suffix(".events.csv"),
        (EventMarker(2.0, duration_seconds=1.5, label="csv-only motion", notes="from spreadsheet"),),
    )
    fake = SimpleNamespace(
        event_markers=[],
        _events_path=lambda path: path.with_suffix(".events.json"),
        _events_csv_path=lambda path: path.with_suffix(".events.csv"),
        _set_event_count=lambda: calls.append("count"),
        _log=lambda message: calls.append(message),
    )

    App._load_event_sidecar(fake, csv_path)

    assert len(fake.event_markers) == 1
    assert fake.event_markers[0].label == "csv-only motion"
    assert fake.event_markers[0].duration_seconds == 1.5
    assert "count" in calls
    assert any("events CSV" in str(call) for call in calls)
