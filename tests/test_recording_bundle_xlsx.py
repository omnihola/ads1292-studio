import zipfile
from pathlib import Path

from ads1292_studio.acquisition import build_acquisition_provenance
from ads1292_studio.calibration import Calibration
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.models import StreamSample
from ads1292_studio.processing import build_processing_settings
from ads1292_studio.protocol import ProtocolStep, TestProtocol
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.recording_bundle import (
    RECORDING_BUNDLE_SCHEMA,
    acquisition_from_bundle,
    events_from_bundle,
    is_recording_bundle_path,
    metadata_from_bundle,
    read_recording_bundle,
    write_recording_bundle,
)
from ads1292_studio.xlsx_io import write_recording_xlsx


def _samples() -> tuple[StreamSample, ...]:
    return (
        StreamSample(0.0, 10, 900, 70, 18, 0, sample_index=0),
        StreamSample(0.002, 11, 901, 70, 18, 0, sample_index=1),
    )


def _acquisition(csv_path: Path):
    return build_acquisition_provenance(
        csv_path=csv_path,
        acquisition_mode="live_stream",
        port="/dev/cu.usbmodem214301",
        sample_rate_hz=500.0,
        calibration=Calibration(label="bundle-cal"),
        live_calibration=None,
        started_at="2026-06-21T12:00:00",
    )


def test_recording_bundle_round_trip_consolidates_session_metadata(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    write_recording_csv(csv_path, _samples())

    bundle_path = write_recording_bundle(
        csv_path,
        metadata=SessionMetadata(session_id="run-001", electrode="MOTAC gel"),
        events=(EventMarker(0.5, label="motion", notes="arm"),),
        calibration=Calibration(label="bundle-cal"),
        acquisition=_acquisition(csv_path),
        protocol=TestProtocol(
            name="bundle protocol",
            steps=(ProtocolStep(0.0, 1.0, "baseline", "Sit still."),),
        ),
        quality_gate=QualityGate(min_duration_seconds=0.5),
        processing=build_processing_settings(),
        sample_rate_hz=500.0,
        created_at="2026-06-21T12:00:00",
    )

    assert bundle_path == csv_path.with_suffix(".json")
    assert is_recording_bundle_path(bundle_path)
    data = read_recording_bundle(csv_path)
    assert data["schema"] == RECORDING_BUNDLE_SCHEMA
    assert data["csv_name"] == "recording.csv"
    assert data["metadata"]["session_id"] == "run-001"
    assert data["events"]["events"][0]["label"] == "motion"
    assert data["calibration"]["label"] == "bundle-cal"
    assert data["protocol"]["steps"][0]["label"] == "baseline"
    assert metadata_from_bundle(data).electrode == "MOTAC gel"
    assert events_from_bundle(data)[0].notes == "arm"
    assert acquisition_from_bundle(data).port == "/dev/cu.usbmodem214301"


def test_recording_xlsx_contains_events_and_data_sheets(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    write_recording_csv(csv_path, _samples())

    xlsx_path = write_recording_xlsx(
        csv_path,
        events=(EventMarker(0.25, duration_seconds=0.5, label="motion", notes="arm"),),
    )

    assert xlsx_path == csv_path.with_suffix(".xlsx")
    assert xlsx_path.exists()
    with zipfile.ZipFile(xlsx_path) as workbook:
        names = set(workbook.namelist())
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
        workbook_xml = workbook.read("xl/workbook.xml").decode()
        events_xml = workbook.read("xl/worksheets/sheet1.xml").decode()
        data_xml = workbook.read("xl/worksheets/sheet2.xml").decode()
    assert 'name="Events"' in workbook_xml
    assert 'name="Data"' in workbook_xml
    assert "event_id" in events_xml
    assert "motion" in events_xml
    assert "ch1_counts" in data_xml
    assert "900" in data_xml
