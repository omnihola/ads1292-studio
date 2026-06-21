from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path

from ads1292_studio.acquisition import read_acquisition_json
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.events import (
    EVENT_ANNOTATIONS_SCHEMA,
    EVENT_TIMESTAMP_REFERENCE,
    EventMarker,
    read_events_csv,
    read_events_json,
)


RECORDING_MANIFEST_SCHEMA = "ads1292-recording-manifest-v1"

REQUIRED_SIDECAR_ROLES = (
    "metadata",
    "event_annotations",
    "calibration",
    "acquisition",
    "protocol",
    "quality_gate",
)

SIDECAR_PATHS = (
    ("metadata", ".json"),
    ("events", ".events.json"),
    ("events_csv", ".events.csv"),
    ("calibration", ".calibration.json"),
    ("acquisition", ".acquisition.json"),
    ("protocol", ".protocol.json"),
    ("quality_gate", ".quality-gate.json"),
)


@dataclass(frozen=True)
class RecordingManifestVerification:
    manifest_path: Path
    ok: bool
    checked_files: int
    failures: tuple[str, ...]


def build_recording_manifest(
    csv_path: Path | str,
    *,
    created_at: str | None = None,
) -> dict:
    source_csv = Path(csv_path)
    recording = read_recording_csv(source_csv)
    files = [_file_entry("raw_csv", source_csv)]
    present_roles = {"raw_csv"}
    events: tuple[EventMarker, ...] = tuple()
    event_source_role = "none"
    event_source_path = ""
    acquisition = None

    for role, suffix in SIDECAR_PATHS:
        path = source_csv.with_suffix(suffix)
        if not path.exists():
            continue
        files.append(_file_entry(role, path))
        present_roles.add(role)
        if role == "events":
            events = read_events_json(path)
            event_source_role = role
            event_source_path = path.name
        elif role == "events_csv" and not events:
            events = read_events_csv(path)
            event_source_role = role
            event_source_path = path.name
        elif role == "acquisition":
            acquisition = read_acquisition_json(path)

    return {
        "schema": RECORDING_MANIFEST_SCHEMA,
        "created_at": created_at or datetime.now().isoformat(timespec="seconds"),
        "source_csv": source_csv.name,
        "recording": {
            "sample_count": len(recording.samples),
            "duration_seconds": round(float(recording.duration_seconds), 6),
            "sample_rate_hz": recording.sample_rate_hz,
            "first_timestamp_seconds": _first_timestamp(recording.samples),
            "last_timestamp_seconds": _last_timestamp(recording.samples),
        },
        "sidecar_completeness": _sidecar_completeness(present_roles),
        "event_annotations": _event_annotation_summary(
            events,
            source_role=event_source_role,
            source_path=event_source_path,
        ),
        "acquisition": _acquisition_summary(
            acquisition,
            actual_sample_count=len(recording.samples),
            actual_span_seconds=round(float(recording.duration_seconds), 6),
        ),
        "files": files,
    }


def write_recording_manifest(
    csv_path: Path | str,
    *,
    created_at: str | None = None,
) -> Path:
    source_csv = Path(csv_path)
    output = source_csv.with_suffix(".manifest.json")
    output.write_text(json.dumps(build_recording_manifest(source_csv, created_at=created_at), indent=2) + "\n")
    return output


def verify_recording_manifest(manifest_path: Path | str) -> RecordingManifestVerification:
    manifest = Path(manifest_path)
    base_dir = manifest.parent
    failures: list[str] = []
    try:
        payload = json.loads(manifest.read_text())
    except Exception as exc:
        return RecordingManifestVerification(
            manifest_path=manifest,
            ok=False,
            checked_files=0,
            failures=(f"manifest read failed: {exc}",),
        )

    checked = 0
    for item in payload.get("files", []):
        role = str(item.get("role", "unknown"))
        relative = item.get("path")
        if not isinstance(relative, str):
            failures.append(f"{role}: missing path")
            continue
        path = base_dir / relative
        if not path.exists():
            failures.append(f"{role}: missing file {relative}")
            continue
        checked += 1
        expected_bytes = item.get("bytes")
        actual_bytes = path.stat().st_size
        if expected_bytes != actual_bytes:
            failures.append(f"{role}: byte mismatch for {relative}")
        expected_sha = item.get("sha256")
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_sha != actual_sha:
            failures.append(f"{role}: sha256 mismatch for {relative}")

    missing_roles = tuple(payload.get("sidecar_completeness", {}).get("missing_roles", ()))
    if missing_roles:
        failures.append(f"required sidecars missing: {', '.join(missing_roles)}")
    acquisition_audit = str(payload.get("acquisition", {}).get("completion_audit", "unknown"))
    if acquisition_audit != "pass":
        failures.append(f"acquisition completion audit failed: {acquisition_audit}")
    failures.extend(_recording_metric_failures(payload, base_dir))
    return RecordingManifestVerification(
        manifest_path=manifest,
        ok=not failures,
        checked_files=checked,
        failures=tuple(failures),
    )


