# ADS1292 Studio

ADS1292 Studio is a macOS-friendly research acquisition and review app for the
TI ADS1292RECG-FE / ADS1x9x ECG-FE boards. It replaces the fragile legacy
Windows GUI path for MOTAC gel ECG electrode validation.

This is not diagnostic medical software. It is for feasibility evaluation,
material comparison, recording, and waveform-quality review.

## Run

From this folder:

```bash
PYTHONPATH=src conda run -n sensor python -m ads1292_studio
```

or:

```bash
./run_gui_sensor.sh
```

CLI checks:

```bash
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli ports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli firmware --port /dev/cu.usbmodem11101
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli review ../record/ads1292/2026-06-18-164923-ads1292-live.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report ../record/ads1292/2026-06-18-164923-ads1292-live.csv --out reports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-meta-template reports/session-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report ../record/ads1292/2026-06-18-164923-ads1292-live.csv --meta reports/session-template.json --out reports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-events-template reports/events-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report ../record/ads1292/2026-06-18-164923-ads1292-live.csv --events reports/events-template.json --out reports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-calibration-template reports/calibration-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report ../record/ads1292/2026-06-18-164923-ads1292-live.csv --calibration reports/calibration-template.json --out reports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-protocol-template reports/protocol-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report ../record/ads1292/2026-06-18-164923-ads1292-live.csv --protocol reports/protocol-template.json --out reports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package ../record/ads1292/2026-06-18-164923-ads1292-live.csv --out packages
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli verify-package packages/<session>/manifest.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc ../record/ads1292/2026-06-18-164923-ads1292-live.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc ../record/ads1292/2026-06-18-164923-ads1292-live.csv --max-baseline-drift 500 --max-noise-rms 1000 --max-peak-to-peak 30000
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc ../record/ads1292/2026-06-18-164923-ads1292-live.csv --protocol reports/protocol-template.json --max-baseline-drift 500 --max-noise-rms 1000 --max-peak-to-peak 30000
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli batch recording-a.csv recording-b.csv --out reports/batch
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index
```

Batch export writes both a per-recording CSV and a `*-groups.csv` summary grouped
by electrode label.

Session index export writes both the recording library and a
`*-sidecar-plan.csv` / `*-sidecar-plan.html` checklist for missing metadata,
event, calibration, protocol, and quality-gate sidecars. It also writes a
`*-sidecar-templates/` folder with reviewable JSON templates for those missing
sidecars; the templates are staged in the report output folder and do not modify
the original recording folder. The sidecar plan includes both the generated
template path and the final target sidecar path for each missing file. It also
writes an executable `*-apply-sidecars.sh` helper that copies reviewed templates
beside the raw recordings with `cp -n`, so existing sidecars are not overwritten.

## Features in V1

- Explicit Refresh / Connect / Start / Stop flow.
- Dual raw channel recording.
- ADS1292R-aware channel labels: CH2 is ECG Lead I (LA-RA), CH1 is respiration raw.
- Live ECG, respiration raw, and lead-off/status display.
- Synchronized three-panel ADS1292R view: CH2 ECG Lead I, CH1 respiration raw,
  and lead-off/contact status on the same time axis.
- Empty Live ECG panels show the acquisition sequence directly: select an
  ADS1292 port, connect the recorder, then press Start.
- CSV saving with `status_byte` and `lead_off_bits`.
- Offline CSV review with R-peak detection and conservative PQRST review.
- HTML/PNG review report export for experiment records.
- Session metadata JSON for anonymous subject ID, electrode type, montage,
  operator, and notes; metadata is included in exported reports.
- Batch comparison export for multiple recordings, including CSV, HTML, and PNG
  summary outputs plus grouped electrode-level statistics.
- Event markers for motion, deep breathing, electrode touch, or other protocol
  annotations; events can be saved as `.events.json` sidecars and included in
  exported reports.
- ADC calibration config for Vref, PGA gain, and bit depth; GUI plots and
  reports can display ECG in microvolts while raw CSV counts remain preserved.
- Session package export with raw CSV, sidecars, report files, and SHA256
  manifest for auditable experiment records.
- Session package verification to detect missing or modified files from the
  package manifest.
- Quality gate pass/fail checks for minimum duration, contact percentage, QRS
  clarity, R-peak count, and heart-rate bounds.
