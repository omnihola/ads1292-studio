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
- Auto / CH1 / CH2 ECG source selection.
- Live ECG, other channel, and lead-off/status display.
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

## Safety

Use a battery-powered laptop for body-contact tests. Do not charge the laptop
during recording and do not connect other earth-referenced instruments to the
subject.
