# Task Plan: ADS1292 Studio

## Goal
Build an isolated, GitHub-ready ADS1292RECG-FE desktop acquisition and analysis app under `ads1292-studio/`, with commercial-software direction: robust capture, dual-channel ECG display, quality diagnostics, saved records, offline review, tests, documentation, and iterative bug tracking.

## Current Phase
Phase 11

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

## Notes
- Do not touch unrelated project files except existing `tools/ads1292_mac` as read-only reference.
- Safety remains: battery-powered laptop, no charger, no earth-referenced instruments on subject.
- This plan is active and should be updated after every phase.
