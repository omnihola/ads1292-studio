# ADS1292 Studio

ADS1292 Studio is a macOS-friendly research acquisition, recording, and review
app for TI ADS1292RECG-FE / ADS1x9x ECG-FE boards. It was built for MOTAC gel
ECG electrode validation, where the workflow needs to be simple enough for
bench testing but explicit enough for auditable research records.

This is not diagnostic medical software. It is for feasibility evaluation,
material comparison, waveform-quality review, and experiment documentation.

## Quick Start

From this folder:

```bash
PYTHONPATH=src conda run -n sensor python -m ads1292_studio
```

or:

```bash
./run_gui_sensor.sh
```

The GUI workflow is intentionally manual:

1. Plug in the ADS1292RECG-FE board.
2. Press `Refresh`.
3. Select or type the serial port.
4. Press `Connect`.
5. Choose `Live Monitor` or `Raw Record`.
6. Keep `Save CSV` enabled if the session should be recorded.
7. Press `Start`.
8. Add point/range events during the session if needed.
9. Press `Stop` to close the writer and finalize recording files.

If no board is auto-detected, a manual `/dev/cu.usbmodem*` or
`/dev/cu.usbserial*` path can still be typed and probed with `Connect`.

## Hardware and Signal Mapping

The default mapping is ADS1292R-specific:

- `CH2`: ECG Lead I-like signal, labeled `CH2 Lead I (LA-RA)`.
- `CH1`: respiration / raw impedance channel.
- `lead_off_bits`: contact and electrode-off state from the ADS1292 status byte.
- Sample rate: 500 Hz in the current app assumptions.

The live screen is synchronized as three panels:

1. `CH2 ECG Lead I`
2. `CH1 respiration raw`
3. `lead-off / contact status`

The three panels share the same time axis so motion, breathing, contact loss,
and ECG changes can be compared directly.

## Main GUI Features

### Acquisition Controls

The top toolbar separates physical connection from acquisition:

- `Refresh`: rescan likely ADS1292 serial ports.
- `Connect`: open the selected port and query firmware.
- `Start`: start the selected acquisition mode only after a confirmed
  connection.
- `Stop`: stop the active worker and finalize recording files.
- `Save CSV`: decide whether Start opens a recording file.
- `Live Monitor` / `Raw Record`: choose the acquisition mode.
- `Calibrate Live`: run the board's internal test signal flow to estimate the
  live processed stream scale in `uV/count`.

Controls are state-gated. For example, Start is disabled until the selected
port matches the connected port, and the port field locks while connecting or
streaming so a mid-recording edit cannot silently switch devices.

### Display Controls

The display toolbar is for visualization, not for changing saved raw counts:

- `Window`: rolling time window, such as 8 s.
- `Gain`: display multiplier for viewing.
- `Speed`: ECG-paper sweep cue, such as 25 or 50 mm/s.
- `Auto scale`: robust per-panel scaling.
- `HP`, `Notch`, `LP`, `Bandpass`: optional software display filters.

Saved CSV values preserve the acquired counts. Display filters, gain, smoothing,
and axis scaling are for screen/review readability unless explicitly written as
processing metadata in the recording JSON.

### Workspace Tabs

The main workspace has five tabs:

- `Live ECG`: rolling ECG, respiration, and contact panels.
- `Review CSV`: offline replay of a loaded recording.
- `PQRST Beat`: average beat morphology review aligned to detected R peaks.
- `Spectrum`: FFT spectrum and amplitude histogram for offline review.
- `Event Log`: timestamped app logs and event history.

The sidebar is split into a fixed `Status` column plus task tabs:

- `Session`: metadata, recording notes, and event annotation controls.
- `Validation`: calibration, quality gates, report/package actions, and session
  index tools.
- `Protocol`: baseline/motion/recovery protocol text and safety notes.

The fixed Status panel shows the next valid operator action, connection state,
selected channel map, signal-quality summary, current recording path, event
count, and storage state.

