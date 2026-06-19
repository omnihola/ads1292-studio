# Task Plan: ADS1292 Studio

## Goal
Build an isolated, GitHub-ready ADS1292RECG-FE desktop acquisition and analysis app under `ads1292-studio/`, with commercial-software direction: robust capture, dual-channel ECG display, quality diagnostics, saved records, offline review, tests, documentation, and iterative bug tracking.

## Current Phase
Phase 20

## Phases

### Phase 1: Requirements & Discovery
- [x] Capture user goal: create subfolder, continue GUI, feature-rich/commercial direction, use Superpowers and planning-with-files, prepare GitHub upload limited to this subfolder.
- [x] Read existing ADS1292 Python implementation in `tools/ads1292_mac`.
- [x] Read project target in `target.md`.
- [x] Document findings in `findings.md`.
- **Status:** complete

### Phase 2: Planning & Structure
- [x] Create isolated subfolder `ads1292-studio/`.
- [x] Create persistent planning files.
- [x] Create Superpowers implementation plan.
- [x] Initialize isolated git repository for this subfolder only.
- **Status:** complete

### Phase 3: Implementation V1
- [x] Move core ADS1x9x protocol code into focused modules.
- [x] Build reusable signal analysis functions for channel choice, filtering, R peak detection, HR, PQRST review, and quality flags.
- [x] Build a richer Tk/Matplotlib desktop GUI with live view, source selection, save status, session metadata, offline CSV loading, and quality metrics.
- [x] Add CLI entry points and shell launcher.
- [x] Add user-facing README.
- **Status:** complete

### Phase 4: Testing & Verification
- [x] Add pytest unit tests for parsing, signal processing, CSV IO, and sample-data analysis.
- [x] Run syntax checks.
- [x] Run test suite.
- [x] Verify offline sample CSV produces expected CH2 ECG detection and HR range.
- **Status:** complete

### Phase 5: GitHub Preparation
- [x] Add `.gitignore`, package metadata, and readme basics.
- [x] Commit only the `ads1292-studio/` repository.
- [x] Determine remote/upload path.
- [x] Push when remote is available and authenticated.
- **Status:** complete

### Phase 6: Report Export & Experiment Records
- [x] Add quality metric model for contact, HR, QRS, P/T, and source selection.
- [x] Add HTML + PNG report export for offline recordings.
- [x] Add CLI `report` command.
- [x] Add GUI `Export Report` button.
- [x] Add tests and smoke test against the real saved CSV.
- **Status:** complete

### Phase 7: Session Metadata & Audit Trail
- [x] Add session metadata model and JSON read/write.
- [x] Include metadata in HTML reports.
- [x] Add CLI metadata template generation and `--meta` report input.
- [x] Add GUI metadata fields and sidecar JSON save during recording.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 8: Batch Comparison
- [x] Add batch aggregation across multiple CSV recordings.
- [x] Read sidecar metadata for each CSV.
- [x] Export batch CSV, HTML, and PNG summary.
- [x] Add CLI `batch` command.
- [x] Add GUI `Batch Compare` button.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 9: Event Markers & Annotations
- [x] Add event marker model and JSON sidecar read/write.
- [x] Add CLI event template generation and report `--events` input.
- [x] Add GUI event label/notes fields and Add Event action.
- [x] Include event marker table in exported HTML reports.
- [x] Fix buffer clearing so repeated Start/Load cycles do not retain old samples.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 10: Calibration & Engineering Units
- [x] Add calibration model for Vref, PGA gain, ADC bits, and uV/count scale.
- [x] Add calibration JSON template/read/write helpers.
- [x] Convert report plots from raw counts to microvolts while preserving raw CSV.
- [x] Include calibration table in HTML reports.
- [x] Add CLI `--calibration` and `--write-calibration-template`.
- [x] Add GUI calibration fields plus `.calibration.json` sidecar save/load.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 11: Session Package & Audit Manifest
- [x] Add session package export that copies raw CSV and available sidecars.
- [x] Generate report inside the package.
- [x] Write manifest JSON with schema, metrics, bytes, and SHA256 checksums.
- [x] Add CLI `package` command.
- [x] Add GUI `Export Package` button.
- [x] Ignore generated `packages/` outputs.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 12: Package Integrity Verification
- [x] Add package manifest verification with byte and SHA256 checks.
- [x] Detect missing files and modified files.
- [x] Add CLI `verify-package` command.
- [x] Add GUI `Verify Package` button.
- [x] Add tests and real package smoke test.
- **Status:** complete

