# ADS1292 Studio — PySide6 GUI Modernization (Phase 44) — Design Spec

**Date:** 2026-06-21
**Status:** Approved design (visual baseline accepted); ready for implementation planning
**Visual baseline:** `docs/mockups/2026-06-21-pyqt-modernization-mockup-v5.html` (+ rendered `.png`)

## 1. Goal & scope

Modernize the ADS1292 Studio desktop GUI so it looks contemporary and is easier to
operate, by **rewriting only the widget/styling layer in PySide6** while reusing the
entire toolkit-agnostic core and the `gui_state` view-model unchanged.

Focus (agreed with user):
1. **Visual modernization** — color, typography, spacing, flat controls, semantic state,
   light-first theme.
2. **Usability / workflow** — one obvious primary action, state-gated controls with a
   persistent "Next step" hint, clear status at a glance.

**Non-goals (this phase):** new analysis features; changing signal semantics
(CH2 = ECG, CH1 = respiration is authoritative per TI SBAS502C); migrating plotting to
pyqtgraph; dark mode (the token system is dark-ready, but light ships first).

## 2. Constraints & key decisions

| Decision | Rationale |
|---|---|
| Binding = **PySide6** (LGPL) | Safe to share/publish a research tool; API ~identical to PyQt6. |
| **Rewrite only the widget layer**; reuse core + `gui_state` | The riskiest code (threading, signal processing, recording) is untouched. |
| Plotting via **`FigureCanvasQTAgg`** (phase 1) | `report.py` / `review_render.py` / `spectrum.py` produce matplotlib figures; embedding keeps export working. pyqtgraph for live is a later optional optimization. |
| **Parallel `ui_qt/` package** + new entry point `ads1292-studio-qt` | The working Tk app keeps running until Qt reaches parity. |
| **Light-first, dark-ready token system** compiled to QSS | One source of truth; dark map drops in later with no widget changes. |
| **True 3-column layout**, side columns scroll internally | Matches the real app; equal-height columns remove the empty center-bottom. |
| Live tab = **2 panels** (ECG + respiration) | Lead-off waveform removed; contact kept as a metric + Channel-map row. |
| **Calibrate Live in the control toolbar**, state-gated | Matches existing `calibrate_live()` preconditions (connected, not streaming). |

## 3. Reuse map (what does NOT change)

Reused **as-is** (no Tkinter imports):
`device`, `workers` (`LiveWorker`, `AcquisitionMode`), `acquisition`, `calibration`,
`csv_io`, `display`, `events`, `event_overlay`, `models`, `processing`, `protocol`,
`quality`, `quality_gate`, `metadata`, `recording_bundle`, `recording_manifest`,
`recording_paths`, `report`, `review_render`, `live_render`, `spectrum`, `segments`,
`session_index`, `session_package`, `batch`, `xlsx_io`.

Reused **view-model** (pure functions, toolkit-agnostic):
`gui_state` (control gating, status cards, workflow hint, tick intervals, formatting),
`gui_workers` (background result types + compute fns), `gui_quality`, `gui_samples`,
`gui_session_index`, `gui_forms`. `gui_specs` is reused as the **token/spec seed**.

Re-implemented for Qt (replaces the Tk-bound files; Tk versions stay for the old app):
`app.py` → `ui_qt/main_window.py` + controllers; `gui_layout.py` → `ui_qt/header.py`,
`ui_qt/sidebar_forms.py`, `ui_qt/status_panel.py`; `gui_plots.py` →
`ui_qt/live_panel.py` (+ review/pqrst/spectrum panels in 44.2); `gui_style.py` →
`ui_qt/theme.py`; `gui_scroll.py` → native `QScrollArea`.

## 4. New package structure

