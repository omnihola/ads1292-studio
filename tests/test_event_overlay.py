from ads1292_studio.event_overlay import (
    EventOverlayItem,
    build_event_overlay_items,
    event_overlay_key,
)
from ads1292_studio.events import EventMarker, event_from_interval


def test_no_events_returns_empty() -> None:
    assert build_event_overlay_items((), x_max_seconds=10.0) == ()


def test_non_positive_x_max_returns_empty() -> None:
    events = (EventMarker(timestamp_seconds=1.0, label="motion"),)
    assert build_event_overlay_items(events, x_max_seconds=0.0) == ()
    assert build_event_overlay_items(events, x_max_seconds=-5.0) == ()


def test_point_event_is_not_interval_and_labels_at_start() -> None:
    events = (EventMarker(timestamp_seconds=4.0, label="touch"),)

    items = build_event_overlay_items(events, x_max_seconds=30.0)

    assert len(items) == 1
    item = items[0]
    assert item.is_interval is False
    assert item.start_seconds == 4.0
    assert item.end_seconds == 4.0
    assert item.label == "touch"
    assert item.label_x == 4.0


def test_interval_event_is_interval_and_labels_at_midpoint() -> None:
    events = (event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion"),)

    items = build_event_overlay_items(events, x_max_seconds=60.0)

    assert len(items) == 1
    item = items[0]
    assert item.is_interval is True
    assert item.start_seconds == 10.0
    assert item.end_seconds == 20.0
    assert item.label_x == 15.0


def test_interval_overrunning_record_end_is_clamped() -> None:
    events = (event_from_interval(start_seconds=70.0, end_seconds=120.0, label="recovery"),)

    items = build_event_overlay_items(events, x_max_seconds=90.0)

    assert len(items) == 1
    item = items[0]
    assert item.start_seconds == 70.0
    assert item.end_seconds == 90.0
    assert item.is_interval is True
    assert item.label_x == 80.0


def test_event_starting_past_record_end_is_dropped() -> None:
    events = (
        EventMarker(timestamp_seconds=5.0, label="inside"),
        EventMarker(timestamp_seconds=95.0, label="past_end"),
    )

    items = build_event_overlay_items(events, x_max_seconds=90.0)

    assert [item.label for item in items] == ["inside"]


def test_items_are_event_overlay_item_instances() -> None:
    events = (EventMarker(timestamp_seconds=1.0, label="x"),)
    items = build_event_overlay_items(events, x_max_seconds=10.0)
    assert isinstance(items[0], EventOverlayItem)


def test_key_is_stable_for_unchanged_events() -> None:
    events = (
        EventMarker(timestamp_seconds=4.0, label="touch"),
        event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion"),
    )

    first = event_overlay_key(events, x_max_seconds=60.0)
    second = event_overlay_key(events, x_max_seconds=60.0)

    assert first == second


def test_key_changes_when_an_event_is_added() -> None:
    base = (EventMarker(timestamp_seconds=4.0, label="touch"),)
    extended = (*base, event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion"))

    assert event_overlay_key(base, x_max_seconds=60.0) != event_overlay_key(extended, x_max_seconds=60.0)


def test_key_changes_when_x_range_changes() -> None:
    events = (event_from_interval(start_seconds=10.0, end_seconds=80.0, label="motion"),)

    assert event_overlay_key(events, x_max_seconds=60.0) != event_overlay_key(events, x_max_seconds=120.0)
