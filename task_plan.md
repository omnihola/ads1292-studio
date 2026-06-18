# Task Plan: ADS1292 Studio

## Goal
Build an isolated, GitHub-ready ADS1292RECG-FE desktop acquisition and analysis app under `ads1292-studio/`, with commercial-software direction: robust capture, dual-channel ECG display, quality diagnostics, saved records, offline review, tests, documentation, and iterative bug tracking.

## Current Phase
Phase 5

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
- [ ] Push when remote is available and authenticated.
- **Status:** blocked by GitHub authentication

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
| Use GitHub CLI for upload when auth is fixed | `gh` is installed, but the current token for account `omnihola` is invalid. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Root project is not a git repository | 1 | Plan to initialize git only inside `ads1292-studio/`. |
| Initial lead-off interpretation treated status byte `0x10` as disconnected | 1 | Use low nibble as `lead_off_bits`, keep full `status_byte` separately. |
| Initial analysis overemphasized CH1 and missed CH2 ECG-like QRS | 1 | Add channel auto-detection and offline review. |
| GitHub CLI token invalid for `omnihola` | 1 | Local repo committed; external push waits for `gh auth login -h github.com`. |

## Notes
- Do not touch unrelated project files except existing `tools/ads1292_mac` as read-only reference.
- Safety remains: battery-powered laptop, no charger, no earth-referenced instruments on subject.
- This plan is active and should be updated after every phase.
