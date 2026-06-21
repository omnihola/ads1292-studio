from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

from ads1292_studio.acquisition import AcquisitionProvenance, read_acquisition_json
from ads1292_studio.calibration import calibration_template, read_calibration_json
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.events import read_events_csv, read_events_json
from ads1292_studio.metadata import read_metadata_json
from ads1292_studio.protocol import read_protocol_json
from ads1292_studio.quality_gate import quality_gate_template, read_quality_gate_json
from ads1292_studio.report import export_review_report


@dataclass(frozen=True)
class SessionPackageExport:
    package_dir: Path
    manifest_path: Path
    report_html_path: Path


@dataclass(frozen=True)
class PackageVerification:
    manifest_path: Path
    ok: bool
    checked_files: int
    failures: tuple[str, ...]


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
    acquisition = None
    calibration = calibration_template()
    protocol = None
    quality_gate = quality_gate_template()
    sidecars = (
        ("metadata", source_csv.with_suffix(".json")),
        ("events", source_csv.with_suffix(".events.json")),
        ("events_csv", source_csv.with_suffix(".events.csv")),
        ("calibration", source_csv.with_suffix(".calibration.json")),
        ("acquisition", source_csv.with_suffix(".acquisition.json")),
        ("protocol", source_csv.with_suffix(".protocol.json")),
        ("quality_gate", source_csv.with_suffix(".quality-gate.json")),
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
        elif role == "events_csv" and not events:
            events = read_events_csv(copied)
        elif role == "acquisition":
            acquisition = read_acquisition_json(copied)
        elif role == "calibration":
            calibration = read_calibration_json(copied)
        elif role == "protocol":
            protocol = read_protocol_json(copied)
        elif role == "quality_gate":
            quality_gate = read_quality_gate_json(copied)

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
        quality_gate=quality_gate,
        protocol=protocol,
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
            "baseline_drift_counts": report.metrics.baseline_drift_counts,
            "noise_rms_counts": report.metrics.noise_rms_counts,
            "peak_to_peak_counts": report.metrics.peak_to_peak_counts,
            "quality_gate": asdict(quality_gate.normalized()),
            "event_annotations": _event_annotation_summary(events),
            "acquisition": _acquisition_summary(acquisition),
            "segment_metrics": tuple(asdict(segment) for segment in report.segment_metrics),
            "segment_gate": _segment_gate_entry(report.segment_gate_result),
        },
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return SessionPackageExport(package_dir=package_dir, manifest_path=manifest_path, report_html_path=report.html_path)


def verify_session_package(manifest_path: Path | str) -> PackageVerification:
    manifest = Path(manifest_path)
    package_dir = manifest.parent
    failures: list[str] = []
    try:
        data = json.loads(manifest.read_text())
    except Exception as exc:
        return PackageVerification(manifest_path=manifest, ok=False, checked_files=0, failures=(f"manifest read failed: {exc}",))

    checked = 0
    for item in data.get("files", []):
        role = str(item.get("role", "unknown"))
        relative = item.get("path")
        if not isinstance(relative, str):
            failures.append(f"{role}: missing path")
            continue
        path = package_dir / relative
        if not path.exists():
            failures.append(f"{role}: missing file {relative}")
            continue
        checked += 1
        actual_bytes = path.stat().st_size
        expected_bytes = item.get("bytes")
        if expected_bytes != actual_bytes:
            failures.append(f"{role}: byte mismatch for {relative}")
        expected_sha = item.get("sha256")
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_sha != actual_sha:
            failures.append(f"{role}: sha256 mismatch for {relative}")
    return PackageVerification(manifest_path=manifest, ok=not failures, checked_files=checked, failures=tuple(failures))


def _package_slug(csv_path: Path) -> str:
    stem = "".join(char.lower() if char.isalnum() else "-" for char in csv_path.stem)
    return "-".join(part for part in stem.split("-") if part)[:64] or "ads1292-session"


def _segment_gate_entry(result) -> dict | None:
    if result is None:
        return None
    return {
        "label": result.label,
        "passed": result.passed,
        "failures": result.failures,
        "segment_results": tuple(
            {
                "label": segment.label,
                "status": segment.status,
                "passed": segment.passed,
                "failures": segment.failures,
            }
            for segment in result.segment_results
        ),
    }


def _event_annotation_summary(events) -> dict:
    normalized = tuple(event.normalized() for event in events)
    labels: dict[str, int] = {}
    interval_events = 0
    total_annotated_seconds = 0.0
    for event in normalized:
        labels[event.label] = labels.get(event.label, 0) + 1
        if event.duration_seconds > 0:
            interval_events += 1
            total_annotated_seconds += event.duration_seconds
    return {
        "count": len(normalized),
        "point_events": len(normalized) - interval_events,
        "interval_events": interval_events,
        "total_annotated_seconds": round(total_annotated_seconds, 6),
        "labels": {label: labels[label] for label in sorted(labels)},
    }


def _acquisition_summary(provenance: AcquisitionProvenance | None) -> dict:
    if provenance is None:
        return {
            "mode": "unknown",
            "sample_rate_hz": None,
            "port": "",
            "csv_schema": "",
            "timestamp_reference": "",
            "csv_columns": tuple(),
            "raw_lsb_uv_per_count": None,
            "live_scale_uv_per_count": None,
            "live_scale_runs": 0,
        }
    normalized = provenance.normalized()
    raw_adc = normalized.raw_adc
    live = normalized.live_calibration
    return {
        "mode": normalized.acquisition_mode,
        "sample_rate_hz": normalized.sample_rate_hz,
        "port": normalized.port,
        "csv_schema": normalized.csv_schema,
        "timestamp_reference": normalized.timestamp_reference,
        "csv_columns": normalized.csv_columns,
        "raw_lsb_uv_per_count": raw_adc.get("raw_lsb_uv_per_count"),
        "live_scale_uv_per_count": live.get("mean_uv_per_count") if live else None,
        "live_scale_runs": live.get("runs", 0) if live else 0,
    }


def _file_entry(role: str, path: Path, package_dir: Path) -> dict[str, str | int]:
    data = path.read_bytes()
    return {
        "role": role,
        "path": str(path.relative_to(package_dir)),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
