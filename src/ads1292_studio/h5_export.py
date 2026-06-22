"""On-demand exporters from the canonical HDF5 container.

The .h5 is the single source of truth; these helpers materialize the legacy
interchange formats (CSV / JSON / XLSX) only when the user asks for them.
"""
from __future__ import annotations

import json
from pathlib import Path

from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.h5_io import read_recording_h5
from ads1292_studio.recording_bundle import events_from_bundle


def export_h5_to_csv(h5_path: Path | str, out_path: Path | str) -> Path:
    recording, _ = read_recording_h5(h5_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_recording_csv(out, recording.samples)
    return out


def export_h5_to_json(h5_path: Path | str, out_path: Path | str) -> Path:
    _, bundle = read_recording_h5(h5_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2) + "\n")
    return out


def export_h5_to_xlsx(h5_path: Path | str, out_path: Path | str) -> Path:
    """Export to .xlsx. The xlsx writer reads a CSV, so a temporary CSV is
    materialized from the .h5 samples next to the target and removed after."""
    from ads1292_studio.xlsx_io import write_recording_xlsx, recording_xlsx_path

    recording, bundle = read_recording_h5(h5_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_csv = out.with_suffix(".h5export.tmp.csv")
    try:
        write_recording_csv(tmp_csv, recording.samples)
        events = events_from_bundle(bundle)
        produced = write_recording_xlsx(
            tmp_csv, events=events, sample_rate_hz=recording.sample_rate_hz
        )
        target = out if out.suffix.lower() == ".xlsx" else recording_xlsx_path(out)
        if produced != target:
            produced.replace(target)
        return target
    finally:
        tmp_csv.unlink(missing_ok=True)