```
src/ads1292_studio/
  ui_qt/
    __init__.py
    tokens.py          # design scale (colors, spacing, radius, type) — seeded from APP_VISUAL_TOKENS
    theme.py           # tokens -> QSS stylesheet; Theme(mode="light"); apply_theme(app)
    main_window.py     # QMainWindow: header + toolbars + 3-column body + status bar
    header.py          # title, connection pill
    control_toolbar.py # port, refresh, connect, start, stop, mode, calibrate live, record csv
    display_toolbar.py # auto-scale, filters, scale (window/gain/speed), hint
    sidebar_forms.py   # left column: Session/Validation/Protocol tabbed forms + archive actions
    status_panel.py    # right column: Next step / Overview / Channel map / Signal quality / Session
    live_panel.py      # center: matplotlib FigureCanvasQTAgg (2 axes) + SNR/Event console
    event_console.py   # SNR readout + regrouped event-annotation controls
    widgets/           # small reusable widgets: Card, StatusRow, Pill, IconButton
    controllers/
      acquisition_controller.py  # owns LiveWorker; connect/start/stop/calibrate (background threads)
      live_tick.py               # QTimer that drains sample/log/result queues -> updates UI
  app_qt.py            # entry: main() -> QApplication + MainWindow; console_script ads1292-studio-qt
```

File-size guideline: keep each module focused (<400 lines typical), matching the
project's existing "many small files" convention.

## 5. Theme / token system (light-first)

`ui_qt/tokens.py` exposes a dict (and typed accessors) consumed by `theme.py`. Approved
values from the v5 mockup:

| Token | Value | Use |
|---|---|---|
| surface | `#EEF2F7` | app background |
| panel | `#FFFFFF` | elevated cards |
| panel_alt | `#F5F8FC` | subtle fills, toolbars, table rows |
| border | `#DCE3EC` | hairline borders |
| border_strong | `#C6D0DC` | input/button borders |
| ink | `#1B2533` | primary text |
| ink_muted | `#5A6677` | secondary text |
| ink_faint | `#8A95A4` | tertiary / hints |
| accent | `#1E88A8` | primary actions (medical teal) |
| accent_press | `#166076` | pressed/hover |
| accent_soft | `#E2F1F6` | accent tints, chips |
| indigo | `#4C5DD4` | respiration trace, logo gradient |
| ok / ok_soft | `#2E9E6B` / `#E3F4EC` | connected / pass |
| warn / warn_soft | `#C8881E` / `#FBF0DA` | caution |
| bad / bad_soft | `#D24B4B` / `#FBE7E7` | error / disconnected / destructive |
| ecg / resp | `#1E88A8` / `#4C5DD4` | plot traces |
| radius / radius_sm | `10px` / `7px` | cards / inputs |
| spacing grid | 4px base (gaps 6/8/10/14) | consistent rhythm |
| type scale | 11 / 12.5 / 13 / 17 px; mono for numerics | labels / body / titles / readouts |

`theme.py` builds one QSS string from these tokens and applies it via
`app.setStyleSheet(...)`. Matplotlib axis/trace colors are derived from the same tokens
(reuse `plot_theme` seeds) so plots match the chrome. A future `mode="dark"` swaps the
color block only.

## 6. Layout spec (3 columns)

- **Header:** logo + "ADS1292 Studio" + "MOTAC ECG validation"; right = connection pill
  (semantic color: red disconnected / teal streaming / green connected).
- **Control toolbar:** Port (combo) · Refresh · **Connect** (primary) · Start · Stop ·
  Mode · **Calibrate Live** · Record CSV (checkbox). Enabled/disabled from `gui_state`.
- **Display toolbar:** Auto scale (toggle) · Filters (HP/Notch/LP/QRS segmented) · Scale
  (Window/Gain/Speed) · derived hint text.
- **Left column** (`QScrollArea`): tabbed `Session / Validation / Protocol` forms —
  recording notes, acquisition provenance, Load CSV, Optional archive (Export Report,
  Export Package, Verify Package, Batch Compare, Session Index).
