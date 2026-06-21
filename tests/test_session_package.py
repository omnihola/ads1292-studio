import hashlib
import json
from pathlib import Path

from ads1292_studio.acquisition import build_acquisition_provenance, write_acquisition_json
from ads1292_studio.calibration import Calibration, write_calibration_json
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker, write_events_json
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol, write_protocol_json
from ads1292_studio.quality_gate import QualityGate, write_quality_gate_json
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
    write_acquisition_json(
        path.with_suffix(".acquisition.json"),
        build_acquisition_provenance(
            csv_path=path,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem214301",
            sample_rate_hz=500.0,
            calibration=Calibration(label="bench-cal"),
            live_calibration=None,
            started_at="2026-06-21T12:00:00",
        ),
    )


def test_export_session_package_copies_sidecars_and_writes_manifest(tmp_path: Path) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    out_dir = tmp_path / "packages"
    _write_session_files(csv_path)

    export = export_session_package(csv_path=csv_path, out_dir=out_dir, title="Package Test")

    assert export.package_dir.exists()
    assert export.manifest_path.exists()
    assert export.report_html_path.exists()
    manifest = json.loads(export.manifest_path.read_text())
    roles = {file_info["role"] for file_info in manifest["files"]}
    assert {
        "raw_csv",
        "metadata",
        "events",
        "calibration",
        "acquisition",
        "protocol",
        "quality_gate",
        "report_html",
        "report_ecg_png",
        "report_pqrst_png",
    } <= roles
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


def test_verify_session_package_fails_after_file_tamper(tmp_path: Path) -> None:
    csv_path = tmp_path / "pkg-001.csv"
    _write_session_files(csv_path)
    export = export_session_package(csv_path=csv_path, out_dir=tmp_path / "packages", title="Package Test")
    raw_csv = export.package_dir / "pkg-001.csv"
    raw_csv.write_text(raw_csv.read_text() + "\n# tampered\n")

    result = verify_session_package(export.manifest_path)

    assert result.ok is False
    assert any("sha256 mismatch" in failure for failure in result.failures)