### Events

Events are for marking experimental context, not for altering the waveform:

- `Add Point Event`: add one timestamp, for example `touch`, `motion`, or
  `electrode adjust`.
- `Start Range`: mark the beginning of an interval.
- `End Range`: close the interval at the current recording time.
- `Add Manual Range`: add an exact start/end interval from typed seconds.
- `Remove Last Event` and `Remove Event #`: correct annotations without
  deleting the whole session.

Point events draw as dashed vertical markers. Range events draw as shaded spans.
The same overlay geometry is used in Live ECG, Review CSV, and exported reports.

## Acquisition Modes

### Live Monitor

`Live Monitor` uses the ADS1x9x firmware streaming command. The app parses the
stream as signed 16-bit `ch1` and `ch2` count values with board heart-rate,
respiration-rate, and status fields. This mode is the default for live ECG
screening because it streams continuously and updates smoothly.

Live CSV columns:

- `timestamp`
- `sample_index`
- `ch1_counts`
- `ch2_counts`
- `board_heart_rate`
- `board_respiration_rate`
- `status_byte`
- `lead_off_bits`

If live calibration was run before recording, extra columns are appended:

- `live_scale_uv_per_count`
- `live_scale_std_uv_per_count`
- `live_scale_cv_percent`
- `live_scale_runs`
- `live_test_signal_pp_uv`
- `live_scale_type`

The live `uV/count` value is empirical for this firmware stream. It is measured
from repeated internal-test-signal runs and saved with the CSV so later analysis
knows the scale used for that recording.

### Raw Record

`Raw Record` uses the ADS1x9x acquire-data command and records 24-bit ADC
values in chunks. This mode is better for scale-rigorous experiments because it
uses the ADS1292 ADC count scale from `Vref`, `PGA gain`, and `adc_bits`.

Raw CSV columns:

- `timestamp`
- `sample_index`
- `ch1_raw24`
- `ch2_raw24`
- `ch1_uv`
- `ch2_uv`
- `status_byte`
- `lead_off_bits`
- `vref_mv`
- `pga_gain`
- `adc_bits`
- `raw_lsb_uv_per_count`
- `acquisition_mode`

Raw mode can look less smooth in the live GUI because it is chunked
request/response acquisition rather than continuous streaming. That is a UI
tradeoff, not a reason to discard the raw values.

## Recording Files

When `Save CSV` is enabled, pressing Start creates a timestamped recording under
`~/Documents/ECG/`. Live monitor sessions go to `~/Documents/ECG/live/`; raw ADC
sessions go to `~/Documents/ECG/raw/`. The CSV writer opens at Start and closes
after Stop. A second Start creates a new file; it does not append to the
previous stopped session.

For a recording named:

```text
~/Documents/ECG/live/2026-06-21-125109-008670-ads1292-studio.csv
```

the app can produce:

- `.csv`: acquired samples.
- `.json`: unified recording bundle with metadata, events, calibration,
  acquisition provenance, protocol, quality gate, and display/processing
  settings.
- `.xlsx`: two-sheet workbook with `Events` and `Data`.
- `.manifest.json`: generated or refreshed when a manifest/package workflow is
  used, with hashes for audit checks.
- report files: HTML plus PNG figures for ECG, PQRST, and spectrum review.
- package folder: raw CSV, sidecars, reports, and SHA256 manifest.

The current preferred recording companion is the unified `.json` bundle. Older
sidecars such as `.events.json`, `.calibration.json`, `.protocol.json`,
`.quality-gate.json`, `.acquisition.json`, and `.processing.json` are still
loaded for compatibility when no unified bundle is present.

The `.xlsx` workbook is written only when the CSV exists and the acquisition
worker has stopped. It is designed for convenient inspection in Excel while the
CSV/JSON pair remains the primary machine-readable record.

## Review and Analysis

Offline review computes:

- ECG source selection or override.
- R-peak detection.
- HR summary from R-R intervals.
- Contact percentage from lead-off bits.
- QRS clarity.
- Tentative P and T visibility from average-beat windows.
- Baseline drift, noise RMS, and peak-to-peak artifact metrics.
- Protocol-segment metrics when a protocol is available.
- FFT spectrum and amplitude histogram.

Important interpretation rules:

- P/T labels are tentative screening labels, not clinical confirmation.
- PQRST review uses raw selected channel data for morphology analysis.
- Report ECG plots use a fixed QRS-oriented bandpass for export consistency.
- GUI display filters are for viewing; they should not be treated as the only
  morphology-preserving analysis path.

## CLI

The CLI mirrors the GUI workflows and is useful for smoke tests, reports, batch
comparison, and folder-level audit.

```bash
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli ports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli firmware --port /dev/cu.usbmodem11101
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli stream --port /dev/cu.usbmodem11101 --seconds 10 --csv ~/Documents/ECG/live/test.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli review ~/Documents/ECG/live/test.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report ~/Documents/ECG/live/test.csv --out reports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc ~/Documents/ECG/live/test.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package ~/Documents/ECG/live/test.csv --out packages
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli verify-package packages/<session>/manifest.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli batch recording-a.csv recording-b.csv --out reports/batch
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index recordings --out reports/session-index
```

Template helpers:

```bash
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-meta-template reports/session-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-events-template reports/events-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-calibration-template reports/calibration-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-protocol-template reports/protocol-template.json
```

Session index export scans a recordings folder, ignores generated summary CSVs,
and writes CSV/HTML library tables with signal status, sidecar completeness,
package-readiness, and next-action recommendations. It also stages sidecar
templates and safe copy scripts so incomplete records can be completed without
overwriting existing sidecars.

## Design Logic

### 1. Preserve Acquired Data First

The app always treats acquired counts as the primary record. Display gain,
filters, smoothing, decimation, and autoscale are presentation layers. Calibration
metadata is saved beside the data rather than destructively rewriting the raw
recording.

### 2. Keep Acquisition Simple and Explicit

Connection and acquisition are separate states. Start requires a confirmed port.
Stop only applies while streaming. Save CSV locks once acquisition begins because
the output path is chosen at Start. This prevents ambiguous sessions such as
"which port/file did this data come from?"

### 3. Separate Live UI from Worker I/O

Serial I/O runs in `LiveWorker` on a background thread. Tkinter owns the UI
thread. Samples move through queues, and GUI ticks drain bounded batches so the
window remains responsive during acquisition.

### 4. Keep Expensive Analysis Single-Flight

Quality analysis and offline render work run in background futures. The app uses
generation-aware result draining and single-flight scheduling so stale review
jobs do not pile up behind the newest data.

### 5. Share One Annotation Model

`EventMarker` is the single model for point and interval annotations. The same
event-overlay core builds geometry for live display, offline review, reports,
XLSX, and JSON bundles. This keeps event timing consistent across outputs.

### 6. Make GUI State Deterministic

Toolbar states, status cards, workflow hints, cursor changes, and connection
badges are derived from one immutable `GuiState` snapshot. This avoids separate
pieces of UI disagreeing about whether the app is idle, connected, starting,
streaming, loading, or packaging.

### 7. Keep Plot Mutation Local

`app.py` orchestrates workflow; plot creation and artist updates live in
`gui_plots.py`, `live_render.py`, and `review_render.py`. Render helpers build
data frames; GUI plot helpers apply changed-only Matplotlib artist updates.

### 8. Prefer Auditability over Hidden Automation

Recording bundles include acquisition provenance, calibration, quality gates,
protocol steps, and processing settings. Session packages include hashes. The
operator can later prove which file, scale, contact status, and annotations were
used for a figure.

### 9. Avoid Risky Hardware Configuration by Default

The app supports safe connection, stream/acquire, firmware query, raw ADC
capture, and live test-signal calibration. It does not expose a broad register
write panel in the normal GUI because arbitrary ADS1292 register writes can
change the acquisition state and make records harder to compare.

