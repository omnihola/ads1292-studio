from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

from ads1292_studio.calibration import calibration_template, read_calibration_json
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.events import read_events_json
from ads1292_studio.metadata import read_metadata_json
from ads1292_studio.report import export_review_report


@dataclass(frozen=True)
class SessionPackageExport:
    package_dir: Path
    manifest_path: Path
    report_html_path: Path


def export_session_package(
    csv_path: Path | str,
    out_dir: Path | str,
    title: str = "ADS1292 Session Package",
    source: str = "Auto",
) -> SessionPackageExport:
    source_csv = Path(csv_path)
    output = Path(out_dir)
    package_dir = output / _package_slug(source_csv)
    package_dir.mkdir(parents=True, exist_ok=True)

    copied_csv = package_dir / source_csv.name
    shutil.copy2(source_csv, copied_csv)
    files = [_file_entry("raw_csv", copied_csv, package_dir)]

    metadata = None
    events = tuple()
    calibration = calibration_template()
    sidecars = (
        ("metadata", source_csv.with_suffix(".json")),
        ("events", source_csv.with_suffix(".events.json")),
        ("calibration", source_csv.with_suffix(".calibration.json")),
    )
    for role, sidecar in sidecars:
        if not sidecar.exists():
            continue
        copied = package_dir / sidecar.name
        shutil.copy2(sidecar, copied)
        files.append(_file_entry(role, copied, package_dir))
        if role == "metadata":
            metadata = read_metadata_json(copied)
        elif role == "events":
            events = read_events_json(copied)
        elif role == "calibration":
            calibration = read_calibration_json(copied)

    recording = read_recording_csv(copied_csv)
    report_dir = package_dir / "report"
    report = export_review_report(
        samples=recording.samples,
        out_dir=report_dir,
        title=title,
        sample_rate_hz=recording.sample_rate_hz,
        source=source,
        metadata=metadata,
        events=events,
        calibration=calibration,
    )
    files.extend(
        [
            _file_entry("report_html", report.html_path, package_dir),
            _file_entry("report_ecg_png", report.ecg_png_path, package_dir),
            _file_entry("report_pqrst_png", report.pqrst_png_path, package_dir),
        ]
    )

    manifest_path = package_dir / "manifest.json"
    manifest = {
        "schema": "ads1292-session-package-v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_csv": str(source_csv),
        "title": title,
        "metrics": {
            "quality": report.metrics.quality_label,
            "ecg_source": report.metrics.ecg_source,
            "samples": report.metrics.sample_count,
            "duration_seconds": report.metrics.duration_seconds,
            "median_hr_bpm": report.metrics.hr_median_bpm,
        },
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return SessionPackageExport(package_dir=package_dir, manifest_path=manifest_path, report_html_path=report.html_path)


def _package_slug(csv_path: Path) -> str:
    stem = "".join(char.lower() if char.isalnum() else "-" for char in csv_path.stem)
    return "-".join(part for part in stem.split("-") if part)[:64] or "ads1292-session"


def _file_entry(role: str, path: Path, package_dir: Path) -> dict[str, str | int]:
    data = path.read_bytes()
    return {
        "role": role,
        "path": str(path.relative_to(package_dir)),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
