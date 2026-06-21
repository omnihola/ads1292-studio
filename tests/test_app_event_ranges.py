from __future__ import annotations

from types import SimpleNamespace

from ads1292_studio.app import App
from ads1292_studio.events import EventMarker


class _Var:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class _Text:
    def __init__(self) -> None:
        self.content = ""
        self.calls: list[tuple[str, str, str | None]] = []

    def delete(self, start: str, end: str) -> None:
        self.calls.append(("delete", start, end))
        self.content = ""

    def insert(self, index: str, text: str) -> None:
        self.calls.append(("insert", index, None))
        self.content += text


def _fake_app(*, current_time: float) -> SimpleNamespace:
    calls: list[str] = []
    return SimpleNamespace(
        event_range_start_seconds=None,
        event_range_start_var=_Var("Range start: --"),
        event_label_var=_Var("motion"),
        event_notes_var=_Var("arm motion"),
        event_markers=[],
        _current_event_time=lambda: current_time,
        _set_event_count=lambda: calls.append("count"),
        _save_event_sidecar=lambda: calls.append("save"),
        _log=lambda message: calls.append(message),
        calls=calls,
    )


def test_mark_event_range_start_records_current_time() -> None:
    app = _fake_app(current_time=12.345)

    App.mark_event_range_start(app)

    assert app.event_range_start_seconds == 12.345
    assert app.event_range_start_var.get() == "Range start: 12.35 s"


def test_add_event_range_uses_marked_start_and_current_time() -> None:
    app = _fake_app(current_time=18.0)
    app.event_range_start_seconds = 12.5

    App.add_event_range(app)

    assert len(app.event_markers) == 1
    marker = app.event_markers[0]
    assert marker.timestamp_seconds == 12.5
    assert marker.duration_seconds == 5.5
    assert marker.end_seconds == 18.0
    assert marker.label == "motion"
    assert marker.notes == "arm motion"
    assert app.event_range_start_seconds is None
    assert app.event_range_start_var.get() == "Range start: --"
    assert "count" in app.calls
    assert "save" in app.calls


def test_add_manual_event_range_uses_explicit_seconds() -> None:
    app = _fake_app(current_time=18.0)
    app.manual_event_start_var = _Var("73")
    app.manual_event_end_var = _Var("77.25")

    App.add_manual_event_range(app)

    assert len(app.event_markers) == 1
    marker = app.event_markers[0]
    assert marker.timestamp_seconds == 73.0
    assert marker.duration_seconds == 4.25
    assert marker.end_seconds == 77.25
    assert marker.label == "motion"
    assert marker.notes == "arm motion"
    assert app.manual_event_start_var.get() == ""
    assert app.manual_event_end_var.get() == ""
    assert "count" in app.calls
    assert "save" in app.calls
    assert any("Manual event range 73.00-77.25s" in call for call in app.calls)


def test_set_event_count_shows_latest_event_details() -> None:
    app = SimpleNamespace(
        event_count_var=_Var(),
        event_markers=[
            EventMarker(2.0, label="baseline", notes="quiet"),
            EventMarker(12.5, duration_seconds=5.5, label="motion", notes="arm motion"),
        ],
    )

    App._set_event_count(app)

    assert app.event_count_var.get() == "2 events\nLast: 12.50-18.00 s motion - arm motion"


def test_refresh_event_log_replaces_text_widget_contents() -> None:
    text = _Text()
    app = SimpleNamespace(
        event_log_text=text,
        event_markers=[
            EventMarker(2.0, label="baseline", notes="quiet"),
            EventMarker(12.5, duration_seconds=5.5, label="motion", notes="arm motion"),
        ],
    )

    App._refresh_event_log(app)

    assert text.calls[0][0] == "delete"
    assert "Start (s)\tEnd (s)\tDuration (s)\tType\tLabel\tNotes" in text.content
    assert "12.50\t18.00\t5.50\tinterval\tmotion\tarm motion" in text.content