### Phase 13: Quality Gate & Acceptance Criteria
- [x] Add configurable quality gate thresholds.
- [x] Evaluate pass/fail from computed ECG quality metrics.
- [x] Include Quality Gate table in HTML reports.
- [x] Add CLI `qc` command with threshold options.
- [x] Display Quality Gate status in GUI quality text.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 14: Protocol Templates & Test Plan Sidecars
- [x] Add protocol JSON model for objective, operator instructions, steps, and acceptance notes.
- [x] Add MOTAC ECG validation protocol template.
- [x] Include protocol steps in HTML reports.
- [x] Add CLI `--write-protocol-template` and `--protocol` report options.
- [x] Copy protocol sidecars into session packages and manifests.
- [x] Add GUI protocol fields and `.protocol.json` sidecar save/load.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 15: Batch Group Statistics
- [x] Add electrode-level group summaries for batch rows.
- [x] Compute recordings, usable recordings, usable percent, mean duration, mean contact, mean R peaks, and mean HR.
- [x] Export grouped statistics to `*-groups.csv`.
- [x] Include Group Summary table in batch HTML reports.
- [x] Print grouped output path/count from CLI `batch`.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 16: Artifact & Baseline Drift Metrics
- [x] Add baseline drift metric from selected ECG channel.
- [x] Add noise RMS metric from selected ECG channel.
- [x] Add peak-to-peak metric from selected ECG channel.
- [x] Include artifact metrics in HTML reports.
- [x] Print artifact metrics in CLI `review` and `qc`.
- [x] Display drift/noise summary in GUI quality text.
- [x] Add tests and real CSV smoke test.
- **Status:** complete

### Phase 17: Artifact Threshold Quality Gates
- [x] Add configurable maximum baseline drift gate.
- [x] Add configurable maximum noise RMS gate.
- [x] Add configurable maximum peak-to-peak gate.
- [x] Add CLI `qc` threshold flags for artifact limits.
- [x] Add artifact metrics to session package manifest.
- [x] Add tests and real CSV pass/fail smoke tests.
- **Status:** complete

### Phase 18: Protocol Segment Metrics
- [x] Add protocol-step segment analysis for baseline, motion, and recovery windows.
- [x] Compute per-segment contact, R peaks, HR, baseline drift, noise RMS, and peak-to-peak values.
- [x] Include protocol segment metrics in HTML reports.
- [x] Include protocol segment metrics in session package manifests.
- [x] Keep report segment analysis on the whole-record ECG source so Auto does not switch channels between protocol steps.
- [x] Add tests and real CSV report/package smoke tests.
- **Status:** complete

### Phase 19: Protocol Segment Quality Gates
- [x] Add protocol segment gate evaluation for no-data, contact, R peaks, HR, baseline drift, noise RMS, and peak-to-peak failures.
- [x] Include Protocol Segment Gate status and per-segment failures in HTML reports.
- [x] Include segment gate status and per-segment failures in session package manifests.
- [x] Add CLI `qc --protocol` support using the same gate thresholds.
- [x] Add tests and real CSV report/package/CLI smoke tests.
- **Status:** complete

### Phase 20: GUI Protocol Segment Gate Visibility
- [x] Add testable GUI quality text builder.
- [x] Show protocol segment gate Pass/Fail in GUI quality text for offline protocol recordings.
- [x] Suppress live protocol segment gate evaluation until the live buffer covers the full protocol window.
- [x] Load event, calibration, and protocol sidecars before rendering loaded CSV data.
- [x] Add tests and real CSV GUI-quality smoke test.
- **Status:** complete

### Phase 21: GUI Quality Gate Presets & Sidecars
- [x] Add quality gate JSON template/read/write helpers.
- [x] Add GUI fields for duration, contact, R peaks, HR, QRS clarity, and artifact thresholds.
- [x] Save and load `.quality-gate.json` sidecars with recordings and loaded CSVs.
- [x] Use the GUI quality gate for live/offline quality text and report export.
- [x] Include quality gate sidecars in session packages and manifest metrics.
- [x] Add tests and real CSV package smoke test.
- **Status:** complete