- Artifact metrics for baseline drift, noise RMS, and peak-to-peak counts in
  CLI review, GUI quality text, and HTML reports.
- Artifact threshold checks in CLI QC for maximum baseline drift, noise RMS,
  and peak-to-peak counts.
- Test protocol sidecars for baseline, motion, and recovery steps; protocol
  templates can be included in reports and session packages.
- Protocol segment metrics in reports and package manifests, including
  per-step contact, R peaks, HR, baseline drift, noise RMS, and peak-to-peak
  values for baseline/motion/recovery validation.
- Protocol segment quality gates in reports, session package manifests, and
  CLI `qc --protocol` output, so baseline/motion/recovery failures are named
  explicitly.
- GUI quality text shows protocol segment gate status for offline protocol
  recordings, and live recordings wait until the protocol window is covered
  before evaluating segment gates.
- GUI-configurable quality gate thresholds can be saved and loaded as
  `.quality-gate.json` sidecars; live/offline quality text, reports, and
  session packages use the same pass/fail settings.
- Scrollable left control sidebar keeps metadata, event, calibration,
  quality-gate, protocol, and safety controls reachable on smaller windows.
- Task-based GUI sidebar separates Status, Session, Validation, Protocol, and
  Actions so acquisition controls stay simple while review/export/library tools
  remain one click away.
- GUI buttons are state-gated: Start requires a confirmed connection, Stop
  requires streaming, and report/package export actions require available data
  instead of relying on error dialogs after invalid clicks.
- The Port combobox is state-gated with the same snapshot: it remains editable
  before acquisition, then locks while connecting, starting, or streaming so a
  mid-stream text edit cannot re-enable Connect for a different port.
- The Save CSV acquisition toggle is state-gated too: it stays editable before
  acquisition, then locks while connecting, starting, or streaming because the
  active recording path is decided when Start is pressed.
- GUI control gating, workflow hints, overview text, and status rows share one
  immutable `GuiState` snapshot so the UI does not recompute the same state in
  multiple places.
- Status tab includes a Next Step hint that translates connection, streaming,
  loaded-data, and packaging state into the next valid operator action.
- Status tab includes a compact Overview with Connection, selected Port,
  Acquisition, Data, and Package readiness so the operator can scan the current
  state without interpreting disabled buttons.
- Status Overview is rendered as scan-friendly status rows with deterministic
  ready, running, warning, and neutral styles instead of only a multiline text
  block.
- Session index export scans a recordings folder, ignores generated summary
  CSVs, and writes a CSV/HTML experiment library with ECG source, contact,
  R-peak, HR, quality, and usable/review status.
- Session index also audits sidecar completeness for metadata, events,
  calibration, protocol, and quality-gate files so incomplete experiment
  records are visible before reporting or packaging.
- Session index combines waveform usability and sidecar completeness into
  package-ready status: `package_ready`, `incomplete_record`, or
  `needs_signal_review`.
- Session index HTML and CLI output include package-ready summary counts so
  incomplete records and signal-review records are visible before packaging.
- Session index rows include a next-action recommendation:
  `complete_sidecars`, `review_signal`, or `package_record`.
- Session index HTML and CLI output include next-action summary counts for
  package, sidecar-completion, and signal-review queues.
- GUI Session Index export confirmation shows the same readiness and action
  queue counts as the CLI output.
- Session index also exports a sidecar completion plan CSV/HTML that lists each
  missing sidecar target path, generated template path, and suggested action,
  and the GUI confirmation shows those plan paths.
- Session index stages JSON templates for missing sidecars in a separate
  `*-sidecar-templates/` folder so users can review metadata, event,
  calibration, protocol, and quality-gate templates before copying them beside
  raw recordings.
- Session index writes an executable `*-apply-sidecars.sh` helper that maps the
  staged templates to their final target sidecar paths without overwriting
  existing files.
- Testable signal-analysis core independent of live hardware.

## Development notes

- Keep the live render path lightweight: raw 1x non-inverted display should
  reuse the existing NumPy buffer, and Matplotlib artists should only be
  recreated when their visible settings actually change.
- Reuse fixed display smoothing kernels and stable decimation budgets; live ECG
  and respiration plots use the same window geometry repeatedly during
  streaming.
