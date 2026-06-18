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

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Old Windows TI GUI is unreliable under Parallels/Windows 11 ARM | Build native macOS Python app instead. |
| Existing GUI was too minimal and visually misleading | New app will expose channel source, quality metrics, offline review, and diagnostics. |
| Root folder is not a git repository | Initialize a repository only in the new subfolder. |
| Auto source initially selected CH1 on the real saved CSV | Fixed by including valid R-R count in channel selection instead of only derivative sharpness. |
| GitHub upload cannot continue with current auth | Re-run after `gh auth login -h github.com` refreshes the token. |

## Resources
- Existing reference implementation: `tools/ads1292_mac/ads1x9x.py`
- Existing GUI reference: `tools/ads1292_mac/ads1x9x_gui.py`
- Project target: `target.md`
- Sample data for offline tests: `record/ads1292/2026-06-18-164923-ads1292-live.csv`
- Planning file: `ads1292-studio/task_plan.md`
- Superpowers plan: `ads1292-studio/docs/superpowers/plans/2026-06-18-ads1292-studio-v1.md`

## Visual/Browser Findings
- The user-provided ECG reference image shows repeated sharp R/QRS spikes around a slowly varying baseline.
- Generated review figures from the saved CSV show CH2 has repeated sharp QRS-like spikes, while CH1 can look flat/noisy depending on the time window.
- R-aligned average from CH2 shows a strong R/QRS complex; P and T are too small/unstable to report as validated morphology.

---
*Update this file after every 2 view/browser/search operations.*