## Key Questions
1. Can the first commercial-direction version run without the physical board? Yes: offline CSV review must work from existing saved CSV.
2. Which channel should be treated as ECG? Auto-detect by QRS-like score, with manual CH1/CH2 override. The 2026-06-18 16:49 run shows ECG-like QRS mainly on CH2.
3. Is this medical diagnostic software? No. It is research/evaluation software for ADS1292RECG-FE and MOTAC gel electrode validation.

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use new subfolder `ads1292-studio/` | User explicitly requested a subfolder and GitHub limited to that subfolder. |
| Keep Tk/Matplotlib for V1 | Existing sensor env already supports it; fastest path to working live hardware capture on macOS. |
| Separate live protocol from signal analysis and GUI | Makes testing possible without hardware and prevents GUI-only debugging. |
| Default ECG source to Auto with CH1/CH2 override | Saved data proves CH2 can contain clearer ECG-like QRS than the first streamed field. |
| Save both raw channels and derived metadata | Avoids losing evidence and allows later correction of display assumptions. |
| Combine QRS sharpness with valid R-R count for Auto source | Prevents sparse CH1 transients from beating a regular CH2 ECG signal. |
| Use GitHub CLI for upload when auth is fixed | `gh` is installed, but sandboxed auth checks can be misleading. |
| Use sandbox-external GitHub commands for upload | External keychain auth was valid and push succeeded. |
| Add session metadata sidecars | Commercial-style experiment software needs anonymous subject/electrode/montage/operator/notes tied to each recording and report. |
| Add batch comparison exports | Material validation requires comparing commercial Ag/AgCl controls, MOTAC gel, and formulation variants across repeated recordings. |
| Add event marker sidecars | ECG material tests need time-aligned notes for motion, breathing, electrode touch, posture, or protocol events. |
| Clear all buffers on Start/Load | Repeated GUI sessions must not mix old samples with current recordings. |
| Add calibration sidecars | Commercial-style acquisition must audit ADC Vref/gain/bit-depth and display engineering units, not only raw counts. |
| Add session package manifest | Research/commercial-style records need raw data, sidecars, report artifacts, and hashes tied together for later audit. |
| Add package verification | Auditable records must be re-checkable after transfer or Dropbox/GitHub storage. |
| Add quality gate | MOTAC vs commercial electrode tests need explicit pass/fail criteria instead of only descriptive metrics. |
| Add protocol sidecars | Commercial-style gel validation needs repeatable baseline, motion, and recovery steps attached to each recording. |
| Add batch group statistics | MOTAC vs commercial comparisons need electrode-level summaries, not only one row per recording. |
| Add artifact metrics | ECG electrode validation needs baseline drift and noise evidence, not only R peaks and contact flags. |
| Add artifact threshold gates | Once drift/noise are measured, QC needs explicit failure criteria for material comparison. |
| Add protocol segment metrics | Baseline/motion/recovery material validation needs per-step evidence, not only whole-record summaries. |
| Fix report segment analysis to the whole-record ECG source | Segment-to-segment comparisons are only meaningful when baseline, motion, and recovery use the same channel. |
| Add protocol segment quality gates | Commercial-style validation needs explicit pass/fail calls for each protocol stage, not only descriptive segment metrics. |
| Show segment gate in GUI quality text | A commercial-style desktop app should surface protocol pass/fail without requiring report export or CLI QC. |
| Add GUI quality gate sidecars | Pass/fail standards must be saved with the recording so a later report/package uses the same validation thresholds. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Root project is not a git repository | 1 | Plan to initialize git only inside `ads1292-studio/`. |
| Initial lead-off interpretation treated status byte `0x10` as disconnected | 1 | Use low nibble as `lead_off_bits`, keep full `status_byte` separately. |
| Initial analysis overemphasized CH1 and missed CH2 ECG-like QRS | 1 | Add channel auto-detection and offline review. |
| GitHub CLI token invalid for `omnihola` | 1 | Local repo committed; external push waits for `gh auth login -h github.com`. |
| GitHub CLI token still invalid after user browser login | 2 | Browser auth did not refresh `gh`; still need `gh auth login -h github.com` in CLI. |
| Sandboxed GitHub auth check was misleading | 3 | Ran `gh auth status` outside sandbox; authenticated as `omnihola`, created private repo, and pushed `main`. |
| `conda run` with heredoc did not execute smoke-test metadata writer | 1 | Replaced heredoc with `python -c` for sidecar JSON creation in smoke testing. |
| GUI `_clear_buffers()` did not clear deques | 1 | Buffer clearing code was unreachable after `_metadata()` return; moved deque clearing into `_clear_buffers()`. |
| CLI calibration options were missing after report calibration tests | 1 | Added `--calibration` and `--write-calibration-template`, then verified CLI tests. |
| `packages/` was not ignored initially | 1 | Added `packages/` to `.gitignore` before committing package smoke output. |
| Package verification function was missing | 1 | Added TDD tests, `verify_session_package`, CLI `verify-package`, and GUI Verify Package. |
| Initial quality gate test used short synthetic data | 1 | Made the test threshold explicit and added CLI `--allow-unclear-qrs` for debug/synthetic data. |
| Temporary protocol sidecar was copied outside the subfolder during smoke setup | 1 | Removed the file immediately and reran package smoke using only ignored files inside `ads1292-studio/`. |
| Quality gate sidecar helpers were missing | 1 | Added normalized `QualityGate` JSON read/write/template helpers and package integration. |
| GUI quality gate parser was missing | 1 | Added explicit GUI value parsing/formatting helpers for required and optional threshold fields. |

## Notes
- Do not touch unrelated project files except existing `tools/ads1292_mac` as read-only reference.
- Safety remains: battery-powered laptop, no charger, no earth-referenced instruments on subject.
- This plan is active and should be updated after every phase.