- Keep live ECG, respiration, and contact/status x-limits explicitly
  synchronized during every live frame; do not rely only on `sharex`, because
  the render helper should remain correct if panel construction changes.
- Use stride decimation for live ECG/respiration traces after display
  smoothing so the rolling view reads as a continuous waveform; reserve
  extrema-preserving decimation for offline review and reports where narrow
  spike preservation matters more than live visual smoothness.
- Keep the live contact/status trace state-aware: use the neutral contact
  color when the visible window is clean and the warning color when any
  lead-off bit is visible, but only write the Matplotlib line color when the
  color actually changes.
- Render contact/status as a crisp digital trace (`steps-post`, snap enabled,
  no antialiasing); do not smooth it like ECG or respiration.
- Check duplicate live render keys before building render frames, and only
  clear empty-state artists after a frame is available, so idle or failed GUI
  ticks do not touch Matplotlib unnecessarily or flash blank axes.
- Live ECG, respiration, and contact axes share x-limits; update the primary
  ECG x-axis only and let Matplotlib propagate the shared range to avoid extra
  per-frame axis writes.
- When streaming samples remain queued after a GUI tick, schedule the next tick
  with the catch-up interval so the display can recover from short stalls
  without adding visible latency.
- Do not run R-peak bandpass/detection work until at least one second of
  samples is available; earlier windows cannot produce valid HR anyway.
- Skip live R-peak detection when the visible contact window is entirely
  lead-off; disconnected electrodes should not spend GUI time on HR estimates
  or show misleading peaks.
- Skip live R-peak detection for flatline ECG windows; a constant trace cannot
  produce valid HR and should not spend GUI time on bandpass/peak detection.
- Hide the live R-peak marker artist when no peaks are visible, and only change
  artist visibility when the peak-present state changes.
- Apply changed-only data writes to the live R-peak marker because the peak
  arrays are sparse and often empty; do not use array-equality guards on full
  live ECG/respiration/contact traces, where comparing the rolling waveform can
  cost more than the Matplotlib update it tries to avoid.
- Apply the same changed-only rule to offline review R-peak markers; keep full
  review ECG/respiration/contact traces as direct `set_data` writes because
  those arrays carry the main waveform and are usually larger than peak markers.
- Keep live R-peak detection to one `find_peaks` pass by selecting the dominant
  ECG polarity before peak search; this preserves inverted-lead support without
  doubling GUI-tick peak detection work.
- Keep both live and offline review Matplotlib line/axis/grid/calibration
  application in `gui_plots.py`; `app.py` should queue frames, clear state, and
  update text/cards instead of owning plot mutation details.
- Avoid redundant PQRST panel redraws during offline review; the review traces
  can refresh with the current frame, but the PQRST panel uses an axis clear and
  full redraw, so only redraw it when the `PqrstReview` content changes.
- Keep the PQRST average-beat line visually consistent with the main signal
  traces: antialiased with rounded caps/joins, so morphology review looks smooth
  without changing the underlying averaged beat data.
- Keep the ECG paper grid low-contrast and warm-toned enough to give ECG-paper
  scale cues without competing with the live trace; preserve the 25/50 mm/s
  spacing behavior while adjusting only palette, alpha, or linewidth for visual
  polish.
- Keep live axis title caching and title writes in `gui_plots.py`; `app.py`
  should pass current display/filter context and channel labels only.
- Keep live metrics text generation and changed-only StringVar writes in
  `gui_state.py`; `app.py` should pass frame values rather than formatting
  toolbar text directly.
- Keep expensive live quality recomputation in the existing single-flight
  background worker so GUI ticks do not accumulate queued analysis jobs; wait
  for at least one second of samples before starting live quality snapshots.
- Keep live quality scheduling decisions in `gui_workers.py`; App must decide
  whether a worker can run before copying live channel buffers into tuples.
- Keep background result dataclasses and worker helpers in `gui_workers.py`,
  with `app.py` importing them for compatibility, so App remains focused on UI
  orchestration rather than owning worker data models.
- Keep live quality and offline review result queues drained through the shared
  generation-aware helper in `gui_workers.py`; App should only apply the newest
  result for the current generation.
- Keep offline review redraw scheduling as a single-flight worker flow in
  `gui_workers.py`: when a redraw is running, store only the newest pending
  samples and submit that latest request after the current future finishes.
