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
    ax_ecg = fig.add_subplot(211)
    ax_resp = fig.add_subplot(212)
    ax_ecg.set_xlim(0.0, x_right)
    return SimpleNamespace(
        loaded_samples=loaded_samples,
        event_markers=event_markers,
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
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


def _make_live_app(*, is_streaming: bool, sample_index: int, event_markers) -> SimpleNamespace:
    fig = Figure()
    ax_ecg = fig.add_subplot(211)
    ax_resp = fig.add_subplot(212)
    return SimpleNamespace(
        is_streaming=is_streaming,
        sample_index=sample_index,
        event_markers=event_markers,
        ax_live_ecg=ax_ecg,
        ax_live_resp=ax_resp,
        live_event_overlay_artists=[],
        live_event_overlay_key=None,
        live_canvas=_FakeCanvas(),
        live_tab=None,
    )


def test_refresh_live_event_overlay_draws_while_streaming() -> None:
    app = _make_live_app(
        is_streaming=True,
        sample_index=15000,
        event_markers=[event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion")],
    )

    App._refresh_live_event_overlay(app)

    assert app.live_event_overlay_key is not None
    assert len(app.ax_live_ecg.patches) == 1
    assert app.live_canvas.draw_idle_calls == 1


def test_refresh_live_event_overlay_keeps_future_manual_events() -> None:
    app = _make_live_app(
        is_streaming=True,
        sample_index=15000,
        event_markers=[event_from_interval(start_seconds=73.0, end_seconds=77.25, label="future artifact")],
    )

    App._refresh_live_event_overlay(app)

    assert app.live_event_overlay_key is not None
    assert len(app.ax_live_ecg.patches) == 1
    assert app.live_event_overlay_artists


def test_refresh_live_event_overlay_is_noop_when_not_streaming() -> None:
    app = _make_live_app(
        is_streaming=False,
        sample_index=0,
        event_markers=[event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion")],
    )

    App._refresh_live_event_overlay(app)

    assert app.live_event_overlay_key is None
    assert app.live_event_overlay_artists == []
    assert app.live_canvas.draw_idle_calls == 0


def test_clear_live_event_overlay_removes_artists() -> None:
    app = _make_live_app(
        is_streaming=True,
        sample_index=15000,
        event_markers=[event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion")],
    )
    App._refresh_live_event_overlay(app)
    artists = list(app.live_event_overlay_artists)
    assert artists

    App._clear_live_event_overlay(app)

    assert app.live_event_overlay_artists == []
    assert app.live_event_overlay_key is None
    assert all(artist.axes is None for artist in artists)