## Module Map

- `app.py`: Tkinter application orchestration and user workflows.
- `gui_layout.py`: header, toolbar, sidebar, workspace shell, and button wiring.
- `gui_specs.py`: visual constants, tab labels, channel labels, and layout specs.
- `gui_state.py`: immutable GUI state, control gating, status cards, workflow
  hints, and changed-only UI helpers.
- `gui_plots.py`: Matplotlib panel creation and artist updates.
- `live_render.py`: rolling-window live render frame construction.
- `review_render.py`: offline review render frame construction.
- `workers.py`: serial acquisition worker, live mode, raw mode, CSV writer
  ownership.
- `device.py`: ADS1x9x serial protocol, port detection, firmware query,
  streaming frames, raw acquire frames, and live calibration register sequence.
- `csv_io.py`: live CSV, raw CSV, import compatibility, and recorder classes.
- `xlsx_io.py`: lightweight XLSX writer with `Events` and `Data` sheets.
- `recording_bundle.py`: unified JSON bundle for metadata/events/calibration/
  acquisition/protocol/quality/processing.
- `recording_manifest.py`: SHA256 manifest generation and verification support.
- `session_package.py`: export and verify self-contained session packages.
- `signal_processing.py`: filters, channel selection, R peaks, HR, and PQRST
  screening.
- `quality.py` and `quality_gate.py`: quality metrics and pass/fail evaluation.
- `events.py` and `event_overlay.py`: event model, event IDs, sample indices,
  log formatting, and overlay geometry.
- `report.py`: HTML and PNG report export.
- `spectrum.py`: FFT spectrum and raw-count histogram analysis.
- `session_index.py`: folder-level recording library and sidecar/manifest audit.
- `batch.py`: multi-recording comparison summaries.
- `calibration.py`: raw ADC scale and empirical live-stream calibration.
- `acquisition.py`: acquisition provenance and user-readable summaries.
- `protocol.py` and `segments.py`: protocol templates and segment metrics.
- `matplotlib_runtime.py` and `macos_stderr.py`: macOS runtime cleanup for
  Matplotlib/Tk noise and cache behavior.

## Development Notes

- Keep `app.py` as an orchestrator. Put layout in `gui_layout.py`, state logic
  in `gui_state.py`, render-frame creation in `live_render.py` /
  `review_render.py`, and Matplotlib artist mutation in `gui_plots.py`.
- Keep the live render path lightweight. Do not recreate Matplotlib artists on
  every tick if data, limits, labels, or overlay keys did not change.
- Keep ECG, respiration, and contact x-limits synchronized in every live frame.
- Use stride/extrema decimation deliberately: live plotting should read as a
  smooth rolling signal; offline review and reports should preserve narrow
  spikes.
- Do not spend GUI time detecting R peaks when the contact window is fully
  lead-off, when the signal is flat, or when fewer than one second of samples is
  available.
- Keep contact/status as a crisp digital trace. Do not smooth it like ECG.
- Keep event overlay geometry in the pure `event_overlay.py` core so live,
  review, report, XLSX, and JSON timing stay aligned.
- Keep log rendering batched in `gui_log.py`; do not autoscroll hidden log tabs.
- Keep sidebar and workspace tab strips keyboard-accessible with stable widths
  so hover/selection does not reflow the layout.
- Keep Quality, Report, Package, Batch, and Session Index paths usable without
  live hardware.
- Keep tests hardware-free where possible by mocking devices and testing parser,
  worker, state, render, and file-output behavior independently.

## Tests

Run the full suite:

```bash
pytest -q
```

The test suite covers parser behavior, acquisition workers, live/raw CSV output,
GUI control state, event overlays, quality metrics, reports, packages, XLSX,
session index, plotting, and macOS runtime handling.

## Safety

Use a battery-powered laptop for body-contact tests. Do not charge the laptop
during recording and do not connect other earth-referenced instruments to the
subject.
