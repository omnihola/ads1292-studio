# Progress Log

## Session: 2026-06-18

### Phase 1: Requirements & Discovery
- **Status:** complete
- **Started:** 2026-06-18
- Actions taken:
  - Read user objective from active goal.
  - Read Superpowers and planning-with-files instructions.
  - Inspected current project root and confirmed no root git repository exists.
  - Inspected `target.md` and existing ADS1292 code under `tools/ads1292_mac`.
  - Recorded project-specific ECG constraints and saved-data findings.
- Files created/modified:
  - `ads1292-studio/task_plan.md`
  - `ads1292-studio/findings.md`
  - `ads1292-studio/progress.md`

### Phase 2: Planning & Structure
- **Status:** complete
- Actions taken:
  - Created `ads1292-studio/` with `docs/superpowers/plans`, `src/ads1292_studio`, and `tests`.
  - Created persistent planning files in the new subfolder.
  - Created Superpowers implementation plan for V1.
- Files created/modified:
  - `ads1292-studio/`

### Phase 3: Implementation V1
- **Status:** complete
- Actions taken:
  - Added Python package metadata and CLI/GUI entry points.
  - Added immutable data models, ADS1x9x device protocol, CSV IO, signal processing, live worker, plotting helper, and Tk desktop app.
  - Added Live, Review, PQRST, and Log tabs.
  - Added ECG source Auto/CH1/CH2 selection and status-byte/lead-off-bit handling.
  - Added offline CSV review path.
- Files created/modified:
  - `pyproject.toml`
  - `.gitignore`
  - `README.md`
  - `run_gui_sensor.sh`
  - `src/ads1292_studio/*.py`

### Phase 4: Testing & Verification
- **Status:** complete
- Actions taken:
  - Added tests before implementation for CSV IO, stream payload parsing, signal processing, and real saved CSV regression.
  - Verified the red test state failed because the package did not exist.
  - Fixed Auto channel selection root cause by combining QRS sharpness with valid R-R count.
  - Ran syntax checks, pytest, and CLI offline review.
- Files created/modified:
  - `tests/test_csv_io.py`
  - `tests/test_device_parser.py`
  - `tests/test_signal_processing.py`

### Phase 6: Report Export & Experiment Records
- **Status:** complete
- Actions taken:
  - Added `QualityMetrics` and `compute_quality_metrics`.
  - Added report export module that writes HTML, ECG PNG, and PQRST PNG.
  - Added CLI `report` command.
  - Added GUI `Export Report` button.
  - Added tests for quality metrics and report file output.
  - Added `reports/` to `.gitignore`.
- Files created/modified:
  - `src/ads1292_studio/quality.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_quality_report.py`
  - `.gitignore`
  - `README.md`

### Phase 7: Session Metadata & Audit Trail
- **Status:** complete
- Actions taken:
  - Added `SessionMetadata` model plus JSON read/write/template helpers.
  - Added metadata section to HTML reports.
  - Added CLI `report --write-meta-template` and `report --meta`.
  - Added GUI metadata fields for session ID, subject ID, electrode, montage, operator, and notes.
  - Added sidecar JSON save next to CSV recordings.
  - Added metadata tests and real CSV metadata report smoke test.
- Files created/modified:
  - `src/ads1292_studio/metadata.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_metadata.py`
  - `tests/test_quality_report.py`
  - `README.md`

### Phase 8: Batch Comparison
- **Status:** complete
- Actions taken:
  - Added `batch.py` with aggregation of multiple CSV recordings.
  - Batch summary reads each CSV sidecar metadata JSON when present.
  - Added CSV, HTML, and PNG batch summary export.
  - Added CLI `batch` command.
  - Added GUI `Batch Compare` button.
  - Added tests using synthetic commercial/MOTAC recordings.
  - Ran a real-CSV smoke test using duplicated ADS1292 recording with different metadata sidecars.
- Files created/modified:
  - `src/ads1292_studio/batch.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_batch.py`
  - `README.md`

### Phase 9: Event Markers & Annotations
- **Status:** complete
- Actions taken:
  - Added `EventMarker` model plus JSON read/write/template helpers.
  - Added CLI `report --write-events-template` and `report --events`.
  - Added GUI event label/notes fields and Add Event action.
  - Added `.events.json` sidecar save/load behavior for recordings and loaded CSVs.
  - Added event marker table to HTML reports.
  - Fixed GUI buffer clearing so Start/Load resets old samples correctly.
  - Added event tests and report integration tests.
- Files created/modified:
  - `src/ads1292_studio/events.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_events.py`
  - `tests/test_quality_report.py`
  - `README.md`

### Phase 10: Calibration & Engineering Units
- **Status:** complete
- Actions taken:
  - Added `Calibration` model with Vref, PGA gain, ADC bits, and uV/count conversion.
  - Added calibration JSON template/read/write helpers.
  - Added report calibration table and converted report ECG/PQRST plots to microvolts.
  - Added CLI `report --write-calibration-template` and `report --calibration`.
  - Added GUI calibration fields and `.calibration.json` sidecar save/load.
  - Changed GUI live/review display from counts to uV while preserving raw CSV counts.
  - Added calibration and CLI tests.
- Files created/modified:
  - `src/ads1292_studio/calibration.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_calibration.py`
  - `tests/test_cli.py`
  - `tests/test_quality_report.py`
  - `README.md`

### Phase 11: Session Package & Audit Manifest
- **Status:** complete
- Actions taken:
  - Added session package export that copies raw CSV and available sidecars.
  - Added report generation inside each package.
  - Added `manifest.json` with schema, source path, metrics, byte counts, and SHA256 checksums.
  - Added CLI `package` command.
  - Added GUI `Export Package` button.
  - Added `packages/` to `.gitignore`.
  - Added session package and CLI tests.
- Files created/modified:
  - `src/ads1292_studio/session_package.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_session_package.py`
  - `tests/test_cli.py`
  - `.gitignore`
  - `README.md`

### Phase 12: Package Integrity Verification
- **Status:** complete
- Actions taken:
  - Added manifest verification for package files.
  - Verification checks existence, byte count, and SHA256 for every manifest file entry.
  - Added CLI `verify-package` command.
  - Added GUI `Verify Package` button that reports OK or failure details.
  - Added tests for clean package verification and tamper detection.
- Files created/modified:
  - `src/ads1292_studio/session_package.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_session_package.py`
  - `tests/test_cli.py`
  - `README.md`

### Phase 13: Quality Gate & Acceptance Criteria
- **Status:** complete
- Actions taken:
  - Added `QualityGate` and `QualityGateResult`.
  - Added pass/fail evaluation for duration, contact, QRS clarity, R peaks, and HR bounds.
  - Added Quality Gate table to HTML reports.
  - Added CLI `qc` command with threshold options and `--allow-unclear-qrs`.
  - Added GUI quality text that includes Gate Pass/Fail.
  - Added tests for pass/fail behavior, report integration, and CLI QC.
- Files created/modified:
  - `src/ads1292_studio/quality_gate.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_quality_gate.py`
  - `tests/test_quality_report.py`
  - `tests/test_cli.py`
  - `README.md`

### Phase 14: Protocol Templates & Test Plan Sidecars
- **Status:** complete
- Actions taken:
  - Added `ProtocolStep` and `TestProtocol` models with JSON read/write helpers.
  - Added a MOTAC ECG validation protocol template with baseline, motion, and recovery steps.
  - Added protocol sections to exported HTML reports.
  - Added CLI `report --write-protocol-template` and `report --protocol`.
  - Added session package support for `.protocol.json` sidecars and manifest entries.
  - Added GUI protocol fields and automatic `.protocol.json` sidecar save/load.
  - Added tests for protocol JSON, report integration, CLI integration, and package manifest integration.
