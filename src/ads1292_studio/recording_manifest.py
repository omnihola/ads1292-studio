from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

from ads1292_studio.acquisition import read_acquisition_json
from ads1292_studio.hashing import sha256_file
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.events import (
    DEFAULT_EVENT_SAMPLE_RATE_HZ,
    EVENT_ANNOTATIONS_SCHEMA,
    EVENT_SAMPLE_INDEX_REFERENCE,
    EVENT_TIMESTAMP_REFERENCE,
    EventMarker,
    event_sample_indices,
    read_events_csv,
    read_events_json,
)
from ads1292_studio.processing import read_processing_json
from ads1292_studio.recording_bundle import (
    acquisition_from_bundle,
    events_from_bundle,
    is_recording_bundle_path,
    processing_from_bundle,
    read_recording_bundle,
    recording_bundle_path,
)
from ads1292_studio.xlsx_io import recording_xlsx_path


RECORDING_MANIFEST_SCHEMA = "ads1292-recording-manifest-v1"

REQUIRED_SIDECAR_ROLES = (
    "metadata",
    "event_annotations",
    "calibration",
    "acquisition",
    "protocol",
    "quality_gate",
    "processing",
)

SIDECAR_PATHS = (
    ("metadata", ".json"),
    ("events", ".events.json"),
    ("events_csv", ".events.csv"),
    ("calibration", ".calibration.json"),
    ("acquisition", ".acquisition.json"),
    ("protocol", ".protocol.json"),
    ("quality_gate", ".quality-gate.json"),
    ("processing", ".processing.json"),
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
    xlsx_path = recording_xlsx_path(source_csv)
    if xlsx_path.exists():
        files.append(_file_entry("recording_xlsx", xlsx_path))
    present_roles = {"raw_csv"}
    events: tuple[EventMarker, ...] = tuple()
    event_source_role = "none"
    event_source_path = ""
    acquisition = None
    processing = None
    bundle_path = recording_bundle_path(source_csv)
    if is_recording_bundle_path(bundle_path):
        bundle = read_recording_bundle(bundle_path)
        files.append(_file_entry("recording_bundle", bundle_path))
        present_roles.add("recording_bundle")
        present_roles.update(REQUIRED_SIDECAR_ROLES)
        events = events_from_bundle(bundle)
        event_source_role = "recording_bundle"
        event_source_path = bundle_path.name
        acquisition = acquisition_from_bundle(bundle)
        processing = processing_from_bundle(bundle)

    if "recording_bundle" not in present_roles:
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
            elif role == "processing":
                processing = read_processing_json(path)

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
            **recording_sample_index_summary(recording.samples),
        },
        "sidecar_completeness": _sidecar_completeness(present_roles),
        "event_annotations": _event_annotation_summary(
            events,
            source_role=event_source_role,
            source_path=event_source_path,
            sample_rate_hz=recording.sample_rate_hz,
        ),
        "acquisition": _acquisition_summary(
            acquisition,
            actual_sample_count=len(recording.samples),
            actual_span_seconds=round(float(recording.duration_seconds), 6),
        ),
        "processing": _processing_summary(processing),
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
        actual_sha = sha256_file(path)
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
    return {
        "role": role,
        "path": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
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
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
) -> dict:
    labels: dict[str, int] = {}
    interval_events = 0
    total_annotated_seconds = 0.0
    total_annotated_samples = 0
    sample_rate = sample_rate_hz if sample_rate_hz > 0 else DEFAULT_EVENT_SAMPLE_RATE_HZ
    normalized_events = tuple(event.normalized() for event in events)
    for marker in normalized_events:
        labels[marker.label] = labels.get(marker.label, 0) + 1
        if marker.duration_seconds > 0:
            interval_events += 1
            total_annotated_seconds += marker.duration_seconds
            total_annotated_samples += event_sample_indices(marker, sample_rate)["duration_samples"]
    return {
        "schema": EVENT_ANNOTATIONS_SCHEMA,
        "timestamp_reference": EVENT_TIMESTAMP_REFERENCE,
        "sample_rate_hz": sample_rate,
        "sample_index_reference": EVENT_SAMPLE_INDEX_REFERENCE,
        "count": len(normalized_events),
        "point_events": len(normalized_events) - interval_events,
        "interval_events": interval_events,
        "total_annotated_seconds": round(total_annotated_seconds, 6),
        "total_annotated_samples": total_annotated_samples,
        "labels": {label: labels[label] for label in sorted(labels)},
        "source_role": source_role,
        "source_path": source_path,
        "events": [_event_annotation_entry(event, sample_rate_hz=sample_rate) for event in normalized_events],
    }


