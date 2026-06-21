from pathlib import Path
from types import SimpleNamespace

from ads1292_studio import app as app_module
from ads1292_studio.app import App
from ads1292_studio.events import EventMarker


def test_start_initializes_events_csv_sidecar() -> None:
    import inspect

    source = inspect.getsource(App.start)

    assert "write_events_csv(self._events_csv_path(csv_path), self.event_markers)" in source


def test_save_event_sidecar_writes_json_and_csv(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        app_module,
        "write_events_json",
        lambda path, events: calls.append(("json", Path(path).name, tuple(events))),
    )
    monkeypatch.setattr(
        app_module,
        "write_events_csv",
        lambda path, events: calls.append(("csv", Path(path).name, tuple(events))),
        raising=False,
    )
    fake = SimpleNamespace(
        recording_path=Path("recording.csv"),
        event_markers=(EventMarker(1.0, label="motion"),),
        _events_path=lambda csv_path: csv_path.with_suffix(".events.json"),
        _events_csv_path=lambda csv_path: csv_path.with_suffix(".events.csv"),
    )

    App._save_event_sidecar(fake)

    assert ("json", "recording.events.json", fake.event_markers) in calls
    assert ("csv", "recording.events.csv", fake.event_markers) in calls
