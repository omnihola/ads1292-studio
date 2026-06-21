import hashlib
import json
from pathlib import Path

from ads1292_studio.acquisition import (
    build_acquisition_provenance,
    finalize_acquisition_provenance,
    write_acquisition_json,
)
from ads1292_studio.calibration import Calibration, LiveStreamCalibration, write_calibration_json
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker, write_events_csv, write_events_json
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol, write_protocol_json
from ads1292_studio.quality_gate import QualityGate, write_quality_gate_json
from ads1292_studio.recording_manifest import write_recording_manifest
from ads1292_studio.session_package import export_session_package, verify_session_package


def _write_session_files(path: Path) -> None:
    samples = tuple(
        StreamSample(
            timestamp=index / 500.0,
            ch1=0,
            ch2=900 if index % 50 == 0 else 0,
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index in range(600)
    )
    write_recording_csv(path, samples)
    write_metadata_json(
        path.with_suffix(".json"),
        SessionMetadata(session_id="pkg-001", subject_id="anonymous", electrode="MOTAC gel"),
    )
    write_events_json(path.with_suffix(".events.json"), (EventMarker(0.5, "motion", "arm moved"),))
    write_events_csv(path.with_suffix(".events.csv"), (EventMarker(0.5, "motion", "arm moved"),))
    write_calibration_json(path.with_suffix(".calibration.json"), Calibration(label="bench-cal"))
    write_protocol_json(
        path.with_suffix(".protocol.json"),
        TestProtocol(
            name="package protocol",
            objective="Package the test plan with the recording.",
            steps=(ProtocolStep(0.0, 1.0, "baseline", "Sit still."),),
        ),
    )
    write_quality_gate_json(
        path.with_suffix(".quality-gate.json"),
        QualityGate(min_duration_seconds=0.5, min_r_peaks=1, require_qrs_clear=False),
    )
    acquisition = build_acquisition_provenance(
        csv_path=path,
        acquisition_mode="live_stream",
        port="/dev/cu.usbmodem214301",
        sample_rate_hz=500.0,
        calibration=Calibration(label="bench-cal"),
        live_calibration=LiveStreamCalibration(
            mean_uv_per_count=1.895,
            std_uv_per_count=0.002,
            cv_percent=0.11,
            runs=5,
            test_signal_pp_uv=2016.6666667,
        ),
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
    write_recording_manifest(path, created_at="2026-06-21T12:00:04")


def test_export_session_package_copies_sidecars_and_writes_manifest(tmp_path: Path) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    out_dir = tmp_path / "packages"
    _write_session_files(csv_path)

    export = export_session_package(csv_path=csv_path, out_dir=out_dir, title="Package Test")

    assert export.package_dir.exists()
    assert export.manifest_path.exists()
    assert export.report_html_path.exists()
    manifest = json.loads(export.manifest_path.read_text())
    sidecar_completeness = manifest["sidecar_completeness"]
    assert sidecar_completeness["complete"] is True
    assert sidecar_completeness["missing_roles"] == []
    assert sidecar_completeness["required_roles"] == [
        "metadata",
        "event_annotations",
        "calibration",
        "acquisition",
        "protocol",
        "quality_gate",
    ]
    roles = {file_info["role"] for file_info in manifest["files"]}
    assert {
        "raw_csv",
        "metadata",
        "events",
        "events_csv",
        "calibration",
        "acquisition",
        "protocol",
        "quality_gate",
        "recording_manifest",
        "report_html",
        "report_ecg_png",
        "report_pqrst_png",
    } <= roles
    recording_manifest = next(file_info for file_info in manifest["files"] if file_info["role"] == "recording_manifest")
    copied_recording_manifest = export.package_dir / recording_manifest["path"]
    assert copied_recording_manifest.exists()
    assert recording_manifest["sha256"] == hashlib.sha256(copied_recording_manifest.read_bytes()).hexdigest()
    assert manifest["metrics"]["ecg_source"] == "CH2"
    assert "baseline_drift_counts" in manifest["metrics"]
    assert "noise_rms_counts" in manifest["metrics"]
    assert "peak_to_peak_counts" in manifest["metrics"]
    assert manifest["metrics"]["segment_metrics"][0]["label"] == "baseline"
    assert manifest["metrics"]["segment_metrics"][0]["sample_count"] > 0
    assert manifest["metrics"]["segment_gate"]["label"] in {"Pass", "Fail"}
    assert manifest["metrics"]["segment_gate"]["segment_results"][0]["label"] == "baseline"
    assert manifest["metrics"]["quality_gate"]["min_duration_seconds"] == 0.5
    assert manifest["metrics"]["quality_gate"]["require_qrs_clear"] is False
    annotations = manifest["metrics"]["event_annotations"]
    assert annotations["schema"] == "ads1292-event-annotations-v1"
    assert annotations["timestamp_reference"] == "relative_seconds_from_recording_start"
    assert annotations["count"] == 1
    assert annotations["point_events"] == 1
    assert annotations["interval_events"] == 0
    assert annotations["total_annotated_seconds"] == 0.0
    assert annotations["labels"] == {"motion": 1}
    assert annotations["source_role"] == "events"
    assert annotations["source_path"] == "pkg-001.events.json"
    acquisition = manifest["metrics"]["acquisition"]
    assert acquisition["mode"] == "live_stream"
    assert acquisition["sample_rate_hz"] == 500.0
    assert acquisition["port"] == "/dev/cu.usbmodem214301"
    assert acquisition["csv_schema"] == "ads1292-studio-live-stream-v1"
    assert acquisition["timestamp_reference"] == "relative_seconds_from_recording_start"
    column_map = {entry["name"]: entry for entry in acquisition["csv_columns"]}
    assert column_map["timestamp"]["unit"] == "s"
    assert column_map["ch2_counts"]["description"] == "CH2 ECG Lead I (LA-RA)"
    assert column_map["live_scale_uv_per_count"]["unit"] == "uV/count"
    assert acquisition["raw_lsb_uv_per_count"] == Calibration(label="bench-cal").microvolts_per_count
    assert acquisition["live_scale_uv_per_count"] == 1.895
    assert acquisition["live_scale_runs"] == 5
    assert acquisition["completion_status"] == "finalized"
    assert acquisition["sample_count"] == 600
    assert acquisition["sample_span_seconds"] == 1.198
    assert acquisition["ended_at"] == "2026-06-21T12:00:02"
    assert acquisition["actual_sample_count"] == 600
    assert acquisition["actual_span_seconds"] == 1.198
    assert acquisition["completion_audit"] == "pass"
    assert acquisition["sample_count_delta"] == 0
    assert acquisition["sample_span_delta_seconds"] == 0.0
    raw_entry = next(file_info for file_info in manifest["files"] if file_info["role"] == "raw_csv")
    copied_csv = export.package_dir / raw_entry["path"]
    expected_sha = hashlib.sha256(copied_csv.read_bytes()).hexdigest()
    assert raw_entry["sha256"] == expected_sha
    assert raw_entry["bytes"] == copied_csv.stat().st_size


def test_verify_session_package_passes_clean_manifest(tmp_path: Path) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    _write_session_files(csv_path)
    export = export_session_package(csv_path=csv_path, out_dir=tmp_path / "packages", title="Package Test")

    result = verify_session_package(export.manifest_path)

    assert result.ok is True
    assert result.checked_files >= 4
    assert result.failures == tuple()


def test_export_session_package_uses_events_csv_when_json_missing(tmp_path: Path) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    _write_session_files(csv_path)
    csv_path.with_suffix(".events.json").unlink()
    write_events_csv(
        csv_path.with_suffix(".events.csv"),
        (EventMarker(0.5, duration_seconds=0.25, label="csv-only motion", notes="spreadsheet edited"),),
    )

    export = export_session_package(csv_path=csv_path, out_dir=tmp_path / "packages", title="Package Test")

    manifest = json.loads(export.manifest_path.read_text())
    roles = {file_info["role"] for file_info in manifest["files"]}
    html = export.report_html_path.read_text()
    assert "events_csv" in roles
    assert "events" not in roles
    assert manifest["metrics"]["event_annotations"]["source_role"] == "events_csv"
    assert manifest["metrics"]["event_annotations"]["source_path"] == "pkg-001.events.csv"
    assert manifest["sidecar_completeness"]["complete"] is True
    assert "event_annotations" in manifest["sidecar_completeness"]["present_roles"]
    assert manifest["sidecar_completeness"]["missing_roles"] == []
    assert verify_session_package(export.manifest_path).ok is True
    assert "csv-only motion" in html
    assert "spreadsheet edited" in html


def test_export_session_package_summarizes_event_annotation_intervals(tmp_path: Path) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    _write_session_files(csv_path)
    events = (
        EventMarker(0.5, duration_seconds=0.25, label="motion", notes="small movement"),
        EventMarker(1.0, duration_seconds=0.5, label="motion", notes="large movement"),
        EventMarker(2.0, label="electrode touch", notes="adjust LA"),
    )
    write_events_json(csv_path.with_suffix(".events.json"), events)
    write_events_csv(csv_path.with_suffix(".events.csv"), events)

    export = export_session_package(csv_path=csv_path, out_dir=tmp_path / "packages", title="Package Test")

    annotations = json.loads(export.manifest_path.read_text())["metrics"]["event_annotations"]
    assert annotations["count"] == 3
    assert annotations["interval_events"] == 2
    assert annotations["point_events"] == 1
    assert annotations["total_annotated_seconds"] == 0.75
    assert annotations["labels"] == {"electrode touch": 1, "motion": 2}
    assert annotations["events"] == [
        {
            "start_seconds": 0.5,
            "end_seconds": 0.75,
            "duration_seconds": 0.25,
            "label": "motion",
            "notes": "small movement",
        },
        {
            "start_seconds": 1.0,
            "end_seconds": 1.5,
            "duration_seconds": 0.5,
            "label": "motion",
            "notes": "large movement",
        },
        {
            "start_seconds": 2.0,
            "end_seconds": 2.0,
            "duration_seconds": 0.0,
            "label": "electrode touch",
            "notes": "adjust LA",
        },
    ]


def test_verify_session_package_fails_after_file_tamper(tmp_path: Path) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    _write_session_files(csv_path)
    export = export_session_package(csv_path=csv_path, out_dir=tmp_path / "packages", title="Package Test")
    raw_csv = export.package_dir / "pkg-001.csv"
    raw_csv.write_text(raw_csv.read_text() + "\n# tampered\n")

    result = verify_session_package(export.manifest_path)

    assert result.ok is False
    assert any("sha256 mismatch" in failure for failure in result.failures)


def test_verify_session_package_fails_when_required_sidecar_was_missing(tmp_path: Path) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    _write_session_files(csv_path)
    csv_path.with_suffix(".acquisition.json").unlink()
    export = export_session_package(csv_path=csv_path, out_dir=tmp_path / "packages", title="Package Test")

    manifest = json.loads(export.manifest_path.read_text())
    sidecar_completeness = manifest["sidecar_completeness"]
    assert sidecar_completeness["complete"] is False
    assert sidecar_completeness["missing_roles"] == ["acquisition"]
    assert "acquisition" not in sidecar_completeness["present_roles"]

    result = verify_session_package(export.manifest_path)

    assert result.ok is False
    assert "required sidecars missing: acquisition" in result.failures


def test_verify_session_package_fails_when_acquisition_completion_mismatches_csv(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    _write_session_files(csv_path)
    acquisition = build_acquisition_provenance(
        csv_path=csv_path,
        acquisition_mode="live_stream",
        port="/dev/cu.usbmodem214301",
        sample_rate_hz=500.0,
        calibration=Calibration(label="bench-cal"),
        live_calibration=None,
        started_at="2026-06-21T12:00:00",
    )
    write_acquisition_json(
        csv_path.with_suffix(".acquisition.json"),
        finalize_acquisition_provenance(
            acquisition,
            ended_at="2026-06-21T12:00:02",
            finalized_at="2026-06-21T12:00:03",
            sample_count=598,
            first_timestamp_seconds=0.0,
            last_timestamp_seconds=1.0,
        ),
    )

    export = export_session_package(csv_path=csv_path, out_dir=tmp_path / "packages", title="Package Test")

    acquisition_metrics = json.loads(export.manifest_path.read_text())["metrics"]["acquisition"]
    assert acquisition_metrics["completion_audit"] == "fail"
    assert acquisition_metrics["sample_count_delta"] == -2
    assert acquisition_metrics["sample_span_delta_seconds"] == -0.198
    result = verify_session_package(export.manifest_path)
    assert result.ok is False
    assert "acquisition completion audit failed: fail" in result.failures


def test_verify_session_package_fails_when_acquisition_completion_is_open(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    _write_session_files(csv_path)
    write_acquisition_json(
        csv_path.with_suffix(".acquisition.json"),
        build_acquisition_provenance(
            csv_path=csv_path,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem214301",
            sample_rate_hz=500.0,
            calibration=Calibration(label="bench-cal"),
            live_calibration=None,
            started_at="2026-06-21T12:00:00",
        ),
    )

    export = export_session_package(csv_path=csv_path, out_dir=tmp_path / "packages", title="Package Test")

    acquisition_metrics = json.loads(export.manifest_path.read_text())["metrics"]["acquisition"]
    assert acquisition_metrics["completion_audit"] == "pending"
    result = verify_session_package(export.manifest_path)
    assert result.ok is False
    assert "acquisition completion audit failed: pending" in result.failures
