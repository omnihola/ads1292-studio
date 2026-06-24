# ADS1292 Studio

ADS1292 Studio is a macOS-friendly ECG acquisition, recording, and review app
for the TI ADS1292RECG-FE / ADS1x9x ECG-FE board family. It was built for MOTAC
gel electrode validation, where the workflow needs to be fast enough for bench
testing and explicit enough for research records.

This is not diagnostic medical software. It is for feasibility evaluation,
materials comparison, signal-quality review, and experiment documentation.

## Current App Status

- Main GUI: PySide6 / Qt.
- Live plot engine: pyqtgraph (`LiveScope`) for real-time ECG and respiration.
- Offline plots/reports: Matplotlib, SciPy, seaborn styling where appropriate.
- Tested runtime on this machine: `sensor` conda environment with PySide6 6.9.x.
- Default sample-rate assumption: 500 Hz.
- Default channel interpretation: CH2 is ECG Lead I-like signal; CH1 is
  respiration/raw impedance.

The legacy Tk GUI is still present for comparison and regression coverage, but
new work should target the Qt front end.

## Quick Start

From this folder:

```bash
./run_gui_sensor.sh
```

Equivalent explicit command:

```bash
PYTHONPATH=src conda run -n sensor python -m ads1292_studio
```

Installed console entry points:

```bash
ads1292-studio      # Qt GUI
ads1292-studio-qt   # Qt GUI
ads1292-studio-tk   # legacy Tk GUI
ads1292-studio-cli  # command-line tools
```

If the board is not auto-detected, type the serial path manually. On macOS this
is usually `/dev/cu.usbmodem*` or `/dev/cu.usbserial*`.

## Bench Workflow

1. Plug in the ADS1292RECG-FE board.
2. Press `Refresh`.
3. Select or type the port.
4. Press `Connect`.
5. Choose `Live Monitor` or `Raw Record`.
6. Select output formats: `CSV`, `HDF5`, `XLSX`.
7. Press `Start`.
8. Add point or range events during the session if needed.
9. Press `Stop` to close acquisition and finalize files.
10. Review the recording in `Review CSV`, `PQRST Beat`, `Spectrum`, and `Info`.

Connection and acquisition are intentionally separate. `Connect` proves that the
selected port is the board. `Start` starts a new acquisition. `Stop` finalizes
the current session.

## Hardware Mapping

The app uses the board-specific ADS1292R interpretation that has been used in
MOTAC testing:

| Signal | App label | Meaning |
| --- | --- | --- |
| CH2 | `CH2 ECG Lead I (LA-RA)` | ECG Lead I-like signal |
| CH1 | `CH1 raw impedance` | respiration / impedance channel |
| status low bits | `lead_off_bits` | lead-off / contact status |
| sample rate | `500 Hz` | nominal app assumption |

Lead-off is displayed as a status indicator and saved as raw status data. It is
not automatically converted into event annotations, because this board can keep
lead-off bits asserted in ways that would otherwise produce misleading full-run
event spans.

## Acquisition Modes

### Live Monitor

`Live Monitor` uses the ADS1x9x firmware streaming command. The firmware stream
is parsed as signed 16-bit values for CH1 and CH2, plus board heart-rate,
respiration-rate, and status fields.

Use this mode for:

- normal ECG hookup testing;
- real-time waveform viewing;
- electrode/contact troubleshooting;
- MOTAC gel screening where continuous display smoothness matters.

Live mode can be calibrated with the board's internal test signal. The measured
live scale is empirical for the firmware stream and is saved as metadata when a
live recording is made.

### Raw Record

`Raw Record` uses the ADS1x9x acquire-data command and records signed 24-bit ADC
codes. Acquisition is chunked request/response rather than continuous streaming.

Use this mode for:

- scale-rigorous data capture;
- FFT/spectrum checks;
- waveform work where the raw ADC value matters;
- experiments where you want the ADC count scale from Vref, PGA gain, and ADC
  bit depth.

Raw mode can update less smoothly on screen because the app receives data in
blocks. That is an acquisition-mode tradeoff, not a reason to discard the data.
The GUI resets the live plot range at every new Start so switching from 16-bit
live display to 24-bit raw display does not hide the first raw frame.

## Display Controls

Display controls change visualization only. They do not rewrite the acquired
counts saved to disk.

