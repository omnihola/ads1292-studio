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
```

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
- Testable signal-analysis core independent of live hardware.

## Safety

Use a battery-powered laptop for body-contact tests. Do not charge the laptop
during recording and do not connect other earth-referenced instruments to the
subject.
