from __future__ import annotations

from types import SimpleNamespace

from matplotlib.figure import Figure

from ads1292_studio.app import App
from ads1292_studio.events import event_from_interval


class _FakeCanvas:
    def __init__(self) -> None:
        self.draw_idle_calls = 0

    def draw_idle(self) -> None:
        self.draw_idle_calls += 1


def _make_review_app(*, loaded_samples, event_markers, x_right: float = 30.0) -> SimpleNamespace:
    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    ax_ecg.set_xlim(0.0, x_right)
    return SimpleNamespace(
        loaded_samples=loaded_samples,
        event_markers=event_markers,
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
        ax_review_status=ax_status,
        review_event_overlay_artists=[],
        review_event_overlay_key=None,
        review_canvas=_FakeCanvas(),
        review_tab=None,
    )


def test_refresh_review_event_overlay_draws_for_loaded_recording() -> None:
    app = _make_review_app(
        loaded_samples=(1, 2, 3),
        event_markers=[event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion")],
        x_right=30.0,
    )

    App._refresh_review_event_overlay(app)

    assert app.review_event_overlay_key is not None
    assert len(app.review_event_overlay_artists) > 0
    assert len(app.ax_review_ecg.patches) == 1
    assert app.review_canvas.draw_idle_calls == 1


def test_refresh_review_event_overlay_is_noop_without_loaded_recording() -> None:
    app = _make_review_app(
        loaded_samples=(),
        event_markers=[event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion")],
    )

    App._refresh_review_event_overlay(app)

    assert app.review_event_overlay_key is None
    assert app.review_event_overlay_artists == []
    assert app.review_canvas.draw_idle_calls == 0


def test_refresh_review_event_overlay_clears_overlay_when_events_removed() -> None:
    app = _make_review_app(
        loaded_samples=(1, 2, 3),
        event_markers=[event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion")],
        x_right=30.0,
    )
    App._refresh_review_event_overlay(app)
    assert len(app.ax_review_ecg.patches) == 1

    app.event_markers = []
    App._refresh_review_event_overlay(app)

    assert len(app.ax_review_ecg.patches) == 0
    assert app.review_event_overlay_artists == []
