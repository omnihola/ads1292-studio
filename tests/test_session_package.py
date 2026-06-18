import hashlib
import json
from pathlib import Path

from ads1292_studio.calibration import Calibration, write_calibration_json
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker, write_events_json
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import StreamSample
from ads1292_studio.session_package import export_session_package


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
    assert {"raw_csv", "metadata", "events", "calibration", "report_html", "report_ecg_png", "report_pqrst_png"} <= roles
    assert manifest["metrics"]["ecg_source"] == "CH2"
    raw_entry = next(file_info for file_info in manifest["files"] if file_info["role"] == "raw_csv")
    copied_csv = export.package_dir / raw_entry["path"]
    expected_sha = hashlib.sha256(copied_csv.read_bytes()).hexdigest()
    assert raw_entry["sha256"] == expected_sha
    assert raw_entry["bytes"] == copied_csv.stat().st_size
