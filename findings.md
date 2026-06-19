# Findings & Decisions

## Requirements
- Create a dedicated subfolder and perform work inside it.
- Continue improving the ADS1292RECG-FE GUI toward commercial-quality software.
- Use Superpowers and planning-with-files for design/progress records.
- Iterate toward bug elimination, not a one-off script.
- Prepare for GitHub upload limited to this subfolder.
- Keep the software aligned with the MOTAC gel ECG validation project.

## Research Findings
- Existing macOS path talks to ADS1292RECG-FE as USB CDC serial device named `ADS1x9x - ECG Recorder`.
- Existing serial protocol uses framed commands with start `0x02`, end `0x03`, data-stream toggle `0x93`, firmware query `0x99`.
- Streaming frames include board HR, respiration rate, status/lead-off byte, and 14 pairs of signed 16-bit samples.
- Saved CSV `record/ads1292/2026-06-18-164923-ads1292-live.csv` contains 75.46 s at 500 Hz.
- That saved run has nearly all lead-off low-nibble bits at 0, so electrode contact was mostly valid.
- In that run, clear ECG-like QRS spikes appear mainly in the second streamed field (`resp_counts`/CH2), not CH1.
- PQRST check from that run: R/QRS is clear; P and T are not reliable enough to claim as full morphology evidence.
- `target.md` defines this project as a soft, humectant, ionically conductive skin-electrode interface for long-duration ECG monitoring with stack `skin / MOTAC:glycerol:H2O:LiCl gel / Ag-AgCl current collector / flexible backing / snap or wire`.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Preserve raw CH1 and CH2 in all recordings | Channel interpretation may differ by board mode/electrode wiring; raw evidence must remain inspectable. |
| Derive `lead_off_bits` from `status_byte & 0x0F` | Avoids false disconnect warnings from high status bits such as `0x10`. |
| Add offline CSV review as V1 feature | It enables testing and debugging without needing the board attached. |
| Add QRS-like channel auto-selection | User data showed ECG was visible in CH2 while CH1 was misleading. |
| Store planning files in `ads1292-studio/` | Keeps work self-contained and GitHub-ready. |
| Combine QRS sharpness with valid R-R count for Auto source | Real data showed CH1 can contain sharper but sparse artifacts while CH2 has regular ECG peaks. |
| Upload with `gh` after authentication | `gh` is installed, but current token for `omnihola` is invalid. |
| Add HTML/PNG report export | Experiment review needs portable records with ECG source, HR, contact quality, and PQRST/QRS notes. |
| Push succeeded via sandbox-external `gh` | Repo is `https://github.com/omnihola/ads1292-studio`, created private and tracking `origin/main`. |
| Add session metadata JSON | Anonymous subject ID, electrode, montage, operator, and notes need to travel with reports for comparable experiments. |
| Add batch comparison summary | Commercial/MOTAC/formulation comparison needs cohort-level CSV/HTML/PNG summaries instead of one file at a time. |
| Add event marker sidecars | Time-aligned protocol events make motion artifacts, deep-breath tests, electrode touch, or posture changes auditable in reports. |
| Keep buffer clearing in `_clear_buffers()` | GUI Start/Load cycles must clear previous samples, status, HR/RR, and event markers before a new session. |
| Add calibration sidecars | Raw counts alone are not enough for auditable ECG review; Vref, gain, ADC bits, and uV/count must be recorded. |
| Add session package manifest | A complete experiment record should bundle raw CSV, sidecars, report outputs, metrics, bytes, and SHA256 checksums. |
| Add package verification | The package manifest should not only record hashes; the app must verify them after transfer or archive. |
| Add quality gate | Electrode validation needs explicit pass/fail gates for contact, duration, QRS, R peaks, and HR bounds. |
| Add protocol sidecars | Commercial-quality gel validation needs the planned baseline, motion, and recovery steps saved with each recording. |
| Add batch group statistics | Material comparisons need electrode-level summaries before claiming MOTAC vs commercial performance. |
| Add artifact metrics | Baseline drift and noise are core electrode-quality evidence for MOTAC vs commercial ECG tests. |
| Add artifact threshold gates | Drift/noise metrics need configurable pass/fail limits for repeatable material validation. |
| Add protocol segment metrics | Baseline, motion, and recovery stages need separate contact, R-peak, HR, drift, noise, and peak-to-peak evidence. |
| Keep report segment metrics on the whole-record ECG source | A report must not compare baseline CH2 against motion CH1 just because per-segment Auto changed channels. |
| Add protocol segment quality gates | Reports, manifests, and CLI QC should name the failed protocol stage so motion/recovery problems are not hidden inside whole-record averages. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Old Windows TI GUI is unreliable under Parallels/Windows 11 ARM | Build native macOS Python app instead. |
| Existing GUI was too minimal and visually misleading | New app will expose channel source, quality metrics, offline review, and diagnostics. |
| Root folder is not a git repository | Initialize a repository only in the new subfolder. |
| Auto source initially selected CH1 on the real saved CSV | Fixed by including valid R-R count in channel selection instead of only derivative sharpness. |
| GitHub upload cannot continue with current auth | Re-run after `gh auth login -h github.com` refreshes the token. |
| Browser login did not refresh GitHub CLI | `gh auth status` still reports invalid token for `omnihola`; CLI-specific re-auth is required. |
| Sandboxed GitHub auth result was misleading | Escalated shell saw valid keychain auth and push succeeded. |
| `conda run` heredoc smoke step did not create metadata sidecars | Use `python -c` or a script file for smoke setup when running through `conda run`. |
| GUI buffer clearing was unreachable | The deque clearing loop was after a `return` in `_metadata()`; moved it to `_clear_buffers()`. |
| CLI calibration options were initially absent | TDD caught missing parser options before implementation; added template and report input flags. |
| Session package output can pollute git | Generated `packages/` artifacts should be ignored like `reports/` and `recordings/`. |
| Package verify was missing after manifest export | Added a verifier so modified/missing files are detected instead of silently trusted. |
| Synthetic QC data can fail strict QRS checks | Keep default QC strict for real recordings, but allow `--allow-unclear-qrs` for debug fixtures. |
| Protocol sidecar smoke setup briefly touched the parent `record/` folder | Removed the temporary file and reran smoke using ignored files inside `ads1292-studio/reports/`. |
| Per-segment Auto source selected CH1 for the motion segment in real smoke | Fixed report segment analysis to reuse the whole-record ECG source, so all protocol stages compare the same channel. |

