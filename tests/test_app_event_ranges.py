from __future__ import annotations

from types import SimpleNamespace

from ads1292_studio.app import App


class _Var:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


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
