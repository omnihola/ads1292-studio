from pathlib import Path

from ads1292_studio.events import EventMarker, event_template, read_events_json, write_events_json


def test_event_markers_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "events.json"
    events = (
        EventMarker(timestamp_seconds=1.25, label="motion", notes="arm moved"),
        EventMarker(timestamp_seconds=2.5, label="deep breath", notes="subject inhaled"),
    )

    write_events_json(path, events)
    loaded = read_events_json(path)

    assert loaded == events


def test_event_marker_normalizes_blank_fields() -> None:
    marker = EventMarker(timestamp_seconds=-1.0, label="  ", notes="  electrode touched  ").normalized()

    assert marker.timestamp_seconds == 0.0
    assert marker.label == "event"
    assert marker.notes == "electrode touched"


def test_event_template_is_immediately_writable(tmp_path: Path) -> None:
    path = tmp_path / "template.json"

    write_events_json(path, event_template())

    assert read_events_json(path)[0].label == "motion"