- Keep GUI form parsing/formatting for metadata, protocol steps, calibration
  numbers, and quality-gate thresholds in `gui_forms.py`; `app.py` may
  re-export these helpers for compatibility but should not own the conversion
  rules.
- Keep log insertion batched and avoid autoscrolling the log Text widget while
  another workspace tab is selected; scroll to the end when Event Log is opened.
  Keep append/trim/autoscroll Text-widget operations in `gui_log.py` so the
  GUI tick only drains queues and delegates log rendering.
- Keep toolbar toggle chips mouse- and keyboard-accessible, with visible hover
  and focus feedback, because they replace heavier checkbutton chrome,
  including acquisition toggles such as Save CSV; disabled toggle chips must
  use a dedicated muted style and swallow click/keyboard activation so
  state-gating is visually clear and not only decorative.
- Keep the toolbar display summary chip bounded with a fixed character width
  and wrap length so longer mode/filter text cannot stretch the top toolbars or
  push acquisition controls out of view. The chip should read like an operator
  status line (`Live: CH2 ECG Lead I | CH1 Resp | Contact | ...`), not only raw
  internal channel names.
- Keep the header connection pill bounded with a fixed width and wrap length so
  long connection detail strings cannot stretch the title bar; detailed
  connection text belongs in the log and sidebar status area.
- Keep Connect available whenever the GUI is idle and not already connected,
  even if automatic port detection currently reports `no port`; clicking it with
  no selected port shows the existing validation error, while a manually typed
  `/dev/cu.*` path gets a real serial probe. Keep offline CSV actions enabled,
  keep the header badge and sidebar Connection card aligned on the selected-port
  state, and recompute controls immediately when the port field changes or
  Refresh updates the port list. Read the port variable, visible combobox text,
  and combobox values so macOS/Tk combobox sync lag cannot hide a usable port;
  refresh must replace stale or blank visible text with the selected port and
  keep the last valid/manual port as a fallback even if automatic scanning
  temporarily returns no ADS candidates. Enable Start only when the selected
  port matches the connected port.
- Treat macOS `/dev/cu.usbmodem*` and `/dev/cu.usbserial*` devices as ADS1292
  connection candidates in the port list. Some ADS1292RECG-FE boards show up as
  generic USB serial devices before the firmware description is fully
  populated; excluding those candidates can leave Connect/Start/Stop disabled
  even when the visible port field contains the board path.
- Keep custom sidebar/workspace tab strips keyboard-accessible, with visible
  hover and focus states, because they replace native notebook tabs.
- Avoid doing hidden live-plot work: while the Live ECG workspace tab is
  unmapped, keep draining samples and running background quality updates, but
  skip the live plot frame build and canvas redraw. Flush one live redraw when
  the user returns to Live ECG so Review CSV, PQRST, and Log navigation stays
  responsive during streaming.
- Sidebar mouse-wheel hit testing should cover the whole scroll frame, including
  scrollbar and edge padding, not only the canvas interior; otherwise scrolling
  feels broken when the pointer is still visually inside the sidebar.
- Sidebar card value labels, including Overview status values, should set a
  fixed wrap length and left justification so long port/status text does not
  stretch the task panel.
- Keep action buttons' focus borders visible so keyboard navigation has a
  clear current target across acquisition and sidebar controls; build primary
  toolbar actions and sidebar actions through shared helpers so cursor, focus,
  width, and style stay consistent, with disabled buttons using the normal
  arrow cursor instead of a hand cursor. Disabled action buttons should use a
  light recessed surface and muted text so unavailable actions recede instead
  of becoming a row of heavy gray blocks. Buttons should also define pressed
  foreground/background/border tokens, mapped before hover/active states, so
  clicks feel tactile instead of only changing cursor state.
- Keep empty signal panels visually quiet with the dedicated empty-state axis
  surface, muted callouts, and a static reference guide line, then remove those
  empty-state artists and restore normal data-axis chrome as soon as samples
  arrive so the real-time tick path stays clean. Repeated empty-state refreshes
  for the same panel must reuse the existing empty-state artists instead of
  stacking duplicate guide/text artists. Clear empty-state artists by target
  axes/panel; live data should not erase Review or PQRST placeholders.

## Safety

Use a battery-powered laptop for body-contact tests. Do not charge the laptop
during recording and do not connect other earth-referenced instruments to the
subject.