- Files created/modified:
  - `src/ads1292_studio/protocol.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/session_package.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_protocol.py`
  - `tests/test_quality_report.py`
  - `tests/test_cli.py`
  - `tests/test_session_package.py`
  - `README.md`

### Phase 15: Batch Group Statistics
- **Status:** complete
- Actions taken:
  - Added `BatchGroupSummary` model.
  - Added `group_recordings_by_electrode()` for electrode-level batch statistics.
  - Added grouped statistics for recordings, usable recordings, usable percent, mean duration, contact, R peaks, and HR.
  - Added `*-groups.csv` export.
  - Added Group Summary table to batch HTML.
  - Added CLI output for `group_csv` and group count.
  - Added tests for group aggregation and grouped export.
- Files created/modified:
  - `src/ads1292_studio/batch.py`
  - `src/ads1292_studio/cli.py`
  - `tests/test_batch.py`
  - `README.md`

### Phase 16: Artifact & Baseline Drift Metrics
- **Status:** complete
- Actions taken:
  - Added `baseline_drift_counts`, `noise_rms_counts`, and `peak_to_peak_counts` to `QualityMetrics`.
  - Computed artifact metrics from the selected ECG channel.
  - Added artifact metric rows to HTML review reports.
  - Added artifact metric output to CLI `review` and `qc`.
  - Added drift/noise summary to GUI quality text.
  - Added tests for synthetic drift/noise metrics, report output, and CLI review output.
- Files created/modified:
  - `src/ads1292_studio/quality.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_quality_report.py`
  - `tests/test_cli.py`
  - `README.md`

### Phase 17: Artifact Threshold Quality Gates
- **Status:** complete
- Actions taken:
  - Added optional `QualityGate` limits for baseline drift, noise RMS, and peak-to-peak counts.
  - Added artifact threshold failure messages to quality gate evaluation.
  - Added CLI `qc` flags: `--max-baseline-drift`, `--max-noise-rms`, and `--max-peak-to-peak`.
  - Added artifact metrics to session package manifest.
  - Added tests for direct quality-gate failures, CLI QC artifact failures, and package manifest metrics.
- Files created/modified:
  - `src/ads1292_studio/quality_gate.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/session_package.py`
  - `tests/test_quality_gate.py`
  - `tests/test_cli.py`
  - `tests/test_session_package.py`
  - `README.md`

### Phase 18: Protocol Segment Metrics
- **Status:** complete
- Actions taken:
  - Added `SegmentMetrics` and `analyze_protocol_segments()` for protocol-step windows.
  - Added per-step contact, R peaks, HR, baseline drift, noise RMS, peak-to-peak, source, and quality labels.
  - Added Protocol Segment Metrics table to HTML reports when a protocol is supplied.
  - Added `segment_metrics` to session package manifests.
  - Fixed report segment analysis to use the whole-record ECG source when report source is Auto, preventing baseline/motion/recovery comparisons from switching channels.
  - Added tests for segment metrics, report output, source consistency, and package manifest output.
  - Verified against the real ADS1292 CSV with protocol report and package smoke tests.
- Files created/modified:
  - `src/ads1292_studio/segments.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/session_package.py`
  - `tests/test_segments.py`
  - `tests/test_quality_report.py`
  - `tests/test_session_package.py`
  - `README.md`

### Phase 19: Protocol Segment Quality Gates
- **Status:** complete
- Actions taken:
  - Added `SegmentQualityResult`, `SegmentQualityGateResult`, and `evaluate_segment_quality_gates()`.
  - Added per-segment failure checks for no-data, contact, R peaks, HR bounds, baseline drift, noise RMS, and peak-to-peak limits.
  - Added Protocol Segment Gate table to HTML reports.
  - Added `segment_gate` to session package manifests.
  - Added CLI `qc --protocol`, including `protocol_segment_gate`, per-segment status lines, and `segment_failure=` output.
  - Reused the whole-record ECG source for CLI protocol QC when `--source Auto` is selected.
  - Added tests for segment gate pass/fail, empty segments, report output, package manifest output, and CLI `qc --protocol`.
  - Verified against the real ADS1292 CSV with CLI QC, report, and package smoke tests.
- Files created/modified:
  - `src/ads1292_studio/segments.py`
  - `src/ads1292_studio/report.py`
  - `src/ads1292_studio/session_package.py`
  - `src/ads1292_studio/cli.py`
  - `tests/test_segments.py`
  - `tests/test_quality_report.py`
  - `tests/test_session_package.py`
  - `tests/test_cli.py`
  - `README.md`

### Phase 20: GUI Protocol Segment Gate Visibility
- **Status:** complete
- Actions taken:
  - Added `gui_quality.py` with a testable `build_quality_text()` function for GUI sidebar quality summaries.
  - Added protocol segment gate status and failures to GUI quality text when a protocol is evaluated.
  - Added `protocol_ready_for_live_quality()` so live recordings do not report future protocol steps as failed before the protocol window is covered.
  - Updated GUI CSV load order to load event, calibration, and protocol sidecars before rendering the recording.
  - Updated offline review quality text to reuse the same GUI quality builder as live display.
  - Added tests for segment gate text, no-protocol text, and live protocol readiness.
  - Verified against the real ADS1292 CSV/protocol pair with a direct GUI quality text smoke call.
- Files created/modified:
  - `src/ads1292_studio/gui_quality.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_gui_quality.py`
  - `README.md`

### Phase 21: GUI Quality Gate Presets & Sidecars
- **Status:** complete
- Actions taken:
  - Added normalized quality gate JSON template/read/write helpers for `.quality-gate.json` sidecars.
  - Added GUI controls for minimum duration, contact percentage, R peaks, HR range, QRS clarity, and optional artifact limits.
  - Saved the current GUI quality gate beside new recordings and loaded it before rendering existing CSV files.
  - Reused the GUI-selected gate for live quality text, offline quality text, and report export.
  - Included quality gate sidecars in session packages and wrote normalized gate settings into package manifest metrics.
  - Verified with a real ADS1292 CSV package smoke test that the package manifest and report include the quality gate, protocol segment gate, CH2 source, and `Good ECG/QRS` quality label.
- Files created/modified:
  - `src/ads1292_studio/quality_gate.py`
  - `src/ads1292_studio/session_package.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_quality_gate.py`
  - `tests/test_session_package.py`
  - `tests/test_gui_quality_gate_config.py`
  - `README.md`

### Phase 22: Session Index & Recording Library
- **Status:** complete
- Actions taken:
  - Added `session_index.py` for recursive raw recording CSV discovery.
  - Filtered generated `session-index` and grouped summary CSV outputs out of scans.
  - Added CSV/HTML session index export with metadata, source channel, contact, R peaks, HR, quality label, and usable/review status.
  - Added CLI `index <root> --out <dir>` command.
  - Added GUI `Session Index` toolbar action for folder-to-library export.
  - Verified against the real `../record/ads1292` folder; the index found 9 recordings and marked 2 as usable `Good ECG/QRS` CH2 recordings.
- Files created/modified:
  - `src/ads1292_studio/session_index.py`
  - `src/ads1292_studio/cli.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_session_index.py`
  - `tests/test_cli.py`
  - `README.md`

### Phase 23: Session Index Sidecar Completeness Audit
- **Status:** complete
- Actions taken:
  - Added sidecar status fields to each session index row.
  - Checked metadata, events, calibration, protocol, and quality-gate sidecars for every recording.
  - Added `sidecar_status` and `missing_sidecars` columns to CSV exports.
  - Added Sidecars and Missing Sidecars columns to HTML index exports.
  - Verified against the real `../record/ads1292` folder; older real CSVs are correctly marked missing required sidecars.
- Files created/modified:
  - `src/ads1292_studio/session_index.py`
  - `tests/test_session_index.py`
  - `README.md`

