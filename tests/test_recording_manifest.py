import hashlib
import json
from pathlib import Path

from ads1292_studio.acquisition import (
    build_acquisition_provenance,
    finalize_acquisition_provenance,
    write_acquisition_json,
)
from ads1292_studio.calibration import Calibration, write_calibration_json
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker, write_events_csv, write_events_json
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.processing import build_processing_settings, write_processing_json
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol, write_protocol_json
from ads1292_studio.quality_gate import QualityGate, write_quality_gate_json
from ads1292_studio.recording_manifest import (
    RECORDING_MANIFEST_SCHEMA,
    build_recording_manifest,
    verify_recording_manifest,
    write_recording_manifest,
)


def _write_recording(path: Path, *, samples: int = 600) -> None:
    write_recording_csv(
        path,
        tuple(
            StreamSample(
                timestamp=index / 500.0,
                ch1=10,
                ch2=900 if index % 50 == 0 else 0,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            )
            for index in range(samples)
        ),
    )


def _write_complete_sidecars(path: Path) -> None:
    calibration = Calibration(label="manifest-cal")
    write_metadata_json(path.with_suffix(".json"), SessionMetadata(session_id="rec-001", electrode="MOTAC gel"))
    events = (
        EventMarker(timestamp_seconds=0.5, label="baseline", notes="quiet"),
        EventMarker(timestamp_seconds=0.75, duration_seconds=0.25, label="motion", notes="arm motion"),
    )
    write_events_json(path.with_suffix(".events.json"), events)
    write_events_csv(path.with_suffix(".events.csv"), events)
    write_calibration_json(path.with_suffix(".calibration.json"), calibration)
    write_protocol_json(
        path.with_suffix(".protocol.json"),
        TestProtocol(
            name="manifest protocol",
            steps=(ProtocolStep(start_seconds=0.0, duration_seconds=1.0, label="baseline", instruction="Sit still."),),
        ),
    )
    write_quality_gate_json(path.with_suffix(".quality-gate.json"), QualityGate(min_duration_seconds=0.5))
    write_processing_json(path.with_suffix(".processing.json"), build_processing_settings())
    acquisition = build_acquisition_provenance(
        csv_path=path,
        acquisition_mode="live_stream",
        port="/dev/cu.usbmodem214301",
        sample_rate_hz=500.0,
        calibration=calibration,
        live_calibration=None,
        started_at="2026-06-21T12:00:00",
    )
    write_acquisition_json(
        path.with_suffix(".acquisition.json"),
        finalize_acquisition_provenance(
            acquisition,
            ended_at="2026-06-21T12:00:02",
            finalized_at="2026-06-21T12:00:03",
            sample_count=600,
            first_timestamp_seconds=0.0,
            last_timestamp_seconds=1.198,
        ),
    )


