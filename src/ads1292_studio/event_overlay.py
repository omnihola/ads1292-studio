"""Pure geometry for drawing event annotations on a time-axis signal plot.

This module is the single source of truth for where event annotations land on a
waveform. It is deliberately free of Matplotlib and Tk so the geometry can be
unit-tested directly, and so the HTML report export and the interactive GUI
Review tab draw annotations identically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ads1292_studio.events import EventMarker


EVENT_INTERVAL_COLOR = "#F59E0B"
EVENT_POINT_COLOR = "#B45309"
EVENT_INTERVAL_ALPHA = 0.14
EVENT_POINT_ALPHA = 0.72
EVENT_LABEL_Y = 0.96


@dataclass(frozen=True)
class EventOverlayItem:
    """A single annotation resolved to plot coordinates (seconds on the x-axis)."""

    start_seconds: float
    end_seconds: float
    label: str
    is_interval: bool
    label_x: float


def build_event_overlay_items(
    events: Iterable[EventMarker],
    *,
    x_max_seconds: float,
) -> tuple[EventOverlayItem, ...]:
    """Resolve event markers to clamped, plot-ready overlay items.

    Markers that start after ``x_max_seconds`` are dropped; intervals that overrun
    the record end are clamped to it. An interval is any marker whose positive
    duration still spans a nonzero range after clamping; everything else is a
    point. Returns an empty tuple when there is nothing to draw.
    """

    if x_max_seconds <= 0:
        return ()
    items: list[EventOverlayItem] = []
    for event in events:
        marker = event.normalized()
        if marker.timestamp_seconds > x_max_seconds:
            continue
        start = min(max(marker.timestamp_seconds, 0.0), x_max_seconds)
        end = min(max(marker.end_seconds, 0.0), x_max_seconds)
        is_interval = marker.duration_seconds > 0 and end > start
        label_x = start + (end - start) / 2.0 if is_interval else start
        items.append(
            EventOverlayItem(
                start_seconds=start,
                end_seconds=end,
                label=marker.label,
                is_interval=is_interval,
                label_x=label_x,
            )
        )
    return tuple(items)


def event_overlay_key(
    events: Iterable[EventMarker],
    *,
    x_max_seconds: float,
) -> tuple:
    """A hashable digest of the resolved overlay, for changed-only redraws."""

    items = build_event_overlay_items(events, x_max_seconds=x_max_seconds)
    return (round(float(x_max_seconds), 6),) + tuple(
        (item.start_seconds, item.end_seconds, item.label, item.is_interval)
        for item in items
    )
