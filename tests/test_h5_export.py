"""On-demand export from the canonical HDF5 to CSV / JSON / XLSX."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("h5py")

from ads1292_studio.calibration import Calibration
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.events import EventMarker
from ads1292_studio.h5_export import export_h5_to_csv, export_h5_to_json, export_h5_to_xlsx
from ads1292_studio.h5_io import write_recording_h5
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.recording_bundle import AcquisitionProvenance, RecordingProcessingSettings


def _make_h5(tmp_path: Path) -> Path:
    csv_path = tmp_path / "rec-ads1292-studio.csv"
    csv_path.write_text("journal\n")
    samples = tuple(
        StreamSample(timestamp=i / 500.0, ch1=i, ch2=-i,
                     board_heart_rate=60, board_respiration_rate=15, status_byte=0)
        for i in range(12)
    )
    return write_recording_h5(
        csv_path,
        samples=samples,
        sample_rate_hz=500.0,
        metadata=SessionMetadata(operator="bob"),
        events=(EventMarker(timestamp_seconds=0.01, label="evt"),),
        calibration=Calibration(),
        acquisition=AcquisitionProvenance(),
        protocol=TestProtocol(),
        quality_gate=QualityGate(),
        processing=RecordingProcessingSettings(),
        created_at="2026-06-21T20:00:00",
    )


def test_export_csv_round_trips_samples(tmp_path: Path) -> None:
    h5 = _make_h5(tmp_path)
    out = export_h5_to_csv(h5, tmp_path / "export.csv")
    rec = read_recording_csv(out)
    assert len(rec.samples) == 12
    assert rec.samples[3].ch1 == 3 and rec.samples[3].ch2 == -3


def test_export_json_contains_metadata(tmp_path: Path) -> None:
    h5 = _make_h5(tmp_path)
    out = export_h5_to_json(h5, tmp_path / "export.json")
    data = json.loads(out.read_text())
    assert data["metadata"]["operator"] == "bob"
    assert data["created_at"] == "2026-06-21T20:00:00"


def test_export_xlsx_is_a_valid_zip(tmp_path: Path) -> None:
    h5 = _make_h5(tmp_path)
    out = export_h5_to_xlsx(h5, tmp_path / "export.xlsx")
    assert out.exists()
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert any("sheet" in n for n in names)
    # the temp CSV must be cleaned up
    assert not (tmp_path / "export.h5export.tmp.csv").exists()