| Control | Purpose |
| --- | --- |
| `Window` | rolling time window, such as 4/8/12/16 s |
| `Gain` | display multiplier for ECG viewing |
| `Speed` | ECG-paper time-grid cue, 25 or 50 mm/s |
| `Auto scale` | automatic y-range tracking |
| `HP` | high-pass display filter |
| `Notch` | 60 Hz notch display filter |
| `LP` | low-pass display filter |
| `QRS` | QRS-oriented bandpass display filter |
| `Invert ECG` | visual polarity flip for ECG display |

Filters are useful for real-time readability. For morphology arguments, inspect
raw data and average-beat views rather than relying only on the live display
filter state.

## Main GUI Layout

The Qt GUI has three practical zones:

- Top toolbars: port, connection, mode, output format, display controls.
- Center workspace: live plot and analysis tabs.
- Right status panel: next step, connection, channel map, signal quality, and
  recording state.

Workspace tabs:

| Tab | Purpose |
| --- | --- |
| `Live ECG` | synchronized rolling CH2 ECG and CH1 respiration plots |
| `Review CSV` | offline replay of CSV or HDF5 recordings |
| `PQRST Beat` | average-beat morphology review aligned to detected R peaks |
| `Spectrum` | FFT spectrum and amplitude histogram |
| `Info` | recording metadata, event, calibration, and provenance summary |
| `Event Log` | app logs, acquisition logs, event history |

The live ECG area also contains the real-time SNR strip and event annotation
console below the plots.

## Event Logic

Events describe what happened during the experiment. They never alter the raw
signal.

There are two event types:

- Point event: one timestamp, e.g. `motion`, `touch`, `adjust electrode`.
- Range event: start time plus duration, e.g. `motion interval` or `bad contact`.

Live controls:

| Control | Meaning |
| --- | --- |
| `Event label` | short event name |
| `Event notes` | optional free-text notes |
| `Add Point Event` | add label/notes at the current sample clock |
| `Start Range` | remember the current sample clock as range start |
| `End Range` | create a range from remembered start to now |
| manual start/end fields | create an exact range from typed seconds |
| `Remove Last` | remove the most recent event |
| `Remove Event #` | remove a numbered event |

Quick point/range buttons only work while streaming because they depend on the
live sample clock. Manual ranges can be added when streaming or when reviewing a
loaded recording.

Event overlays are shared across Live ECG, Review CSV, reports, JSON/HDF5, and
XLSX export so event timing stays consistent.

## Data Saving Logic

All new recordings are written under:

```text
~/Documents/ECG/
```

Mode-specific folders:

```text
~/Documents/ECG/live/
~/Documents/ECG/raw/
```

Path examples:

```text
~/Documents/ECG/live/2026-06-21-125109-008670-ads1292-studio.csv
~/Documents/ECG/raw/2026-06-21-125109-008670-ads1292-raw.csv
```

Important rules:

- A new file is chosen when `Start` is pressed.
- `Stop` closes the worker and finalizes selected outputs.
- A second Start creates a second session. It does not append to the previous
  stopped recording.
- CSV is the live crash-safe journal whenever any output format is selected.
- HDF5 and XLSX are produced after Stop from the CSV journal.
- If CSV is not selected but HDF5 or XLSX is selected, the CSV journal may be
  removed after the replacement file is durably written.
- Empty captures are kept as CSV only and are not converted into degenerate HDF5
  files.

Output formats:

| Format | Role |
| --- | --- |
| CSV | live journal and simple machine-readable sample table |
| HDF5 | canonical recording container with samples, bundle metadata, and hashes |
| XLSX | Excel-friendly workbook with `Events` and `Data` sheets |
| JSON | exportable metadata bundle derived from HDF5/recording tools |
| report | HTML plus PNG review figures |
| package | self-contained package with manifest and SHA256 verification |

## CSV Columns

### Live CSV

Typical live columns:

```text
timestamp
sample_index
ch1_counts
ch2_counts
board_heart_rate
board_respiration_rate
status_byte
lead_off_bits
```

If live calibration was run before recording, live scale columns are appended:

```text
live_scale_uv_per_count
live_scale_std_uv_per_count
live_scale_cv_percent
live_scale_runs
live_test_signal_pp_uv
live_scale_type
```

### Raw CSV

Typical raw columns:

```text
timestamp
sample_index
ch1_raw24
ch2_raw24
ch1_uv
ch2_uv
status_byte
lead_off_bits
vref_mv
pga_gain
adc_bits
raw_lsb_uv_per_count
acquisition_mode
```

`ch1_raw24` and `ch2_raw24` are signed 24-bit ADC codes. `ch1_uv` and `ch2_uv`
are derived from the raw ADC scale stored in the same row.