### Phase 24: Session Index Package Readiness
- **Status:** complete
- Actions taken:
  - Added `package_ready_status` to each session index row.
  - Classified rows as `package_ready`, `incomplete_record`, or `needs_signal_review`.
  - Added package-ready status to CSV and HTML index exports.
  - Added tests for complete usable recordings, incomplete sidecar records, and complete-but-review-needed signals.
  - Verified against the real `../record/ads1292` folder; two `Good ECG/QRS` recordings are still correctly marked `incomplete_record` because older records lack required sidecars.
- Files created/modified:
  - `src/ads1292_studio/session_index.py`
  - `tests/test_session_index.py`
  - `README.md`

### Phase 25: Session Index Readiness Summary
- **Status:** complete
- Actions taken:
  - Added `SessionIndexSummary` for folder-level readiness counts.
  - Exposed summary counts through `SessionIndexExport`.
  - Added package-ready, incomplete-record, and signal-review counts to HTML session index exports.
  - Added package-ready, incomplete-record, and signal-review counts to CLI `index` output.
  - Verified against the real `../record/ads1292` folder; all 9 old records are correctly summarized as incomplete because required sidecars are missing.
- Files created/modified:
  - `src/ads1292_studio/session_index.py`
  - `src/ads1292_studio/cli.py`
  - `tests/test_session_index.py`
  - `tests/test_cli.py`
  - `README.md`

### Phase 26: Session Index Next-Action Guidance
- **Status:** complete
- Actions taken:
  - Added `next_action` to each session index row.
  - Mapped package-ready records to `package_record`.
  - Mapped incomplete records to `complete_sidecars`.
  - Mapped signal-review records to `review_signal`.
  - Added Next Action to CSV and HTML session index exports.
  - Verified against the real `../record/ads1292` folder; all 9 older records are correctly assigned `complete_sidecars` because required sidecars are missing.
- Files created/modified:
  - `src/ads1292_studio/session_index.py`
  - `tests/test_session_index.py`
  - `README.md`

### Phase 27: Session Index Action Summary
- **Status:** complete
- Actions taken:
  - Added action queue counts to `SessionIndexSummary`.
  - Counted `package_record`, `complete_sidecars`, and `review_signal` next actions.
  - Added next-action summary text to HTML session index exports.
  - Added next-action summary lines to CLI `index` output.
  - Verified against the real `../record/ads1292` folder; all 9 older records are in the `complete_sidecars` queue.
- Files created/modified:
  - `src/ads1292_studio/session_index.py`
  - `src/ads1292_studio/cli.py`
  - `tests/test_session_index.py`
  - `tests/test_cli.py`
  - `README.md`

### Phase 28: GUI Session Index Summary Message
- **Status:** complete
- Actions taken:
  - Added `gui_session_index.py` with a testable `build_session_index_message()` helper.
  - Included total recordings, package-ready, incomplete, and signal-review counts in the GUI confirmation text.
  - Included package, sidecar-completion, and signal-review action queue counts in the GUI confirmation text.
  - Wired the GUI `Session Index` action to show the new summary message after export.
  - Verified against the real `../record/ads1292` folder; the generated GUI message reports 9 records and 9 complete-sidecar actions.
- Files created/modified:
  - `src/ads1292_studio/gui_session_index.py`
  - `src/ads1292_studio/app.py`
  - `tests/test_gui_session_index.py`
  - `README.md`