def test_write_recording_manifest_lists_files_and_scientific_context(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_recording(csv_path)
    _write_complete_sidecars(csv_path)

    manifest_path = write_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")

    assert manifest_path == csv_path.with_suffix(".manifest.json")
    payload = json.loads(manifest_path.read_text())
    assert payload["schema"] == RECORDING_MANIFEST_SCHEMA
    assert payload["created_at"] == "2026-06-21T13:00:00"
    assert payload["source_csv"] == "recording.csv"
    assert payload["recording"]["sample_count"] == 600
    assert payload["recording"]["duration_seconds"] == 1.198
    assert payload["recording"]["first_sample_index"] == 0
    assert payload["recording"]["last_sample_index"] == 599
    assert payload["recording"]["sample_index_contiguous"] is True
    assert payload["recording"]["sample_index_gap_count"] == 0
    assert payload["sidecar_completeness"]["complete"] is True
    assert payload["sidecar_completeness"]["missing_roles"] == []
    roles = {item["role"] for item in payload["files"]}
    assert {
        "raw_csv",
        "metadata",
        "events",
        "events_csv",
        "calibration",
        "acquisition",
        "protocol",
        "quality_gate",
        "processing",
    } <= roles
    raw_csv = next(item for item in payload["files"] if item["role"] == "raw_csv")
    assert raw_csv["path"] == "recording.csv"
    assert raw_csv["sha256"] == hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert payload["event_annotations"]["count"] == 2
    assert payload["event_annotations"]["sample_rate_hz"] == 500.0
    assert (
        payload["event_annotations"]["sample_index_reference"]
        == "zero_based_sample_index_at_recording_sample_rate"
    )
    assert payload["event_annotations"]["interval_events"] == 1
    assert payload["event_annotations"]["total_annotated_seconds"] == 0.25
    assert payload["event_annotations"]["total_annotated_samples"] == 125
    assert payload["event_annotations"]["labels"] == {"baseline": 1, "motion": 1}
    assert payload["event_annotations"]["events"] == [
        {
            "start_seconds": 0.5,
            "end_seconds": 0.5,
            "duration_seconds": 0.0,
            "start_sample_index": 250,
            "end_sample_index": 250,
            "duration_samples": 0,
            "label": "baseline",
            "notes": "quiet",
        },
        {
            "start_seconds": 0.75,
            "end_seconds": 1.0,
            "duration_seconds": 0.25,
            "start_sample_index": 375,
            "end_sample_index": 500,
            "duration_samples": 125,
            "label": "motion",
            "notes": "arm motion",
        },
    ]
    assert payload["acquisition"]["completion_status"] == "finalized"
    assert payload["acquisition"]["completion_audit"] == "pass"
    assert payload["acquisition"]["sample_count_delta"] == 0
    assert payload["acquisition"]["sample_span_delta_seconds"] == 0.0


def test_build_recording_manifest_reports_sample_index_gaps(tmp_path: Path) -> None:
    csv_path = tmp_path / "gapped.csv"
    write_recording_csv(
        csv_path,
        (
            StreamSample(
                timestamp=0.0,
                ch1=1,
                ch2=2,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
                sample_index=100,
            ),
            StreamSample(
                timestamp=0.002,
                ch1=3,
                ch2=4,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
                sample_index=101,
            ),
            StreamSample(
                timestamp=0.004,
                ch1=5,
                ch2=6,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
                sample_index=103,
            ),
        ),
    )

    payload = build_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")

    assert payload["recording"]["first_sample_index"] == 100
    assert payload["recording"]["last_sample_index"] == 103
    assert payload["recording"]["sample_index_contiguous"] is False
    assert payload["recording"]["sample_index_gap_count"] == 1


def test_build_recording_manifest_marks_open_completion_pending(tmp_path: Path) -> None:
    csv_path = tmp_path / "open.csv"
    _write_recording(csv_path, samples=10)
    write_acquisition_json(
        csv_path.with_suffix(".acquisition.json"),
        build_acquisition_provenance(
            csv_path=csv_path,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem214301",
            sample_rate_hz=500.0,
            calibration=Calibration(label="open-cal"),
            live_calibration=None,
            started_at="2026-06-21T12:00:00",
        ),
    )

    payload = build_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")

    assert payload["sidecar_completeness"]["complete"] is False
    assert "metadata" in payload["sidecar_completeness"]["missing_roles"]
    assert payload["recording"]["sample_count"] == 10
    assert payload["acquisition"]["completion_status"] == "open"
    assert payload["acquisition"]["completion_audit"] == "pending"


def test_verify_recording_manifest_accepts_unchanged_recording(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_recording(csv_path)
    _write_complete_sidecars(csv_path)
    manifest_path = write_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")

    result = verify_recording_manifest(manifest_path)

    assert result.ok is True
    assert result.checked_files == 9
    assert result.failures == tuple()


def test_verify_recording_manifest_detects_changed_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_recording(csv_path)
    _write_complete_sidecars(csv_path)
    manifest_path = write_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")
    csv_path.write_text(csv_path.read_text() + "1.200000,10,900,0,0,0,0\n")

    result = verify_recording_manifest(manifest_path)

    assert result.ok is False
    assert "raw_csv: byte mismatch for recording.csv" in result.failures
    assert "raw_csv: sha256 mismatch for recording.csv" in result.failures
    assert "recording sample count mismatch: manifest 600, actual 601" in result.failures


def test_verify_recording_manifest_detects_sample_index_metric_mismatch(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_recording(csv_path)
    _write_complete_sidecars(csv_path)
    manifest_path = write_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")
    payload = json.loads(manifest_path.read_text())
    payload["recording"]["last_sample_index"] = 598
    payload["recording"]["sample_index_gap_count"] = 1
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n")

    result = verify_recording_manifest(manifest_path)

    assert result.ok is False
    assert "recording last sample index mismatch: manifest 598, actual 599" in result.failures
    assert "recording sample index gap count mismatch: manifest 1, actual 0" in result.failures


def test_verify_recording_manifest_rejects_pending_acquisition_completion(tmp_path: Path) -> None:
    csv_path = tmp_path / "open.csv"
    _write_recording(csv_path, samples=10)
    write_acquisition_json(
        csv_path.with_suffix(".acquisition.json"),
        build_acquisition_provenance(
            csv_path=csv_path,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem214301",
            sample_rate_hz=500.0,
            calibration=Calibration(label="open-cal"),
            live_calibration=None,
            started_at="2026-06-21T12:00:00",
        ),
    )
    manifest_path = write_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")

    result = verify_recording_manifest(manifest_path)

    assert result.ok is False
    assert (
        "required sidecars missing: metadata, event_annotations, calibration, protocol, quality_gate, processing"
        in result.failures
    )
    assert "acquisition completion audit failed: pending" in result.failures