## Calibration and Units

There are two different scale concepts:

1. Raw ADC scale: derived from Vref, PGA gain, and ADC bit depth.
2. Live-stream scale: empirical scale for the board firmware's processed
   streaming output.

Raw ADC data is the better path when the exact ADC count scale matters. Live
stream calibration is useful when you are using the firmware's continuous live
stream and need an empirical `uV/count` estimate for that stream.

Do not mix the two scales without explicitly documenting which acquisition mode
produced the recording.

## Real-Time Quality Readouts

The live screen computes a lightweight real-time SNR estimate from the current
ECG window. It displays:

- approximate SNR in dB;
- noise RMS in counts or uV if a live calibration is active;
- contact state from lead-off bits;
- current event count and pending range start.

The SNR estimate is a screening metric for live operation. It is not a substitute
for offline quality review, contact inspection, and morphology checks.

## Offline Review and Analysis

Offline review computes:

- ECG channel choice or source override;
- R-peak detection;
- heart-rate summary from R-R intervals;
- contact percentage from lead-off bits;
- QRS clarity;
- tentative P-wave and T-wave visibility;
- baseline drift;
- noise RMS;
- peak-to-peak artifact metrics;
- FFT spectrum;
- amplitude histogram;
- protocol-segment metrics when a protocol is available.

Interpretation rules:

- P/T labels are tentative screening labels, not clinical confirmation.
- PQRST analysis uses raw selected-channel data, not the current live-display
  filter state.
- Reports use a fixed QRS-oriented bandpass for ECG export consistency.
- Live display filters are for viewing; saved data remains the acquired count
  stream.

## CLI

Use the CLI for headless checks, reports, packages, and batch/index work.

```bash
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli ports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli firmware --port /dev/cu.usbmodem11101
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli stream --port /dev/cu.usbmodem11101 --seconds 10 --csv ~/Documents/ECG/live/test.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli review ~/Documents/ECG/live/test.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report ~/Documents/ECG/live/test.csv --out reports
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc ~/Documents/ECG/live/test.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli manifest ~/Documents/ECG/live/test.csv
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli verify-recording ~/Documents/ECG/live/test.manifest.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package ~/Documents/ECG/live/test.csv --out packages
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli verify-package packages/<session>/manifest.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli batch ~/Documents/ECG/live --out reports/batch
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ~/Documents/ECG --out reports/session-index
```

Template helpers:

```bash
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-meta-template reports/session-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-events-template reports/events-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-calibration-template reports/calibration-template.json
PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-protocol-template reports/protocol-template.json
```

## Troubleshooting

### No port found

- Press `Refresh`.
- Check for `/dev/cu.usbmodem*` or `/dev/cu.usbserial*`.
- Type the port manually and press `Connect`.
- Make sure Parallels or another app has not captured the USB device.

### Connect works but Start appears to do nothing

- Check that the selected port still matches the connected port.
- Watch the Event Log for worker errors.
- Unplug/replug the board, then reconnect.
- If Raw mode times out, use Live Monitor first to confirm the board path and
  firmware response.

### Live works but Raw display looks blank

Raw mode uses 24-bit count values and a chunked acquisition path. Starting a new
recording resets the pyqtgraph view range so the first raw frame becomes
visible. If a window still looks blank, confirm that:

- acquisition state says `streaming`;
- SNR/contact values are changing;
- Auto scale is enabled;
- the selected mode is really `Raw Record`;
- the Event Log does not show acquire timeouts.

### Raw mode looks choppy

This is expected. Raw mode prioritizes data completeness by acquiring larger
blocks. Live Monitor is the smooth display mode.

### Bandpass or filters make morphology look different

Filters are display processing. They can make R peaks easier to see but can also
change Q/S/P/T appearance. Use raw review plus average-beat morphology when the
shape itself is the claim.

### CSV seems empty

Check the file size and whether Stop/finalization completed. If a capture has
zero samples, the app keeps the CSV and skips HDF5 finalization. If CSV was not
selected but HDF5/XLSX was selected, the CSV journal may be removed after the
replacement output is written.

## Project Structure

Key modules:

| Path | Responsibility |
| --- | --- |
| `src/ads1292_studio/app_qt.py` | Qt app entry point |
| `src/ads1292_studio/ui_qt/main_window.py` | Qt main-window assembly and tick loop |
| `src/ads1292_studio/ui_qt/controller.py` | acquisition controller, queues, finalization |
| `src/ads1292_studio/ui_qt/live_scope.py` | pyqtgraph live ECG/respiration scope |
| `src/ads1292_studio/ui_qt/event_console.py` | SNR strip and annotation controls |
| `src/ads1292_studio/ui_qt/status_panel.py` | fixed right-side status cards |
| `src/ads1292_studio/workers.py` | serial acquisition worker for live and raw modes |
| `src/ads1292_studio/device.py` | ADS1x9x serial protocol and frame parsers |
| `src/ads1292_studio/models.py` | sample and review dataclasses |
| `src/ads1292_studio/csv_io.py` | CSV readers/writers for live and raw recordings |
| `src/ads1292_studio/h5_io.py` | canonical HDF5 writer/reader/verifier |
| `src/ads1292_studio/xlsx_io.py` | two-sheet XLSX export |
| `src/ads1292_studio/recording_paths.py` | `~/Documents/ECG/live` and `raw` paths |
| `src/ads1292_studio/recording_bundle.py` | metadata/events/calibration/provenance bundle |
| `src/ads1292_studio/signal_processing.py` | filters, R peaks, HR, PQRST screening |
| `src/ads1292_studio/quality.py` | signal-quality and SNR metrics |
| `src/ads1292_studio/spectrum.py` | FFT and histogram analysis |
| `src/ads1292_studio/report.py` | HTML/PNG report export |
| `src/ads1292_studio/session_package.py` | package export and verification |
| `src/ads1292_studio/session_index.py` | folder-level recording index |
| `src/ads1292_studio/app.py` | legacy Tk app |

## Design Logic

1. Preserve acquired data first.
   Display gain, filters, smoothing, decimation, and autoscale are presentation
   layers. The saved count stream is the primary record.

2. Keep connection, acquisition, and finalization explicit.
   `Connect` validates the board. `Start` creates a session. `Stop` finalizes
   the selected outputs.

3. Keep serial I/O off the GUI thread.
   Worker threads own device reads and CSV writes. The Qt timer drains queues and
   updates UI state.

4. Make real-time plotting lightweight.
   pyqtgraph handles the live trace. The app uses peak-preserving decimation
   before plotting wide windows.

5. Avoid broad hardware register editing in the normal GUI.
   Arbitrary ADS1292 register writes can silently change acquisition state and
   make records hard to compare. The normal GUI exposes safer workflows only.

6. Use one event model everywhere.
   `EventMarker` drives live overlays, review overlays, reports, JSON/HDF5, and
   XLSX export.

7. Use HDF5 as the canonical post-recording container.
   HDF5 stores samples, metadata bundle, and per-array integrity hashes. CSV is
   the live journal and simple exchange format.

8. Keep research provenance visible.
   Recordings include acquisition mode, port, timestamps, calibration, protocol,
   quality gate, processing settings, events, and measured effective sample rate
   when available.

## Development

Install or run in the `sensor` environment used on this machine. For local dev:

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor pytest -q
```

Targeted GUI/display checks:

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor pytest tests/test_live_scope.py tests/test_ui_qt_smoke.py -q
```

Useful principles for future changes:

- Keep `main_window.py` as orchestration, not signal-processing logic.
- Put live plot behavior in `live_scope.py`.
- Put acquisition/finalization behavior in `controller.py` and `workers.py`.
- Keep file-format changes covered by tests in `tests/test_csv_io.py`,
  `tests/test_h5_io.py`, `tests/test_h5_export.py`, and
  `tests/test_recording_bundle_xlsx.py`.
- Keep hardware-free tests for parser, worker, UI state, render, and export
  behavior.
- Do not make display filters mutate saved data.
- Do not make event annotations depend on hidden GUI-only state.

## Test Coverage

The test suite covers:

- ADS1x9x stream and acquire parsers;
- live and raw worker behavior;
- port discovery;
- Qt control gating and smoke tests;
- pyqtgraph live scope behavior;
- event overlay consistency;
- CSV/HDF5/XLSX export;
- recording bundles and package manifests;
- signal processing and quality metrics;
- spectrum and histogram analysis;
- report generation;
- batch and session-index tools;
- macOS runtime handling.

Current expected command:

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor pytest -q
```

## Safety

For body-contact ECG tests:

- Use a battery-powered laptop.
- Do not charge the laptop during body-contact recording.
- Do not connect other earth-referenced instruments to the subject.
- Do not use the board or this software for diagnosis or clinical decisions.
- Treat all recordings as research/feasibility data only.
