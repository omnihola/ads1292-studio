from pathlib import Path
import json

from ads1292_studio.events import (
    EventMarker,
    event_from_interval,
    event_template,
    read_events_csv,
    read_events_json,
    write_events_csv,
    write_events_json,
)


def test_event_markers_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "events.json"
    events = (
        EventMarker(timestamp_seconds=1.25, label="motion", notes="arm moved"),
        EventMarker(timestamp_seconds=2.5, label="deep breath", notes="subject inhaled"),
    )

    write_events_json(path, events)
    loaded = read_events_json(path)
    data = json.loads(path.read_text())

    assert loaded == events
    assert data["schema"] == "ads1292-event-annotations-v1"
    assert data["timestamp_reference"] == "relative_seconds_from_recording_start"
    assert data["events"][0]["label"] == "motion"


def test_event_markers_json_reader_accepts_legacy_list_format(tmp_path: Path) -> None:
    path = tmp_path / "legacy.events.json"
    path.write_text(
        json.dumps(
            [
                {
                    "timestamp_seconds": 1.25,
                    "duration_seconds": 0.5,
                    "label": "legacy motion",
                    "notes": "old sidecar",
                }
            ]
        )
    )

    loaded = read_events_json(path)

    assert loaded == (
        EventMarker(
            1.25,
            duration_seconds=0.5,
            label="legacy motion",
            notes="old sidecar",
        ),
    )


def test_event_marker_supports_duration_and_end_seconds(tmp_path: Path) -> None:
    path = tmp_path / "events.json"
    events = (
        EventMarker(
            timestamp_seconds=12.0,
            duration_seconds=3.5,
            label="motion segment",
            notes="subject moved right arm",
        ),
    )

    write_events_json(path, events)
    loaded = read_events_json(path)
    data = json.loads(path.read_text())

    assert loaded[0].duration_seconds == 3.5
    assert loaded[0].end_seconds == 15.5
    assert "duration_seconds" in path.read_text()
    assert data["events"][0]["start_seconds"] == 12.0
    assert data["events"][0]["end_seconds"] == 15.5
    assert data["events"][0]["event_type"] == "interval"


def test_event_sidecars_include_sample_indices_for_reproducible_segments(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "recording.events.json"
    csv_path = tmp_path / "recording.events.csv"
    events = (
        EventMarker(
            timestamp_seconds=73.0,
            duration_seconds=4.25,
            label="artifact",
            notes="motion artifact excluded from HRV",
        ),
    )

    write_events_json(json_path, events, sample_rate_hz=500.0)
    write_events_csv(csv_path, events, sample_rate_hz=500.0)

    payload = json.loads(json_path.read_text())
    csv_text = csv_path.read_text()
    event = payload["events"][0]
    assert payload["sample_rate_hz"] == 500.0
    assert payload["sample_index_reference"] == "zero_based_sample_index_at_recording_sample_rate"
    assert event["start_sample_index"] == 36500
    assert event["end_sample_index"] == 38625
    assert event["duration_samples"] == 2125
    assert "start_sample_index,end_sample_index,duration_samples" in csv_text
    assert "36500,38625,2125" in csv_text
    assert read_events_json(json_path) == tuple(event.normalized() for event in events)
    assert read_events_csv(csv_path) == tuple(event.normalized() for event in events)


def test_events_json_reader_accepts_start_end_seconds_without_duration(tmp_path: Path) -> None:
    path = tmp_path / "edited.events.json"
    path.write_text(
        json.dumps(
            {
                "schema": "ads1292-event-annotations-v1",
                "timestamp_reference": "relative_seconds_from_recording_start",
                "events": [
                    {
                        "start_seconds": 12.0,
                        "end_seconds": 15.5,
                        "event_type": "interval",
                        "label": "motion",
                        "notes": "spreadsheet-style edit",
                    }
                ],
            }
        )
    )

    loaded = read_events_json(path)

    assert loaded == (
        EventMarker(12.0, duration_seconds=3.5, label="motion", notes="spreadsheet-style edit"),
    )


def test_event_markers_csv_round_trip_includes_start_end_duration(tmp_path: Path) -> None:
    path = tmp_path / "recording.events.csv"
    events = (
        EventMarker(
            timestamp_seconds=12.0,
            duration_seconds=3.5,
            label="motion segment",
            notes="subject moved right arm, visible artifact",
        ),
        EventMarker(timestamp_seconds=25.0, label="electrode touch", notes="adjusted LA"),
    )

    write_events_csv(path, events)
    loaded = read_events_csv(path)
    text = path.read_text()

    assert loaded == tuple(event.normalized() for event in events)
    assert (
        "start_seconds,end_seconds,duration_seconds,start_sample_index,end_sample_index,duration_samples,event_type,label,notes"
        in text
    )
    assert "6000,7750,1750" in text
    assert "15.500000" in text
    assert ",interval,motion segment," in text
    assert ",point,electrode touch," in text
    assert "motion segment" in text


def test_events_csv_reader_accepts_start_end_seconds_without_duration(tmp_path: Path) -> None:
    path = tmp_path / "edited.events.csv"
    path.write_text(
        "start_seconds,end_seconds,event_type,label,notes\n"
        "12.000000,15.500000,interval,motion,spreadsheet-style edit\n"
    )

    loaded = read_events_csv(path)

    assert loaded == (
        EventMarker(12.0, duration_seconds=3.5, label="motion", notes="spreadsheet-style edit"),
    )


def test_format_event_log_text_lists_point_and_interval_rows() -> None:
    from ads1292_studio.events import format_event_log_text

    text = format_event_log_text(
        (
            EventMarker(2.0, label="baseline", notes="quiet"),
            EventMarker(12.5, duration_seconds=5.5, label="motion", notes="arm motion"),
        )
    )

    assert "Start (s)\tEnd (s)\tDuration (s)\tType\tLabel\tNotes" in text
    assert "2.00\t2.00\t0.00\tpoint\tbaseline\tquiet" in text
    assert "12.50\t18.00\t5.50\tinterval\tmotion\tarm motion" in text


def test_event_marker_normalizes_negative_duration_to_point_event() -> None:
    marker = EventMarker(timestamp_seconds=2.0, duration_seconds=-1.0).normalized()

    assert marker.duration_seconds == 0.0
    assert marker.end_seconds == 2.0


def test_event_from_interval_orders_start_and_end_times() -> None:
    marker = event_from_interval(
        start_seconds=17.0,
        end_seconds=12.0,
        label="motion segment",
        notes="start/end clicked in reverse during review",
    )

    assert marker.timestamp_seconds == 12.0
    assert marker.duration_seconds == 5.0
    assert marker.end_seconds == 17.0


def test_event_marker_normalizes_blank_fields() -> None:
    marker = EventMarker(timestamp_seconds=-1.0, label="  ", notes="  electrode touched  ").normalized()

    assert marker.timestamp_seconds == 0.0
    assert marker.label == "event"
    assert marker.notes == "electrode touched"


def test_event_template_is_immediately_writable(tmp_path: Path) -> None:
    path = tmp_path / "template.json"

    write_events_json(path, event_template())

    assert read_events_json(path)[0].label == "motion"