## Resources
- Existing reference implementation: `tools/ads1292_mac/ads1x9x.py`
- Existing GUI reference: `tools/ads1292_mac/ads1x9x_gui.py`
- Project target: `target.md`
- Sample data for offline tests: `record/ads1292/2026-06-18-164923-ads1292-live.csv`
- Planning file: `ads1292-studio/task_plan.md`
- Superpowers plan: `ads1292-studio/docs/superpowers/plans/2026-06-18-ads1292-studio-v1.md`
- Report export command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --out reports`
- Metadata template command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-meta-template reports/session-template.json`
- Batch command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli batch file1.csv file2.csv --out reports/batch`
- Batch group output: batch export writes both per-recording CSV and `*-groups.csv`
- Events template command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-events-template reports/events-template.json`
- Event report command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --events reports/events-template.json --out reports`
- Calibration template command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-calibration-template reports/calibration-template.json`
- Calibration report command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --calibration reports/calibration-template.json --out reports`
- Session package command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli package <csv> --out packages`
- Session package verify command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli verify-package packages/<session>/manifest.json`
- Quality gate command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc <csv>`
- Artifact metrics command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli review <csv>`
- Artifact gate command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc <csv> --max-baseline-drift <counts> --max-noise-rms <counts> --max-peak-to-peak <counts>`
- Protocol template command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report --write-protocol-template reports/protocol-template.json`
- Protocol report command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli report <csv> --protocol reports/protocol-template.json --out reports`
- Protocol segment metrics are generated automatically when `--protocol` is supplied to `report` or when a `.protocol.json` sidecar is included in a session package.
- Protocol segment gate command: `PYTHONPATH=src conda run -n sensor python -m ads1292_studio.cli qc <csv> --protocol reports/protocol-template.json`

## Visual/Browser Findings
- The user-provided ECG reference image shows repeated sharp R/QRS spikes around a slowly varying baseline.
- Generated review figures from the saved CSV show CH2 has repeated sharp QRS-like spikes, while CH1 can look flat/noisy depending on the time window.
- R-aligned average from CH2 shows a strong R/QRS complex; P and T are too small/unstable to report as validated morphology.

---
*Update this file after every 2 view/browser/search operations.*