## Test Results
| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Root git check | `git status --short` at project root | Determine repository state | Not a git repository | Pass |
| TDD red check | `conda run -n sensor python -m pytest -q` before implementation | Import failures for missing package | 3 collection errors | Pass |
| Unit tests | `conda run -n sensor python -m pytest -q` | All tests pass | 7 passed | Pass |
| Syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/*.py` | No syntax errors | Passed | Pass |
| Offline review | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli review ../record/ads1292/2026-06-18-164923-ads1292-live.csv` | Select CH2, QRS clear | `ecg_source=CH2`, `qrs_clear=True`, HR 93.5 bpm | Pass |
| Local git commit | `git commit -m "feat: add ads1292 studio v1"` | Commit only subfolder repo | Commit `d28ea54` created | Pass |
| GitHub auth check | `gh auth status` | Authenticated GitHub account | Token invalid for `omnihola` | Blocked |
| Report tests | `conda run -n sensor python -m pytest tests/test_quality_report.py -q` | Report tests pass | 2 passed | Pass |
| Full tests after report feature | `conda run -n sensor python -m pytest -q` | All tests pass | 9 passed | Pass |
| Real CSV report smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report ../record/ads1292/2026-06-18-164923-ads1292-live.csv --out reports/smoke2` | HTML and PNG files created, CH2 source | `ecg_source=CH2`, `quality=Good ECG/QRS` | Pass |
| GitHub auth recheck after user login | `gh auth status` | Authenticated GitHub CLI | Token still invalid for `omnihola` | Blocked |
| Sandboxed-external GitHub auth check | escalated `gh auth status` | Authenticated GitHub CLI | Logged in as `omnihola` | Pass |
| GitHub upload | escalated `gh repo create ads1292-studio --private --source=. --remote=origin --push` | Create private repo and push only subfolder repo | Pushed to `https://github.com/omnihola/ads1292-studio` | Pass |
| Metadata tests | `conda run -n sensor python -m pytest tests/test_metadata.py tests/test_quality_report.py -q` | Metadata/report tests pass | 4 passed | Pass |
| Full tests after metadata | `conda run -n sensor python -m pytest -q` | All tests pass | 11 passed | Pass |
| Metadata report smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --meta reports/meta-smoke/session.json --out reports/meta-smoke` | HTML contains Session Metadata and CH2 source | HTML grep found metadata/electrode/source | Pass |
| Batch tests | `conda run -n sensor python -m pytest tests/test_batch.py -q` | Batch tests pass | 2 passed | Pass |
| Full tests after batch | `conda run -n sensor python -m pytest -q` | All tests pass | 13 passed | Pass |
| Batch real CSV smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli batch control.csv motac.csv --out reports/batch-smoke2` | HTML/CSV/PNG generated with commercial and MOTAC metadata | HTML contains both electrode labels and CH2 source | Pass |
| Event TDD red check | `conda run -n sensor python -m pytest tests/test_events.py tests/test_quality_report.py -q` before implementation | Missing events module | `ModuleNotFoundError: ads1292_studio.events` | Pass |
| Event/report tests | `conda run -n sensor python -m pytest tests/test_events.py tests/test_quality_report.py -q` | Event and report tests pass | 5 passed | Pass |
| Syntax compile after events | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/events.py src/ads1292_studio/report.py src/ads1292_studio/cli.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| Full tests after events | `conda run -n sensor python -m pytest -q` | All tests pass | 16 passed | Pass |
| Event real CSV smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --events reports/event-smoke/events.json --out reports/event-smoke` | HTML contains event table and CH2 source | `ecg_source=CH2`, `quality=Good ECG/QRS`, HTML contains Event Markers | Pass |
| Calibration TDD red check | `conda run -n sensor python -m pytest tests/test_calibration.py tests/test_quality_report.py -q` before implementation | Missing calibration module | `ModuleNotFoundError: ads1292_studio.calibration` | Pass |
| Calibration/report tests | `conda run -n sensor python -m pytest tests/test_calibration.py tests/test_quality_report.py -q` | Calibration and report tests pass | 6 passed | Pass |
| CLI calibration red check | `conda run -n sensor python -m pytest tests/test_cli.py -q` before CLI implementation | Missing CLI args | `unrecognized arguments: --write-calibration-template`, `--calibration` | Pass |
| CLI calibration tests | `conda run -n sensor python -m pytest tests/test_cli.py -q` | CLI calibration tests pass | 2 passed | Pass |
| Calibration syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/calibration.py src/ads1292_studio/report.py src/ads1292_studio/cli.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| Full tests after calibration | `conda run -n sensor python -m pytest -q` | All tests pass | 22 passed | Pass |
| Calibration real CSV smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --calibration reports/calibration-smoke/calibration.json --out reports/calibration-smoke` | HTML contains calibration table and CH2 source | `ecg_source=CH2`, `quality=Good ECG/QRS`, HTML contains `2.420 V` and `0.0481 uV/count` | Pass |
| Session package TDD red check | `conda run -n sensor python -m pytest tests/test_session_package.py tests/test_cli.py -q` before implementation | Missing session package module | `ModuleNotFoundError: ads1292_studio.session_package` | Pass |
| Session package tests | `conda run -n sensor python -m pytest tests/test_session_package.py tests/test_cli.py -q` | Session package and CLI tests pass | 4 passed | Pass |
| Full tests after session package | `conda run -n sensor python -m pytest -q` | All tests pass | 24 passed | Pass |
| Session package syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_package.py src/ads1292_studio/cli.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| Session package real CSV smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package <csv> --out packages/smoke` | Manifest includes schema, CH2, Good ECG/QRS, raw/report SHA256 entries | Manifest grep found all required fields | Pass |
| Package verify TDD red check | `conda run -n sensor python -m pytest tests/test_session_package.py tests/test_cli.py -q` before implementation | Missing verify function | `ImportError: cannot import name 'verify_session_package'` | Pass |
| Package verify tests | `conda run -n sensor python -m pytest tests/test_session_package.py tests/test_cli.py -q` | Clean package passes, tampered CSV fails, CLI verify returns success | 7 passed | Pass |
| Full tests after package verify | `conda run -n sensor python -m pytest -q` | All tests pass | 27 passed | Pass |
| Package verify syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_package.py src/ads1292_studio/cli.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| Real package verify smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli verify-package packages/verify-smoke/.../manifest.json` | Real package verifies cleanly | `checked_files=4`, `ok=True` | Pass |
| Quality gate TDD red check | `conda run -n sensor python -m pytest tests/test_quality_gate.py tests/test_quality_report.py tests/test_cli.py -q` before implementation | Missing quality gate module | `ModuleNotFoundError: ads1292_studio.quality_gate` | Pass |
| Quality gate tests | `conda run -n sensor python -m pytest tests/test_quality_gate.py tests/test_quality_report.py tests/test_cli.py -q` | Gate/report/CLI tests pass | 9 passed | Pass |
| Full tests after quality gate | `conda run -n sensor python -m pytest -q` | All tests pass | 30 passed | Pass |
| Quality gate syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/quality_gate.py src/ads1292_studio/report.py src/ads1292_studio/cli.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| Quality gate real CSV smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc <csv>` | Real ADS1292 CSV passes QC | `quality_gate=Pass`, `ecg_source=CH2`, `quality=Good ECG/QRS` | Pass |
| Quality gate report smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --out reports/qc-smoke` | HTML contains Quality Gate Pass | grep found `Quality Gate`, `Pass`, `Good ECG/QRS`, `CH2` | Pass |
| Protocol TDD red check | `conda run -n sensor python -m pytest tests/test_protocol.py tests/test_quality_report.py tests/test_cli.py -q` before implementation | Missing protocol module | `ModuleNotFoundError: ads1292_studio.protocol` | Pass |
| Protocol related tests | `conda run -n sensor python -m pytest tests/test_protocol.py tests/test_quality_report.py tests/test_cli.py tests/test_session_package.py -q` | Protocol/report/CLI/package tests pass | 15 passed | Pass |
| Full tests after protocol sidecars | `conda run -n sensor python -m pytest -q` | All tests pass | 35 passed | Pass |
| Protocol syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/protocol.py src/ads1292_studio/report.py src/ads1292_studio/cli.py src/ads1292_studio/session_package.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| Protocol template smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-protocol-template reports/protocol-smoke/protocol.json` | Template JSON generated | `protocol_template=reports/protocol-smoke/protocol.json` | Pass |
| Protocol report real CSV smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --protocol reports/protocol-smoke/protocol.json --out reports/protocol-smoke` | Report includes protocol and CH2 quality | grep found `Test Protocol`, `MOTAC ECG validation`, `baseline`, `motion`, `recovery`, `CH2`, `Good ECG/QRS` | Pass |
| Protocol package real CSV smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package reports/protocol-smoke/package-source.csv --out packages/protocol-smoke` | Manifest and package report include protocol | grep found `"role": "protocol"`, `Test Protocol`, `CH2`, `Good ECG/QRS` | Pass |
| Batch group TDD red check | `conda run -n sensor python -m pytest tests/test_batch.py -q` before implementation | Missing group API | `ImportError: cannot import name 'group_recordings_by_electrode'` | Pass |
| Batch group tests | `conda run -n sensor python -m pytest tests/test_batch.py -q` | Batch group tests pass | 4 passed | Pass |
| Full tests after batch groups | `conda run -n sensor python -m pytest -q` | All tests pass | 37 passed | Pass |
| Batch group syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/batch.py src/ads1292_studio/cli.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| Batch group real CSV smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli batch reports/batch-groups-smoke/commercial.csv reports/batch-groups-smoke/motac.csv --out reports/batch-groups-smoke/out` | Per-recording and grouped outputs generated | `rows=2`, `groups=2`, grep found `Group Summary`, `Usable %`, `CH2`, `Good ECG/QRS` | Pass |
| Artifact metrics TDD red check | `conda run -n sensor python -m pytest tests/test_quality_report.py tests/test_cli.py -q` before implementation | Missing artifact metric fields/report/CLI output | 3 failed with missing `baseline_drift_counts`, missing report row, missing CLI output | Pass |
| Artifact metrics related tests | `conda run -n sensor python -m pytest tests/test_quality_report.py tests/test_cli.py -q` | Quality/report/CLI tests pass | 11 passed | Pass |
| Full tests after artifact metrics | `conda run -n sensor python -m pytest -q` | All tests pass | 39 passed | Pass |
| Artifact metrics syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/quality.py src/ads1292_studio/report.py src/ads1292_studio/cli.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| Artifact metrics real CSV review smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli review <csv>` | Real ADS1292 CSV prints artifact metrics | `baseline_drift_counts=138.0`, `noise_rms_counts=497.2`, `peak_to_peak_counts=19179.0`, `ecg_source=CH2` | Pass |
| Artifact metrics real CSV report smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --out reports/artifact-smoke` | HTML contains artifact metrics | grep found `Baseline drift`, `Noise RMS`, `Peak-to-peak`, `CH2`, `Good ECG/QRS` | Pass |
| Artifact gate TDD red check | `conda run -n sensor python -m pytest tests/test_quality_gate.py tests/test_cli.py tests/test_session_package.py -q` before implementation | Missing artifact gate args and manifest metrics | 3 failed: unexpected gate kwargs, unrecognized CLI args, missing manifest fields | Pass |
| Artifact gate related tests | `conda run -n sensor python -m pytest tests/test_quality_gate.py tests/test_cli.py tests/test_session_package.py -q` | Quality gate, CLI, and package tests pass | 15 passed | Pass |
| Full tests after artifact gates | `conda run -n sensor python -m pytest -q` | All tests pass | 41 passed | Pass |
| Artifact gate syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/quality_gate.py src/ads1292_studio/cli.py src/ads1292_studio/session_package.py` | No syntax errors | Passed | Pass |
| Artifact gate real CSV fail smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc <csv> --max-baseline-drift 100 --max-noise-rms 300 --max-peak-to-peak 10000` | Real ADS1292 CSV fails strict artifact gates | exit 2, failures for baseline drift, noise RMS, and peak-to-peak | Pass |
| Artifact gate real CSV pass smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc <csv> --max-baseline-drift 500 --max-noise-rms 1000 --max-peak-to-peak 30000` | Real ADS1292 CSV passes loose artifact gates | `quality_gate=Pass`, `ecg_source=CH2` | Pass |
| Protocol segment TDD red check | `conda run -n sensor python -m pytest tests/test_segments.py tests/test_quality_report.py tests/test_session_package.py -q` before implementation | Missing segment module | `ModuleNotFoundError: ads1292_studio.segments` | Pass |
| Protocol segment related tests | `conda run -n sensor python -m pytest tests/test_segments.py tests/test_quality_report.py tests/test_session_package.py -q` | Segment/report/package tests pass | 8 passed | Pass |
| Protocol segment full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 43 passed | Pass |
| Protocol segment syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/segments.py src/ads1292_studio/report.py src/ads1292_studio/session_package.py` | No syntax errors | Passed | Pass |
| Protocol segment real CSV report smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --protocol reports/segment-smoke/protocol.json --out reports/segment-smoke` | HTML contains segment table and CH2 per segment | grep found `Protocol Segment Metrics`, baseline, motion, recovery, CH2, artifact columns | Pass |
| Protocol segment real package smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package reports/segment-package-smoke/package-source.csv --out packages/segment-smoke` | Manifest and package report include segment metrics | grep found `segment_metrics`, `Protocol Segment Metrics`, baseline, motion, recovery, CH2 | Pass |
| Protocol segment gate TDD red check | `conda run -n sensor python -m pytest tests/test_segments.py tests/test_quality_report.py tests/test_session_package.py -q` before implementation | Missing segment gate API/report/package fields | Import error for `evaluate_segment_quality_gates` | Pass |
| Protocol segment gate related tests | `conda run -n sensor python -m pytest tests/test_segments.py tests/test_quality_report.py tests/test_session_package.py -q` | Segment gate, report, and package tests pass | 10 passed | Pass |
| Protocol segment CLI red check | `conda run -n sensor python -m pytest tests/test_cli.py::test_cli_qc_with_protocol_reports_segment_failures -q` before implementation | CLI rejects missing protocol support | `unrecognized arguments: --protocol` | Pass |
| Protocol segment CLI test | `conda run -n sensor python -m pytest tests/test_cli.py::test_cli_qc_with_protocol_reports_segment_failures -q` | CLI reports segment failures and returns 2 | 1 passed | Pass |
| Protocol segment gate full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 46 passed | Pass |
| Protocol segment gate syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/segments.py src/ads1292_studio/report.py src/ads1292_studio/session_package.py src/ads1292_studio/cli.py` | No syntax errors | Passed | Pass |
| Protocol segment gate real CSV QC smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc <csv> --protocol reports/segment-gate-smoke/protocol.json --max-baseline-drift 500 --max-noise-rms 1000 --max-peak-to-peak 30000` | Overall and segment gates pass real CSV | `quality_gate=Pass`, `protocol_segment_gate=Pass`, baseline/motion/recovery Pass | Pass |
| Protocol segment gate real CSV report smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --protocol reports/segment-gate-smoke/protocol.json --out reports/segment-gate-smoke` | Report includes Protocol Segment Gate | grep found `Protocol Segment Gate`, baseline, motion, recovery, Pass, CH2 | Pass |
| Protocol segment gate real package smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package reports/segment-gate-package-smoke/package-source.csv --out packages/segment-gate-smoke` | Manifest and report include segment gate | grep found `segment_gate`, `segment_results`, `Protocol Segment Gate`, baseline, motion, recovery | Pass |
| GUI quality TDD red check | `conda run -n sensor python -m pytest tests/test_gui_quality.py -q` before implementation | Missing GUI quality builder | `ModuleNotFoundError: ads1292_studio.gui_quality` | Pass |
| GUI quality tests | `conda run -n sensor python -m pytest tests/test_gui_quality.py -q` | GUI quality text and live readiness tests pass | 3 passed | Pass |
| GUI quality full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 49 passed | Pass |
| GUI quality syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/gui_quality.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| GUI quality real CSV smoke | `PYTHONPATH=src conda run -n sensor python -c "... build_quality_text(...)"` | Real CSV quality text includes segment gate | `Gate Pass ... Segment Gate Pass` | Pass |
| Quality gate sidecar TDD red check | `conda run -n sensor python -m pytest tests/test_quality_gate.py tests/test_session_package.py -q` before implementation | Missing quality gate sidecar helpers | Import failures for JSON helper functions | Pass |
| GUI quality gate config red check | `conda run -n sensor python -m pytest tests/test_gui_quality_gate_config.py -q` before implementation | Missing GUI quality gate parser | Import failure for `_quality_gate_from_values` | Pass |
| Quality gate sidecar tests | `conda run -n sensor python -m pytest tests/test_gui_quality_gate_config.py tests/test_quality_gate.py tests/test_session_package.py -q` | GUI/gate/package tests pass | 10 passed | Pass |
| Quality gate full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 53 passed | Pass |
| Quality gate syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py src/ads1292_studio/quality_gate.py src/ads1292_studio/session_package.py` | No syntax errors | Passed | Pass |
| Quality gate real package smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package reports/quality-gate-package-smoke/package-source.csv --out packages/quality-gate-smoke --title ADS1292-Quality-Gate-Package-Smoke` | Manifest and report include quality gate sidecar/settings and real CSV quality | grep found `quality_gate`, `"role": "quality_gate"`, `max_noise_rms_counts`, `Quality Gate`, `Protocol Segment Gate`, `CH2`, and `Good ECG/QRS` | Pass |
| Session index TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` before implementation | Missing session index module | `ModuleNotFoundError: ads1292_studio.session_index` | Pass |
| Session index focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` | Session index and CLI tests pass | 3 passed | Pass |
| Session index real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-smoke --title ADS1292-Real-Session-Index` | Real recording folder exports index | `rows=9`; grep found `CH2`, `Good ECG/QRS`, `Usable recordings`, and `2026-06-18-164923` | Pass |
| Session index full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 56 passed | Pass |
| Session index syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py src/ads1292_studio/cli.py src/ads1292_studio/session_index.py` | No syntax errors | Passed | Pass |
| Session index sidecar TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py -q` before implementation | Missing sidecar completeness fields | `AttributeError: 'SessionIndexRow' object has no attribute 'sidecar_status'` | Pass |
| Session index sidecar focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py -q` | Sidecar status tests pass | 3 passed | Pass |
| Session index sidecar CLI/smoke tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` plus real `index ../record/ads1292` smoke | CSV/HTML include sidecar status and missing sidecars | 4 passed; grep found `sidecar_status`, `Missing Sidecars`, and missing sidecar lists | Pass |
| Session index sidecar full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 57 passed | Pass |
| Session index sidecar syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py` | No syntax errors | Passed | Pass |
| Session index package-ready TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py -q` before implementation | Missing package-ready status fields | `AttributeError: 'SessionIndexRow' object has no attribute 'package_ready_status'` and missing CSV column | Pass |
| Session index package-ready focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py -q` | Package-ready status tests pass | 4 passed | Pass |
| Session index package-ready CLI/smoke tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` plus real `index ../record/ads1292` smoke | CSV/HTML include package-ready status and real folder exports | 5 passed; real smoke wrote 9 rows with `Package Ready`, `package_ready_status`, `Good ECG/QRS`, and `incomplete_record` | Pass |
| Session index package-ready full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 58 passed | Pass |
| Session index package-ready syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py` | No syntax errors | Passed | Pass |
| Session index summary TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` before implementation | Missing summary object and CLI summary lines | `AttributeError: 'SessionIndexExport' object has no attribute 'summary'`; missing `package_ready=0` output | Pass |
| Session index summary focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` | Summary object, HTML text, and CLI output pass | 6 passed | Pass |
| Session index summary full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 59 passed | Pass |
| Session index summary syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py src/ads1292_studio/cli.py` | No syntax errors | Passed | Pass |
| Session index summary real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-summary-smoke --title ADS1292-Session-Index-Summary-Smoke` | Real folder summary counts are printed and HTML contains summary text | `rows=9`, `package_ready=0`, `incomplete_records=9`, `needs_signal_review=0`; HTML contains package-ready summary line | Pass |
| Session index next-action TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py -q` before implementation | Missing next-action fields | `AttributeError: 'SessionIndexRow' object has no attribute 'next_action'`; missing CSV column | Pass |
| Session index next-action focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py -q` | Row, CSV, and HTML next-action tests pass | 6 passed | Pass |
| Session index next-action full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 60 passed | Pass |
| Session index next-action syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py` | No syntax errors | Passed | Pass |
| Session index next-action real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-action-smoke --title ADS1292-Session-Action-Smoke` | Real folder exports next-action guidance | `rows=9`; CSV/HTML include `Next Action`; all rows have `complete_sidecars` | Pass |
| Session index action-summary TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` before implementation | Missing action summary counts | `AttributeError: 'SessionIndexSummary' object has no attribute 'action_package_record'`; missing CLI action lines | Pass |
| Session index action-summary focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` | Summary, HTML, and CLI action counts pass | 7 passed | Pass |
| Session index action-summary full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 60 passed | Pass |
| Session index action-summary syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py src/ads1292_studio/cli.py` | No syntax errors | Passed | Pass |
| Session index action-summary real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-action-summary-smoke --title ADS1292-Action-Summary-Smoke` | Real folder action queue counts are printed and HTML contains summary text | `rows=9`, `action_package_record=0`, `action_complete_sidecars=9`, `action_review_signal=0` | Pass |
| GUI session index message TDD red check | `conda run -n sensor python -m pytest tests/test_gui_session_index.py -q` before implementation | Missing GUI session index message helper | `ModuleNotFoundError: No module named 'ads1292_studio.gui_session_index'` | Pass |
| GUI session index message focused test | `conda run -n sensor python -m pytest tests/test_gui_session_index.py -q` | GUI message includes readiness and action queue counts | 1 passed | Pass |
| GUI session index message full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 61 passed | Pass |
| GUI session index message syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/gui_session_index.py src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| GUI session index message real folder smoke | `PYTHONPATH=src conda run -n sensor python -c "... build_session_index_message(export) ..."` | Real folder GUI message includes queue counts | Message printed `Indexed 9 recordings`, `Package-ready: 0`, `Incomplete records: 9`, `Complete sidecars: 9` | Pass |
| Sidecar plan TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` before implementation | Missing sidecar plan fields and CLI output | `AttributeError: 'SessionIndexExport' object has no attribute 'sidecar_plan_csv_path'`; missing `sidecar_plan_csv=` output | Pass |
| Sidecar plan focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` | Session index writes sidecar plan CSV/HTML and CLI prints paths/counts | 8 passed | Pass |
| GUI sidecar plan message red check | `conda run -n sensor python -m pytest tests/test_gui_session_index.py -q` before GUI message implementation | GUI message omitted sidecar plan task count and paths | Missing `Sidecar plan rows` text | Pass |
| Sidecar plan GUI/session focused tests | `conda run -n sensor python -m pytest tests/test_gui_session_index.py tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` | GUI message and session index sidecar plan tests pass | 9 passed | Pass |
| Sidecar plan full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 62 passed | Pass |
| Sidecar plan syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py src/ads1292_studio/cli.py src/ads1292_studio/gui_session_index.py` | No syntax errors | Passed | Pass |
| Sidecar plan real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-sidecar-plan-smoke --title ADS1292-Sidecar-Plan-Smoke` | Real folder writes sidecar completion checklist | `rows=9`, `sidecar_plan_rows=45`, `action_complete_sidecars=9`; CSV lists metadata/events/calibration/protocol/quality_gate targets | Pass |
| Sidecar template bundle TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library tests/test_gui_session_index.py -q` before implementation | Missing template bundle fields and CLI/GUI output | `AttributeError: 'SessionIndexExport' object has no attribute 'sidecar_template_dir'`; missing `sidecar_template_dir=` and `Sidecar template files` output | Pass |
| Sidecar template bundle focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library tests/test_gui_session_index.py -q` | Session index stages sidecar templates and reports bundle paths/counts | 10 passed | Pass |
| Sidecar template bundle full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 63 passed | Pass |
| Sidecar template bundle syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py src/ads1292_studio/cli.py src/ads1292_studio/gui_session_index.py` | No syntax errors | Passed | Pass |
| Sidecar template bundle real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-template-bundle-smoke --title ADS1292-Template-Bundle-Smoke` | Real folder writes staged sidecar templates in report output only | `rows=9`, `sidecar_plan_rows=45`, `sidecar_template_files=45`; protocol template contains MOTAC ECG validation; target recording sidecar remained absent | Pass |
| Sidecar plan template-path TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` before implementation | Sidecar plan lacked `template_path` column and values | Missing `relative_path,sidecar,target_path,template_path,suggested_action`; missing staged template path in CLI plan CSV | Pass |
| Sidecar plan template-path focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library -q` | Sidecar plan CSV/HTML include template paths | 9 passed | Pass |
| Sidecar plan template-path full tests | `conda run -n sensor python -m pytest -q` | All tests pass | 63 passed | Pass |
| Sidecar plan template-path syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py src/ads1292_studio/cli.py src/ads1292_studio/gui_session_index.py` | No syntax errors | Passed | Pass |
| Sidecar plan template-path real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-template-path-smoke --title ADS1292-Template-Path-Smoke` | Real folder sidecar plan maps targets to staged templates | `rows=9`, `sidecar_plan_rows=45`, `sidecar_template_files=45`; CSV/HTML include `Template Path` and `sidecar-templates` paths | Pass |
| Sidecar apply script TDD red check | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library tests/test_gui_session_index.py -q` before implementation | Missing sidecar apply script export and CLI/GUI output | `AttributeError: 'SessionIndexExport' object has no attribute 'sidecar_apply_script_path'`; missing `sidecar_apply_script=` and `Apply sidecars script:` | Pass |
| Sidecar apply script focused tests | `conda run -n sensor python -m pytest tests/test_session_index.py tests/test_cli.py::test_cli_index_writes_session_library tests/test_gui_session_index.py -q` | Session index writes executable apply script and CLI/GUI expose it | 11 passed | Pass |
| Sidecar apply script real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-apply-script-smoke --title ADS1292-Apply-Script-Smoke` | Real folder writes apply script for reviewed sidecar templates | `rows=9`, `sidecar_plan_rows=45`, `sidecar_template_files=45`; script is executable and contains `cp -n` commands | Pass |
| Sidecar apply script full tests | `conda run -n sensor python -m pytest -q` | All tests pass after apply-script export | 64 passed | Pass |
| Sidecar apply script syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/session_index.py src/ads1292_studio/cli.py src/ads1292_studio/gui_session_index.py` | No syntax errors | Passed | Pass |
| Sidecar apply script final real folder smoke | `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli index ../record/ads1292 --out reports/session-index-apply-script-smoke-final --title ADS1292-Apply-Script-Smoke-Final` | Real folder script uses absolute paths and is executable | `rows=9`, `sidecar_plan_rows=45`, `sidecar_template_files=45`; `-rwxr-xr-x`; script contains absolute `cp -n` paths | Pass |
| GUI scroll sidebar TDD red check | `conda run -n sensor python -m pytest tests/test_gui_scroll.py -q` before implementation | Missing scrollable sidebar implementation | `ImportError: cannot import name 'ScrollableFrame'` | Pass |
| GUI scroll mousewheel red check | `conda run -n sensor python -m pytest tests/test_gui_scroll.py -q` before mousewheel fix | Missing small-delta mousewheel helper | `ImportError: cannot import name '_mousewheel_units'` | Pass |
| GUI scroll sidebar focused test | `conda run -n sensor python -m pytest tests/test_gui_scroll.py -q` | ScrollableFrame source includes Canvas/scrollbar; mousewheel helper handles small macOS deltas and X11 buttons | 2 passed | Pass |
| GUI scroll related tests | `conda run -n sensor python -m pytest tests/test_gui_quality.py tests/test_gui_quality_gate_config.py tests/test_gui_session_index.py tests/test_gui_scroll.py -q` | GUI helper tests pass after sidebar scroll and wheel fixes | 8 passed | Pass |
| GUI scroll syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| GUI information architecture TDD red check | `conda run -n sensor python -m pytest tests/test_gui_layout.py -q` before implementation | Missing task-based GUI layout helpers | `ImportError: cannot import name 'primary_toolbar_button_labels'` | Pass |
| GUI information architecture focused test | `conda run -n sensor python -m pytest tests/test_gui_layout.py -q` | Toolbar button labels, secondary action labels, and sidebar tabs match the mature GUI layout contract | 3 passed | Pass |
| GUI information architecture related tests | `conda run -n sensor python -m pytest tests/test_gui_quality.py tests/test_gui_quality_gate_config.py tests/test_gui_session_index.py tests/test_gui_scroll.py tests/test_gui_layout.py -q` | Existing GUI helpers still pass after task-based sidebar reorganization | 11 passed | Pass |
| GUI information architecture syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| GUI information architecture full tests | `conda run -n sensor python -m pytest -q` | All tests pass after toolbar/sidebar reorganization | 69 passed | Pass |
| GUI information architecture final syntax/diff checks | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py src/ads1292_studio/gui_quality.py src/ads1292_studio/gui_session_index.py`; `git diff --check` | No syntax errors and no whitespace errors | Passed | Pass |
| GUI control-state TDD red check | `conda run -n sensor python -m pytest tests/test_gui_control_state.py -q` before implementation | Missing deterministic GUI control-state helper | `ImportError: cannot import name 'gui_control_states'` | Pass |
| GUI control-state focused test | `conda run -n sensor python -m pytest tests/test_gui_control_state.py -q` | Button states match disconnected, connected, streaming, and loaded-data workflows | 4 passed | Pass |
| GUI control-state related tests | `conda run -n sensor python -m pytest tests/test_gui_quality.py tests/test_gui_quality_gate_config.py tests/test_gui_session_index.py tests/test_gui_scroll.py tests/test_gui_layout.py tests/test_gui_control_state.py -q` | Existing GUI helper/layout tests pass after state gating | 15 passed | Pass |
| GUI control-state syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| GUI control-state full tests | `conda run -n sensor python -m pytest -q` | All tests pass after button state gating | 73 passed | Pass |
| GUI control-state final syntax/diff checks | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py src/ads1292_studio/gui_quality.py src/ads1292_studio/gui_session_index.py`; `git diff --check` | No syntax errors and no whitespace errors | Passed | Pass |
| GUI workflow hint TDD red check | `conda run -n sensor python -m pytest tests/test_gui_control_state.py -q` before implementation | Missing workflow hint helper | `ImportError: cannot import name 'gui_workflow_hint'` | Pass |
| GUI workflow hint focused test | `conda run -n sensor python -m pytest tests/test_gui_control_state.py -q` | Control states and next-step hints match disconnected, connected, streaming, loaded-data, and package-ready workflows | 9 passed | Pass |
| GUI workflow hint related tests | `conda run -n sensor python -m pytest tests/test_gui_quality.py tests/test_gui_quality_gate_config.py tests/test_gui_session_index.py tests/test_gui_scroll.py tests/test_gui_layout.py tests/test_gui_control_state.py -q` | Existing GUI helper/layout tests pass after adding Status-tab workflow hint | 20 passed | Pass |
| GUI workflow hint syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| GUI workflow hint full tests | `conda run -n sensor python -m pytest -q` | All tests pass after Status-tab workflow hint | 78 passed | Pass |
| GUI workflow hint final syntax/diff checks | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py src/ads1292_studio/gui_quality.py src/ads1292_studio/gui_session_index.py`; `git diff --check` | No syntax errors and no whitespace errors | Passed | Pass |
| GUI status overview TDD red check | `conda run -n sensor python -m pytest tests/test_gui_control_state.py -q` before implementation | Missing compact status overview helper | `ImportError: cannot import name 'gui_status_overview'` | Pass |
| GUI status overview focused test | `conda run -n sensor python -m pytest tests/test_gui_control_state.py -q` | Control states, next-step hints, and Connection/Acquisition/Data/Package overview match disconnected, connected, streaming, loaded-data, and package-ready workflows | 13 passed | Pass |
| GUI status overview related tests | `conda run -n sensor python -m pytest tests/test_gui_quality.py tests/test_gui_quality_gate_config.py tests/test_gui_session_index.py tests/test_gui_scroll.py tests/test_gui_layout.py tests/test_gui_control_state.py -q` | Existing GUI helper/layout tests pass after adding Status-tab Overview | 24 passed | Pass |
| GUI status overview syntax compile | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py` | No syntax errors | Passed | Pass |
| GUI status overview full tests | `conda run -n sensor python -m pytest -q` | All tests pass after adding Status-tab Overview | 82 passed | Pass |
| GUI status overview final syntax/diff checks | `PYTHONPATH=src conda run -n sensor python -m py_compile src/ads1292_studio/app.py src/ads1292_studio/gui_quality.py src/ads1292_studio/gui_session_index.py`; `git diff --check` | No syntax errors and no whitespace errors | Passed | Pass |

## Error Log
| Timestamp | Error | Attempt | Resolution |
|-----------|-------|---------|------------|
| 2026-06-18 | Root project is not a git repository | 1 | Use an isolated git repository under `ads1292-studio/`. |
| 2026-06-18 | TDD red test failed with missing package imports | 1 | Expected red state; implemented package modules. |
| 2026-06-18 | Real saved CSV regression selected CH1 instead of CH2 | 1 | Root cause was sharpness-only score; added valid R-R count into source selection. |
| 2026-06-18 | GitHub push cannot proceed because `gh auth status` reports invalid token for `omnihola` | 1 | Local repo remains committed; re-authenticate with `gh auth login -h github.com`, then push. |
| 2026-06-18 | GitHub CLI still reports invalid token after user says GitHub login is done | 2 | Browser login did not update CLI token; use `gh auth login -h github.com`. |
| 2026-06-18 | Sandboxed `gh auth status` was misleading relative to external keychain auth | 3 | Used escalated shell for GitHub commands; upload succeeded. |
| 2026-06-18 | `conda run` with heredoc did not write smoke-test metadata JSON | 1 | Re-ran metadata sidecar creation with `python -c`, then batch smoke passed. |
| 2026-06-18 | GUI buffer clear code was unreachable after a `return` | 1 | Moved deque clearing into `_clear_buffers()` and covered the iteration with syntax/full tests. |
| 2026-06-18 | CLI tests rejected calibration options | 1 | Added `--calibration` and `--write-calibration-template` to the report subcommand. |
| 2026-06-18 | Session package module did not exist | 1 | Added `session_package.py`, CLI command, GUI export, and package tests. |
| 2026-06-18 | `packages/` output was initially unignored | 1 | Added `packages/` to `.gitignore`. |
| 2026-06-18 | Package verification API did not exist | 1 | Added `verify_session_package`, CLI `verify-package`, GUI Verify Package, and tamper test. |
| 2026-06-18 | Synthetic QC fixture failed default QRS gate | 1 | Added explicit `--allow-unclear-qrs` option for synthetic/debug records and kept default real-data gate strict. |
| 2026-06-18 | Pytest warned that `TestProtocol` looked like a test class | 1 | Added `__test__ = False` to the dataclass. |
| 2026-06-18 | Temporary protocol sidecar was copied outside `ads1292-studio/` during smoke setup | 1 | Removed it immediately and reran package smoke with ignored files inside `reports/`. |
| 2026-06-18 | `conda run` reports nonzero QC failure smoke as a command failure | 1 | Treated exit code 2 as the expected strict-threshold result and verified a loose-threshold pass path separately. |
| 2026-06-18 | Per-segment Auto source selected CH1 for the motion segment in real smoke | 1 | Fixed report segment analysis to reuse the whole-record ECG source, so all protocol stages compare the same channel. |
| 2026-06-18 | Initial segment gate test used a fixed noise limit that did not fail the synthetic motion segment | 1 | Changed the test to derive the threshold between measured baseline and motion noise. |
| 2026-06-18 | Empty segment gate emitted redundant contact/R-peak failures | 1 | Short-circuited no-data segment evaluation so the failure is specific. |
| 2026-06-18 | `dataclasses.asdict()` omitted computed `label`/`status` properties from segment gate manifest output | 1 | Added an explicit manifest serializer for segment gate results. |
| 2026-06-18 | GUI quality text did not expose protocol segment gate results | 1 | Added a testable GUI quality text builder and wired it into live/offline review. |
| 2026-06-18 | Live GUI could mark future protocol steps as failed before enough data was collected | 1 | Added live protocol readiness gating before showing Segment Gate in the sidebar. |
| 2026-06-18 | Quality gate JSON helper imports were missing during TDD red check | 1 | Added normalized sidecar template/read/write helpers and package support. |
| 2026-06-18 | GUI quality gate parser helper was missing during TDD red check | 1 | Added explicit parser/formatter helpers for GUI gate fields. |
| 2026-06-18 | Session index module was missing during TDD red check | 1 | Added recursive session index export plus CLI and GUI entry points. |
| 2026-06-18 | Initial session index fixture was too short/sparse to be classified usable | 1 | Reused the established 7-second ECG-like synthetic waveform from batch tests. |
| 2026-06-18 | Session index sidecar fields were missing during TDD red check | 1 | Added sidecar status and missing sidecar fields to row, CSV, and HTML output. |
| 2026-06-18 | Session index package-ready field was missing during TDD red check | 1 | Added package-ready status to row model, CSV export, and HTML export. |
| 2026-06-18 | Session index summary fields were missing during TDD red check | 1 | Added `SessionIndexSummary`, HTML summary text, and CLI summary output. |
| 2026-06-18 | Session index next-action field was missing during TDD red check | 1 | Added `next_action` to row model, CSV export, and HTML export. |
| 2026-06-18 | Session index action-summary fields were missing during TDD red check | 1 | Added next-action counts to summary, HTML export, and CLI output. |
| 2026-06-18 | GUI session index message helper was missing during TDD red check | 1 | Added `gui_session_index.py` and wired it into `app.session_index()`. |
| 2026-06-18 | CodeGraph is not initialized in `ads1292-studio/` | 1 | Used direct file reads for Phase 29 context and logged the missing index. |
| 2026-06-18 | Session index sidecar plan fields were missing during TDD red check | 1 | Added `SidecarPlanRow`, CSV/HTML plan exports, CLI output, and GUI message fields. |
| 2026-06-18 | GUI sidecar plan test expected 5 missing rows for a fixture that already had metadata | 1 | Corrected the expected count to 4 because `_write_recording()` creates metadata JSON. |
| 2026-06-18 | CodeGraph remains uninitialized in `ads1292-studio/` | 2 | Used direct file reads for Phase 30 context and kept the limitation documented. |
| 2026-06-18 | Session index sidecar template bundle fields were missing during TDD red check | 1 | Added staged template bundle paths, template file generation, CLI output, and GUI message fields. |
| 2026-06-18 | CodeGraph remains uninitialized in `ads1292-studio/` | 3 | Used direct file reads for Phase 31 context and kept the limitation documented. |
| 2026-06-18 | Sidecar plan lacked staged template paths during TDD red check | 1 | Added `template_path` to `SidecarPlanRow`, CSV output, HTML output, and tests. |
| 2026-06-18 | CodeGraph remains uninitialized in `ads1292-studio/` | 4 | Used direct file reads for Phase 32 context and kept the limitation documented. |
| 2026-06-18 | Sidecar apply script export was missing during TDD red check | 1 | Added `sidecar_apply_script_path`, executable script generation, CLI output, and GUI confirmation text. |
| 2026-06-18 | CodeGraph remains uninitialized in `ads1292-studio/` | 5 | Used direct file reads for Phase 33 context and kept the limitation documented. |
| 2026-06-18 | Left sidebar was a non-scrollable plain frame | 1 | Added `ScrollableFrame` and moved the sidebar controls into its content frame. |
| 2026-06-18 | Live Tk widget pytest aborted under macOS Tk | 1 | Replaced it with a stable source-level layout test and kept GUI syntax/helper verification. |
| 2026-06-18 | Sidebar mouse wheel still did not scroll reliably | 1 | Added `_mousewheel_units()` for small macOS deltas and pointer-gated global wheel handling for child widgets. |
| 2026-06-18 | GUI was feature-rich but still too crowded for simple operation | 1 | Reorganized the sidebar into task tabs and moved secondary file/export/library actions out of the acquisition toolbar. |
| 2026-06-18 | GUI exposed impossible actions as clickable buttons | 1 | Added `gui_control_states()` and `_apply_control_states()` so buttons enable only when their workflow prerequisites are met. |
| 2026-06-18 | Disabled GUI controls did not explain the next valid action | 1 | Added `gui_workflow_hint()` and a Status-tab `Next Step` field updated with the same state model as the buttons. |
| 2026-06-18 | Status tab still lacked a stable state snapshot separate from the next-action hint | 1 | Added `gui_status_overview()` and a Status-tab `Overview` field for Connection, Acquisition, Data, and Package readiness. |

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 37 complete; ready to commit and push the GUI status-overview iteration. |
| Where am I going? | Continue iterative polish and bug elimination in `ads1292-studio/`. |
| What's the goal? | Build a robust ADS1292 Studio GUI/app for MOTAC ECG validation. |
| What have I learned? | CH2 can carry the clear ECG-like QRS in the saved run; low-nibble lead-off bits are the safer contact flag. |
| What have I done? | Built, tested, locally committed, and pushed V1 app; added report export, metadata audit trail, batch comparison, event markers, calibration/uV display, session packages, package verification, quality gates, protocol sidecars, batch group statistics, artifact metrics, artifact threshold gates, protocol segment metrics, protocol segment quality gates, GUI segment visibility, GUI quality gate sidecars, session index export, session sidecar completeness audit, package-ready session index status, session index readiness summary counts, per-record next-action guidance, next-action queue counts, GUI session index summary confirmation, session index sidecar completion-plan exports, staged sidecar template bundle exports, sidecar plan template-path traceability, executable sidecar apply-script exports, mousewheel-scrollable left-sidebar controls, a task-based GUI sidebar with a focused acquisition toolbar, GUI button state gating, Status-tab workflow hints, and a Status-tab state overview. |