def _file_entry(role: str, path: Path) -> dict[str, str | int]:
    data = path.read_bytes()
    return {
        "role": role,
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _sidecar_completeness(present_roles: set[str]) -> dict:
    present_required = tuple(role for role in REQUIRED_SIDECAR_ROLES if _required_role_present(role, present_roles))
    missing = tuple(role for role in REQUIRED_SIDECAR_ROLES if role not in present_required)
    return {
        "required_roles": list(REQUIRED_SIDECAR_ROLES),
        "present_roles": list(present_required),
        "missing_roles": list(missing),
        "complete": not missing,
    }


def _required_role_present(role: str, present_roles: set[str]) -> bool:
    if role == "event_annotations":
        return bool({"events", "events_csv"} & present_roles)
    return role in present_roles


def _event_annotation_summary(
    events: tuple[EventMarker, ...],
    *,
    source_role: str,
    source_path: str,
) -> dict:
    labels: dict[str, int] = {}
    interval_events = 0
    total_annotated_seconds = 0.0
    for event in events:
        marker = event.normalized()
        labels[marker.label] = labels.get(marker.label, 0) + 1
        if marker.duration_seconds > 0:
            interval_events += 1
            total_annotated_seconds += marker.duration_seconds
    return {
        "schema": EVENT_ANNOTATIONS_SCHEMA,
        "timestamp_reference": EVENT_TIMESTAMP_REFERENCE,
        "count": len(events),
        "point_events": len(events) - interval_events,
        "interval_events": interval_events,
        "total_annotated_seconds": round(total_annotated_seconds, 6),
        "labels": {label: labels[label] for label in sorted(labels)},
        "source_role": source_role,
        "source_path": source_path,
    }


def _acquisition_summary(
    provenance,
    *,
    actual_sample_count: int,
    actual_span_seconds: float,
) -> dict:
    if provenance is None:
        return _unknown_acquisition(actual_sample_count, actual_span_seconds)
    normalized = provenance.normalized()
    completion = normalized.completion
    audit, sample_delta, span_delta = _completion_audit(
        completion,
        actual_sample_count=actual_sample_count,
        actual_span_seconds=actual_span_seconds,
    )
    return {
        "mode": normalized.acquisition_mode,
        "sample_rate_hz": normalized.sample_rate_hz,
        "port": normalized.port,
        "csv_schema": normalized.csv_schema,
        "timestamp_reference": normalized.timestamp_reference,
        "completion_status": completion.get("status", "open"),
        "sample_count": completion.get("sample_count", 0),
        "sample_span_seconds": completion.get("sample_span_seconds", 0.0),
        "actual_sample_count": actual_sample_count,
        "actual_span_seconds": actual_span_seconds,
        "completion_audit": audit,
        "sample_count_delta": sample_delta,
        "sample_span_delta_seconds": span_delta,
    }


def _unknown_acquisition(actual_sample_count: int, actual_span_seconds: float) -> dict:
    return {
        "mode": "unknown",
        "sample_rate_hz": None,
        "port": "",
        "csv_schema": "",
        "timestamp_reference": "",
        "completion_status": "unknown",
        "sample_count": 0,
        "sample_span_seconds": 0.0,
        "actual_sample_count": actual_sample_count,
        "actual_span_seconds": actual_span_seconds,
        "completion_audit": "unknown",
        "sample_count_delta": 0,
        "sample_span_delta_seconds": 0.0,
    }


def _completion_audit(
    completion: dict,
    *,
    actual_sample_count: int,
    actual_span_seconds: float,
) -> tuple[str, int, float]:
    status = str(completion.get("status", "unknown"))
    if status == "open":
        return "pending", 0, 0.0
    if status != "finalized":
        return "unknown", 0, 0.0
    sample_count = max(0, int(float(completion.get("sample_count", 0) or 0)))
    span_seconds = round(float(completion.get("sample_span_seconds", 0.0) or 0.0), 6)
    sample_delta = sample_count - int(actual_sample_count)
    span_delta = round(span_seconds - float(actual_span_seconds), 6)
    if sample_delta == 0 and abs(span_delta) <= 0.001:
        return "pass", sample_delta, span_delta
    return "fail", sample_delta, span_delta


def _first_timestamp(samples) -> float:
    if not samples:
        return 0.0
    return round(float(samples[0].timestamp), 6)


def _last_timestamp(samples) -> float:
    if not samples:
        return 0.0
    return round(float(samples[-1].timestamp), 6)


def _recording_metric_failures(payload: dict, base_dir: Path) -> tuple[str, ...]:
    source_name = payload.get("source_csv")
    if not isinstance(source_name, str) or not source_name:
        return ("manifest source_csv missing",)
    csv_path = base_dir / source_name
    if not csv_path.exists():
        return (f"source_csv missing: {source_name}",)
    try:
        recording = read_recording_csv(csv_path)
    except Exception as exc:
        return (f"source_csv read failed: {exc}",)
    recording_entry = payload.get("recording", {})
    failures: list[str] = []
    expected_count = int(recording_entry.get("sample_count", 0) or 0)
    actual_count = len(recording.samples)
    if expected_count != actual_count:
        failures.append(f"recording sample count mismatch: manifest {expected_count}, actual {actual_count}")
    expected_duration = round(float(recording_entry.get("duration_seconds", 0.0) or 0.0), 6)
    actual_duration = round(float(recording.duration_seconds), 6)
    if abs(expected_duration - actual_duration) > 0.001:
        failures.append(f"recording duration mismatch: manifest {expected_duration}, actual {actual_duration}")
    return tuple(failures)
