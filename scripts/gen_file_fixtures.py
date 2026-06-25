# scripts/gen_file_fixtures.py
from __future__ import annotations

import csv
from pathlib import Path

import h5py
import numpy as np

from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.h5_io import write_recording_h5, verify_recording_h5
from ads1292_studio.events import EventMarker
from ads1292_studio.xlsx_io import write_recording_xlsx
from ads1292_studio.models import StreamSample
# write_recording_h5 needs the full recording bundle — all six dataclasses have
# zero-arg defaults (canonical construction copied from tests/test_h5_io.py).
from ads1292_studio.calibration import Calibration
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.recording_bundle import AcquisitionProvenance, RecordingProcessingSettings, build_recording_bundle
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, sha256_array
from scripts._xlsx_read import read_xlsx_semantic
import csv as _csv
from ads1292_studio.csv_io import write_raw_recording_csv
from ads1292_studio.models import RawSample

SR = 500.0


def _samples(ch2: list[float], n: int) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(timestamp=round(i / SR, 6), ch1=10 + i, ch2=int(round(ch2[i])),
                     board_heart_rate=72, board_respiration_rate=18, status_byte=(i % 16))
        for i in range(n)
    )


def generate(root: Path) -> list[Path]:
    out = Path(root) / "files"
    out.mkdir(parents=True, exist_ok=True)
    signal = synthetic_ecg(50, SR, bpm=72.0)
    samples = _samples(signal, 50)
    written: list[Path] = []

    # --- live CSV: freeze header + first rows (text level) ---
    csv_path = out / "live_recording.csv"
    write_recording_csv(csv_path, samples)
    with csv_path.open() as fh:
        rows = list(csv.reader(fh))
    sidecar = out / "live_recording_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_csv_live", "name": "live_recording",
        "oracle": {"function": "ads1292_studio.csv_io.write_recording_csv"},
        "csv_header": rows[0],
        "csv_first_rows": rows[1:6],
        "row_count": len(rows) - 1,
        "tolerance": {"kind": "text"},
        "notes": "live CSV column order + names + value formatting frozen at text level",
    }, sidecar)
    written += [csv_path, sidecar]

    # --- HDF5: freeze sidecar (datasets/attrs/per-array sha256), NOT bytes ---
    # write_recording_h5's first positional arg is the CSV path; it derives the
    # .h5 path via recording_h5_path(csv_path) and returns it. samples + the six
    # bundle objects are required keyword args. created_at="" keeps it
    # deterministic (no wall-clock stamp). Canonical construction per tests/test_h5_io.py.
    produced_h5 = write_recording_h5(
        csv_path,
        samples=samples,
        sample_rate_hz=SR,
        metadata=SessionMetadata(operator="fixture", subject_id="p1"),
        events=(),
        calibration=Calibration(),
        acquisition=AcquisitionProvenance(),
        protocol=TestProtocol(),
        quality_gate=QualityGate(),
        processing=RecordingProcessingSettings(),
        created_at="",
    )
    h5_path = out / "recording.h5"
    if produced_h5 != h5_path:
        produced_h5 = produced_h5.rename(h5_path)
    datasets: dict[str, dict] = {}
    attrs: dict[str, str] = {}
    with h5py.File(h5_path, "r") as fh:
        def _visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                datasets[name] = {
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                    "sha256": sha256_array(np.asarray(obj[()], dtype=float))
                        if np.issubdtype(obj.dtype, np.number) else "non-numeric",
                }
        fh.visititems(_visit)
        for key, value in fh.attrs.items():
            attrs[key] = str(value)
    verification = verify_recording_h5(h5_path)
    h5_sidecar = out / "recording_h5_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_hdf5", "name": "recording_h5",
        "oracle": {"function": "ads1292_studio.h5_io.write_recording_h5"},
        "artifact": "recording.h5",
        "datasets": datasets,
        "attrs": attrs,
        "verify_ok": bool(getattr(verification, "ok", verification)),
        "tolerance": {"kind": "structure"},
        "notes": "HDF5 schema + datasets + attrs + per-array sha256; byte-identity NOT required",
    }, h5_sidecar)
    written += [h5_path, h5_sidecar]

    # --- minimal XLSX semantic fixture: sheets + headers + event rows + data rows ---
    point_event = EventMarker(timestamp_seconds=0.020, label="touch", notes="point note", duration_seconds=0.0)
    interval_event = EventMarker(timestamp_seconds=0.040, label="motion", notes="range note", duration_seconds=0.030)
    xlsx_path = write_recording_xlsx(csv_path, events=(point_event, interval_event), sample_rate_hz=SR)
    if xlsx_path != out / "recording.xlsx":
        xlsx_path = xlsx_path.rename(out / "recording.xlsx")
    semantic = read_xlsx_semantic(xlsx_path)
    events_name, data_name = semantic["sheet_names"][0], semantic["sheet_names"][1]
    events_rows = semantic["sheets"][events_name]
    data_rows = semantic["sheets"][data_name]
    point_rows = [r for r in events_rows[1:] if r and r[-3] == "point"]
    interval_rows = [r for r in events_rows[1:] if r and r[-3] == "interval"]
    assert point_rows and interval_rows, "expected one point and one interval event row"
    xlsx_sidecar = out / "recording_xlsx_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_xlsx", "name": "recording_xlsx",
        "oracle": {"function": "ads1292_studio.xlsx_io.write_recording_xlsx"},
        "artifact": "recording.xlsx",
        "sheet_names": semantic["sheet_names"],
        "events_header": events_rows[0],
        "point_event_row": point_rows[0],
        "interval_event_row": interval_rows[0],
        "data_header": data_rows[0],
        "data_first_row": data_rows[1],
        "data_last_row": data_rows[-1],
        "tolerance": {"kind": "semantic"},
        "notes": "XLSX semantic ONLY: sheet names + headers + 1 point + 1 interval event + first/last data row. No style/zip/byte equality.",
    }, xlsx_sidecar)
    written += [xlsx_path, xlsx_sidecar]

    # --- raw CSV: freeze header + first/last rows (text level), default calibration ---
    raw_samples = tuple(
        RawSample(
            timestamp=round(i / SR, 6),
            sample_index=i,
            ch1_raw24=int(round(signal[i])) * 10,
            ch2_raw24=-int(round(signal[i])) * 5,
            status_byte=(i % 16),
        )
        for i in range(50)
    )
    raw_csv_path = out / "raw_recording.csv"
    write_raw_recording_csv(raw_csv_path, raw_samples, calibration=Calibration())
    with raw_csv_path.open() as fh:
        raw_rows = list(_csv.reader(fh))
    raw_sidecar = out / "raw_recording_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_csv_raw", "name": "raw_recording",
        "oracle": {"function": "ads1292_studio.csv_io.write_raw_recording_csv"},
        "csv_header": raw_rows[0],
        "csv_first_rows": raw_rows[1:6],
        "csv_last_row": raw_rows[-1],
        "row_count": len(raw_rows) - 1,
        "tolerance": {"kind": "text"},
        "notes": "raw CSV header + value formatting (CRLF, %.17g uv, %g vref/pga, %.9f lsb) frozen at text level; default Calibration",
    }, raw_sidecar)
    written += [raw_csv_path, raw_sidecar]

    # --- recording bundle: freeze the full default bundle JSON (the C++ parity target) ---
    bundle = build_recording_bundle(
        csv_path="rec.csv",
        metadata=SessionMetadata(operator="fixture", subject_id="p1"),
        events=(EventMarker(0.02, "touch", "n1", 0.0), EventMarker(0.04, "motion", "n2", 0.03)),
        calibration=Calibration(),
        acquisition=AcquisitionProvenance(),
        protocol=TestProtocol(),
        quality_gate=QualityGate(),
        processing=RecordingProcessingSettings(),
        sample_rate_hz=500.0,
        created_at="",
    )
    bundle_path = out / "recording_bundle.json"
    dump_fixture(bundle, bundle_path)
    bundle_sidecar = out / "recording_bundle_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_bundle", "name": "recording_bundle",
        "oracle": {"function": "ads1292_studio.recording_bundle.build_recording_bundle"},
        "artifact": "recording_bundle.json",
        "top_keys": sorted(bundle.keys()),
        "tolerance": {"kind": "structure"},
        "notes": "full default recording bundle; C++ build_recording_bundle must reproduce key-for-key",
    }, bundle_sidecar)
    written += [bundle_path, bundle_sidecar]

    return written