- **Center column:** workspace tabs (Live ECG / Review CSV / PQRST Beat / Spectrum /
  Event Log); Live = 2 synchronized panels (CH2 ECG `Amplitude (counts)`, CH1 respiration
  `Impedance signal (counts)`) that **grow to fill**; bottom = SNR/Event console.
- **Right column** (`QScrollArea`): `Status` — Next step (highlighted), Overview
  (Connection, Port, Acquisition, Data, Package), Channel map (ECG/Respiration/Contact),
  Signal quality (Signal/Contact/Heart rate/Artifacts), Session.
- Body is fixed-height; left/right scroll internally so all three columns are equal height.

### Event console (center bottom), regrouped by intent
- Top strip: **Realtime SNR** readout (left) + live event status (right: count · range start · armed chip).
- **(1) Annotate:** Event label + Event notes → `Add Point Event` (primary) / `Start Range` / `End Range`.
- **(2) Manual range:** Range start s + Range end s → `Add Manual Range`.
- **(3) Manage:** `Remove Last` · Remove # → `Remove Event #` (destructive, tinted red).

## 7. Data flow & concurrency

- **Tick:** a `QTimer` (interval from `gui_state.gui_tick_interval_ms`, active/idle) drains
  `samples` / `logs` / `*_results` queues on the GUI thread → updates ring buffers →
  redraws the live canvas (throttled via existing `should_redraw_live`). This is the Qt
  analogue of the Tk `after()` loop; `LiveWorker` and the queues are unchanged.
- **Background ops:** connect / calibrate / CSV load run on `threading.Thread` and post
  result objects to `queue.Queue`s (existing `ConnectResult`, `LiveCalibrationResult`,
  `CsvLoadResult`, `StreamStartResult`), drained by the timer — identical to today.
- **State:** every UI refresh computes one immutable `GuiState` and feeds
  `gui_control_states`, `gui_status_cards`, `gui_workflow_hint` to drive button
  enable/disable, status cards, and the Next-step hint.

## 8. Phasing

- **44.1 (MVP):** `ui_qt` shell + theme + control/display toolbars + 3-column layout +
  Status panel + live 2-panel plot + SNR/Event console + connect/start/stop/calibrate
  wired to `LiveWorker` via the QTimer drain. Left forms can be present but minimally wired.
- **44.2:** Review CSV / PQRST / Spectrum / Event Log tabs (embed existing matplotlib renders).
- **44.3:** Left-panel forms fully wired (Session/Validation/Protocol) + archive actions
  (report, package, verify, batch, session index) calling existing core modules.
- **44.4:** Polish — focus/hover/pressed states, keyboard shortcuts, density toggle, dark-mode pass.

## 9. Testing strategy

- **No change** to existing core/view-model tests (they don't import a toolkit).
- `theme.py`: deterministic token→QSS output (snapshot test); token table completeness.
- Controllers: logic asserted through `gui_state` outputs (headless, no live Qt needed).
- Widget smoke test: instantiate `MainWindow` under `QApplication` with
  `QT_QPA_PLATFORM=offscreen` to catch construction/layout errors in CI.
- Manual: run `ads1292-studio-qt` against a real board and the saved
  `recordings/*.csv` to confirm parity with the Tk app.

## 10. Risks & mitigations

- **PySide6 / matplotlib-Qt not installed** → add to `pyproject` optional `[qt]` extra;
  document install; keep Tk app as fallback.
- **macOS Qt event-loop + threads** → keep all UI mutations on the GUI thread (timer
  drain only); never touch widgets from worker threads (same discipline as the Tk fix).
- **Scope creep** → strict phasing; 44.1 is a runnable MVP before anything else.
- **Two GUIs to maintain temporarily** → acceptable and intentional; Tk app is removed
  only after Qt reaches parity (separate later decision).

## 11. Open questions

- After parity, do we **remove** the Tk app or keep both entry points? (Defer to end of 44.3.)
- Optional `[qt]` extra vs. hard dependency in `pyproject`? (Lean: optional extra.)
