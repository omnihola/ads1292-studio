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

## 5-Question Reboot Check
| Question | Answer |
|----------|--------|
| Where am I? | Phase 16 complete; ready to commit and push artifact metrics iteration. |
| Where am I going? | Continue iterative polish and bug elimination in `ads1292-studio/`. |
| What's the goal? | Build a robust ADS1292 Studio GUI/app for MOTAC ECG validation. |
| What have I learned? | CH2 can carry the clear ECG-like QRS in the saved run; low-nibble lead-off bits are the safer contact flag. |
| What have I done? | Built, tested, locally committed, and pushed V1 app; added report export, metadata audit trail, batch comparison, event markers, calibration/uV display, session packages, package verification, quality gates, protocol sidecars, batch group statistics, and artifact metrics. |
