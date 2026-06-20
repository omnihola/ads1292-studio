from ads1292_studio.gui_state import (
    ACTIVE_TICK_INTERVAL_MS,
    LIVE_REDRAW_MIN_INTERVAL_MS,
    should_redraw_live,
)


def test_should_redraw_live_blocks_rebuild_within_min_interval() -> None:
    # Two catch-up ticks ~1 ms apart: the second rebuild is throttled.
    assert should_redraw_live(1.001, 1.000, min_interval_ms=40) is False


def test_should_redraw_live_allows_rebuild_after_min_interval() -> None:
    assert should_redraw_live(1.050, 1.000, min_interval_ms=40) is True


def test_should_redraw_live_allows_rebuild_exactly_at_min_interval() -> None:
    assert should_redraw_live(1.040, 1.000, min_interval_ms=40) is True


def test_live_redraw_cap_matches_active_frame_rate() -> None:
    assert LIVE_REDRAW_MIN_INTERVAL_MS == ACTIVE_TICK_INTERVAL_MS
