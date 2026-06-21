# Live Event Annotation Overlay — Design

## Context

The companion spec `2026-06-21-gui-review-event-overlay-design.md` added event
annotation overlays to the offline **Review** waveform and explicitly deferred the
**live** view as "a separate, harder feature" because the live plot is a rolling
window. This spec covers that follow-up — the literal headline example of the
project goal: annotate a time range *during the test* and see it on the live
trace.

## Key enabling fact

`live_render.build_live_render_frame` computes the live x-axis as
`visible_x = indices / sample_rate_hz` — i.e. **absolute seconds from recording
start** — and sets a rolling window `[right - window, right]` (live_render.py
lines 88-90). Because the axis is absolute time, an annotation drawn as a
Matplotlib `axvspan`/`axvline` in **data coordinates** sits at its true position
and scrolls with the window automatically as the per-frame x-limits advance.
Matplotlib clips the off-screen portion. No per-frame overlay work is needed.

This is what makes the live overlay low-risk: it does **not** touch the
performance-tuned `apply_live_render_frame` hot path at all.

## Design

Reuse the iteration-1 pure core (`event_overlay.py`) unchanged.

- **`gui_plots`**: extract the artist-drawing body of `apply_event_overlay_artists`
  into a shared `_draw_event_overlay(axes, label_axis, items, prior_artists)`.
  `apply_event_overlay_artists` (review) and a new
  `apply_live_event_overlay_artists` (live) both wrap it, each keyed on its own
  `*_event_overlay_key`/`*_event_overlay_artists` app attributes. Review behaviour
  and API are unchanged.
- **`app.py`**:
  - `_refresh_live_event_overlay()`: no-op unless `is_streaming`; build overlay
    items from `event_markers` clamped to the current recorded extent
    (`sample_index / SAMPLE_RATE_HZ`) and apply them to the live axes. The
    changed-only key is the marker tuple itself (not the moving window), so a
    render frame never rebuilds the overlay — only an annotation change does.
  - The four event-mutation methods call `_refresh_live_event_overlay()` next to
    the existing `_refresh_review_event_overlay()`, so a newly added/removed
    annotation appears on whichever view is active.
  - `_clear_live_event_overlay()` removes the artists and resets the key; it is
    called from `_clear_signal_buffers` so a new acquisition or CSV load does not
    inherit stale live annotation artists.

## Out of scope

- Click-to-edit annotations on the plot (still read-only visualization).
- Any change to the annotation data model, sidecar schema, report output, or the
  iteration-1 review overlay behaviour.

## Testing (TDD)

- `tests/test_gui_plots.py`: `apply_live_event_overlay_artists` draws on the live
  axes, is changed-only, and clears on an empty item set.
- `tests/test_app_event_overlay.py`: `_refresh_live_event_overlay` draws while
  streaming, is a no-op when not streaming, and `_clear_live_event_overlay`
  removes artists.
- `tests/test_app_event_ranges.py`: the mutation methods invoke the live refresh.

## Verification

Full `pytest` suite (504 passed), plus a real-recording smoke that builds a live
render frame for a rolling 10 s window, applies a "motion 14-16 s" interval and an
18 s point annotation, renders them correctly inside the window, and confirms that
advancing the window to a later range does not rebuild the overlay (same artist
object persists, changed-only returns False).