def _event_annotation_entry(event: EventMarker, *, sample_rate_hz: float) -> dict:
    marker = event.normalized()
    return {
        "start_seconds": round(marker.timestamp_seconds, 6),
        "end_seconds": round(marker.end_seconds, 6),
        "duration_seconds": round(marker.duration_seconds, 6),
        **event_sample_indices(marker, sample_rate_hz),
        "label": marker.label,
        "notes": marker.notes,
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


def _processing_summary(processing) -> dict:
    if processing is None:
        return {}
    normalized = processing.normalized()
    return {
        "schema": normalized.schema,
        "display": normalized.display,
        "software_filters": normalized.software_filters,
        "sample_rate_hz": normalized.sample_rate_hz,
        "ecg_inverted": normalized.ecg_inverted,
        "smoothing_window": normalized.smoothing_window,
        "processing_notes": normalized.processing_notes,
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


def recording_sample_index_summary(samples) -> dict[str, int | bool]:
    if not samples:
        return {
            "first_sample_index": 0,
            "last_sample_index": 0,
            "sample_index_contiguous": True,
            "sample_index_gap_count": 0,
        }
    indices = [_sample_index_or_row(sample, index) for index, sample in enumerate(samples)]
    gap_count = sum(
        1
        for previous, current in zip(indices, indices[1:])
        if current - previous != 1
    )
    return {
        "first_sample_index": indices[0],
        "last_sample_index": indices[-1],
        "sample_index_contiguous": gap_count == 0,
        "sample_index_gap_count": gap_count,
    }


def _sample_index_or_row(sample, row_index: int) -> int:
    sample_index = getattr(sample, "sample_index", None)
    return int(row_index) if sample_index is None else int(sample_index)


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
    expected_sample_index = _expected_sample_index_summary(recording_entry)
    actual_sample_index = recording_sample_index_summary(recording.samples)
    if expected_sample_index["first_sample_index"] != actual_sample_index["first_sample_index"]:
        failures.append(
            "recording first sample index mismatch: "
            f"manifest {expected_sample_index['first_sample_index']}, "
            f"actual {actual_sample_index['first_sample_index']}"
        )
    if expected_sample_index["last_sample_index"] != actual_sample_index["last_sample_index"]:
        failures.append(
            "recording last sample index mismatch: "
            f"manifest {expected_sample_index['last_sample_index']}, "
            f"actual {actual_sample_index['last_sample_index']}"
        )
    if expected_sample_index["sample_index_contiguous"] != actual_sample_index["sample_index_contiguous"]:
        failures.append(
            "recording sample index continuity mismatch: "
            f"manifest {expected_sample_index['sample_index_contiguous']}, "
            f"actual {actual_sample_index['sample_index_contiguous']}"
        )
    if expected_sample_index["sample_index_gap_count"] != actual_sample_index["sample_index_gap_count"]:
        failures.append(
            "recording sample index gap count mismatch: "
            f"manifest {expected_sample_index['sample_index_gap_count']}, "
            f"actual {actual_sample_index['sample_index_gap_count']}"
        )
    return tuple(failures)


def _expected_sample_index_summary(recording_entry: dict) -> dict[str, int | bool]:
    sample_count = int(recording_entry.get("sample_count", 0) or 0)
    return {
        "first_sample_index": int(recording_entry.get("first_sample_index", 0) or 0),
        "last_sample_index": int(recording_entry.get("last_sample_index", max(0, sample_count - 1)) or 0),
        "sample_index_contiguous": bool(recording_entry.get("sample_index_contiguous", True)),
        "sample_index_gap_count": int(recording_entry.get("sample_index_gap_count", 0) or 0),
    }
