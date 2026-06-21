# GUI Review Event Annotation Overlay — Design

## Context

`ads1292-studio/` is a research-grade ECG acquisition/review GUI (43+ TDD phases,
481 tests). Event annotations are already first-class data: point and interval
markers (`EventMarker`), stable IDs, sample-index references, `.events.json` /
`.events.csv` sidecars, an event log table, and report inclusion.

The exported HTML report **draws** these annotations on its ECG PNG
(`report._apply_event_overlays`: interval → shaded span, point → dashed line,
label anchored at the top of the axis). The **interactive Review tab does not**.
A researcher who loads a recording and marks "motion artifact, 73–79 s" can read
it in a text table but cannot *see* that span on the waveform they are reviewing —
even though the static report they export later does show it.

This closes the loop the project's own goal names directly ("在测试过程中多少 s 到
多少 s 之间加一个注释"): annotate a time range → see it highlighted on the signal.

## Problem (evidence)

1. `gui_plots.apply_review_render_frame` draws ECG/resp/status traces, R-peaks,
   titles, axes, grid, and the calibration pulse — but no event overlay.
2. `app.add_event` / `add_event_range` / `add_manual_event_range` /
   `remove_last_event` mutate `self.event_markers`, save the sidecar, and log —
   but never refresh the waveform.
3. The overlay geometry already exists, inlined in `report._apply_event_overlays`.
   Adding a second copy in the GUI would duplicate it (drift risk). It should be
   extracted once and shared.

## Design

### New module: `event_overlay.py` (pure, testable)

A single source of truth for overlay geometry — no Matplotlib, no Tk.

- Constants: `EVENT_INTERVAL_COLOR = "#F59E0B"`, `EVENT_POINT_COLOR = "#B45309"`,
  `EVENT_INTERVAL_ALPHA = 0.14`, `EVENT_POINT_ALPHA = 0.72`, `EVENT_LABEL_Y = 0.96`.
- `EventOverlayItem` (frozen): `start_seconds`, `end_seconds`, `label`,
  `is_interval`, `label_x`.
- `build_event_overlay_items(events, *, x_max_seconds) -> tuple[EventOverlayItem, ...]`:
  normalize each marker, drop markers starting beyond `x_max_seconds`, clamp
  start/end to `[0, x_max_seconds]`, classify interval vs point
  (`duration > 0 and end > start`), and compute the label x (span midpoint for
  intervals, start for points). Returns `()` when `x_max_seconds <= 0`. This is
  exactly the logic currently inlined in `report.py`.
- `event_overlay_key(events, *, x_max_seconds) -> tuple`: a hashable digest of the
  built items plus the rounded x range, for changed-only redraw.

### Refactor: `report._apply_event_overlays`

Reimplement on top of `build_event_overlay_items` and the shared constants. Visual
output is byte-for-byte equivalent, so existing report tests stay green.

### GUI: `gui_plots.apply_event_overlay_artists`

Matplotlib mutation stays in `gui_plots.py` (project convention: `app.py` owns
state, `gui_plots.py` owns plot mutation). Signature:

`apply_event_overlay_artists(app, items, *, key) -> bool`

- Return `False` immediately if `key == app.review_event_overlay_key`
  (changed-only discipline — annotations rarely change between frames).
- Otherwise remove the previously stored artists, draw each item across the three
  shared-x review axes (`ax_review_ecg`, `ax_review_resp`, `ax_review_status`):
  interval → `axvspan`, point → `axvline`; the text label only on the ECG axis,
  in axis-fraction y via `get_xaxis_transform()`. Store the new artist list on
  `app.review_event_overlay_artists`, cache the key, return `True`.

Applying spans to all three axes (label on ECG only) lets a researcher see the
annotated window aligned across ECG, respiration, and contact at once — the
research-grade choice, and a superset of the report's two-axis overlay.

### App wiring

- Initialize `self.review_event_overlay_artists = []` and
  `self.review_event_overlay_key = None`.
- `_show_review_frame` applies the overlay from `self.event_markers` and
  `frame.x_right` after `apply_review_render_frame`, then requests a
  visible-only canvas redraw.
- New `_refresh_review_event_overlay()`: rebuild + redraw the overlay using the
  current review x-range (read back from `ax_review_ecg`), guarded so it is a
  no-op when no recording is loaded. Called from the four event-mutation methods
  so a newly added/removed annotation appears on the waveform immediately.

## Explicitly out of scope

- **Live (streaming) overlay.** The Live tab is a rolling relative-time window;
  overlaying absolute-time annotations there is a separate, harder feature. Data
  is still captured live; visualization lands in Review where the full recording
  is shown on an absolute 0→duration axis.
- Editing/dragging annotations on the plot. This is read-only visualization.
- Any change to the annotation data model, sidecar schema, or report output
  (output stays identical; only its implementation is shared).

## Testing (TDD: failing test first)

- `tests/test_event_overlay.py` (pure unit): empty events → `()`;
  `x_max_seconds <= 0` → `()`; interval classification + midpoint `label_x`;
  point classification + start `label_x`; clamping of an interval that overruns
  the record end; a marker starting past `x_max_seconds` is dropped;
  `event_overlay_key` changes when events change and is stable when they don't.
- `tests/test_gui_plots.py` (Agg, no Tk mainloop): after
  `apply_event_overlay_artists` with one interval + one point, the review ECG
  axis has the expected `axvspan`/`axvline`/`text` artists; a second call with
  the same key is a no-op (returns `False`, artist count unchanged); a call with
  a changed key removes the old artists and draws the new set.
- Existing `test_quality_report.py` event-overlay assertions must remain green
  after the report refactor.

## Verification

Full `pytest` suite (must stay green, now 481 + new tests), then a smoke check
rendering a real recording's review frame with a synthetic interval annotation to
confirm the span artist is present on `ax_review_ecg`.
