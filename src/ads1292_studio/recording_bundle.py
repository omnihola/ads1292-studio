from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from ads1292_studio.acquisition import AcquisitionProvenance
from ads1292_studio.calibration import Calibration
from ads1292_studio.events import (
    DEFAULT_EVENT_SAMPLE_RATE_HZ,
    EVENT_ANNOTATIONS_SCHEMA,
    EVENT_SAMPLE_INDEX_REFERENCE,
    EVENT_TIMESTAMP_REFERENCE,
    EventMarker,
    event_id,
    event_sample_indices,
)
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.processing import RecordingProcessingSettings, build_processing_settings
from ads1292_studio.protocol import ProtocolStep, TestProtocol
from ads1292_studio.quality_gate import QualityGate


RECORDING_BUNDLE_SCHEMA = "ads1292-recording-bundle-v1"


def recording_bundle_path(csv_path: Path | str) -> Path:
    return Path(csv_path).with_suffix(".json")


def is_recording_bundle_path(path: Path | str) -> bool:
    candidate = Path(path)
    if not candidate.exists():
        return False
    try:
        data = json.loads(candidate.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("schema") == RECORDING_BUNDLE_SCHEMA


def read_recording_bundle(path_or_csv: Path | str) -> dict[str, Any]:
    path = Path(path_or_csv)
    if path.suffix.lower() == ".csv":
        path = recording_bundle_path(path)
    data = json.loads(path.read_text())
    if data.get("schema") != RECORDING_BUNDLE_SCHEMA:
        raise ValueError(f"not an ADS1292 recording bundle: {path}")
    return data


def write_recording_bundle(
    csv_path: Path | str,
    *,
    metadata: SessionMetadata,
    events: tuple[EventMarker, ...] | list[EventMarker],
    calibration: Calibration,
    acquisition: AcquisitionProvenance,
    protocol: TestProtocol,
    quality_gate: QualityGate,
    processing: RecordingProcessingSettings,
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
    created_at: str = "",
) -> Path:
    output = recording_bundle_path(csv_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_recording_bundle(
        csv_path=csv_path,
        metadata=metadata,
        events=tuple(events),
        calibration=calibration,
        acquisition=acquisition,
        protocol=protocol,
        quality_gate=quality_gate,
        processing=processing,
        sample_rate_hz=sample_rate_hz,
        created_at=created_at,
    )
    output.write_text(json.dumps(payload, indent=2) + "\n")
    return output


def build_recording_bundle(
    *,
    csv_path: Path | str,
    metadata: SessionMetadata,
    events: tuple[EventMarker, ...],
    calibration: Calibration,
    acquisition: AcquisitionProvenance,
    protocol: TestProtocol,
    quality_gate: QualityGate,
    processing: RecordingProcessingSettings,
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
    created_at: str = "",
) -> dict[str, Any]:
    csv = Path(csv_path)
    normalized_events = tuple(event.normalized() for event in events)
    return {
        "schema": RECORDING_BUNDLE_SCHEMA,
        "created_at": created_at,
        "csv_name": csv.name,
        "metadata": asdict(metadata.normalized()),
        "events": _events_payload(normalized_events, sample_rate_hz=sample_rate_hz),
        "calibration": asdict(calibration.normalized()),
        "acquisition": asdict(acquisition.normalized()),
        "protocol": asdict(protocol.normalized()),
        "quality_gate": asdict(quality_gate.normalized()),
        "processing": asdict(processing.normalized()),
    }


def metadata_from_bundle(bundle: dict[str, Any]) -> SessionMetadata:
    data = _mapping(bundle.get("metadata"))
    allowed = SessionMetadata.__dataclass_fields__
    return SessionMetadata(**{key: data[key] for key in allowed if key in data}).normalized()


def events_from_bundle(bundle: dict[str, Any]) -> tuple[EventMarker, ...]:
    events_payload = _mapping(bundle.get("events"))
    events = events_payload.get("events", [])
    return tuple(_event_from_mapping(item) for item in events if isinstance(item, dict))


def calibration_from_bundle(bundle: dict[str, Any]) -> Calibration:
    data = _mapping(bundle.get("calibration"))
    allowed = Calibration.__dataclass_fields__
    return Calibration(**{key: data[key] for key in allowed if key in data}).normalized()


def acquisition_from_bundle(bundle: dict[str, Any]) -> AcquisitionProvenance:
    data = _mapping(bundle.get("acquisition"))
    allowed = AcquisitionProvenance.__dataclass_fields__
    return AcquisitionProvenance(**{key: data[key] for key in allowed if key in data}).normalized()


def protocol_from_bundle(bundle: dict[str, Any]) -> TestProtocol:
    data = _mapping(bundle.get("protocol"))
    steps = tuple(
        ProtocolStep(
            start_seconds=float(item.get("start_seconds", 0.0) or 0.0),
            duration_seconds=float(item.get("duration_seconds", 0.0) or 0.0),
            label=str(item.get("label", "")),
            instruction=str(item.get("instruction", "")),
        ).normalized()
        for item in data.get("steps", ())
        if isinstance(item, dict)
    )
    return TestProtocol(
        name=str(data.get("name", "")),
        objective=str(data.get("objective", "")),
        operator_instructions=str(data.get("operator_instructions", "")),
        steps=steps,
        acceptance_notes=str(data.get("acceptance_notes", "")),
    ).normalized()


def quality_gate_from_bundle(bundle: dict[str, Any]) -> QualityGate:
    data = _mapping(bundle.get("quality_gate"))
    return QualityGate(
        min_duration_seconds=_float_with_default(data.get("min_duration_seconds"), 8.0),
        min_contact_ok_percent=_float_with_default(data.get("min_contact_ok_percent"), 95.0),
        min_r_peaks=int(_float_with_default(data.get("min_r_peaks"), 5.0)),
        min_hr_bpm=_float_with_default(data.get("min_hr_bpm"), 35.0),
        max_hr_bpm=_float_with_default(data.get("max_hr_bpm"), 180.0),
        require_qrs_clear=bool(data.get("require_qrs_clear", True)),
        max_baseline_drift_counts=_optional_float(data.get("max_baseline_drift_counts")),
        max_noise_rms_counts=_optional_float(data.get("max_noise_rms_counts")),
        max_peak_to_peak_counts=_optional_float(data.get("max_peak_to_peak_counts")),
    ).normalized()


def processing_from_bundle(bundle: dict[str, Any]) -> RecordingProcessingSettings:
    data = _mapping(bundle.get("processing"))
    if not data:
        return build_processing_settings()
    allowed = RecordingProcessingSettings.__dataclass_fields__
    return RecordingProcessingSettings(**{key: data[key] for key in allowed if key in data}).normalized()


def _events_payload(events: tuple[EventMarker, ...], *, sample_rate_hz: float) -> dict[str, Any]:
    sample_rate = float(sample_rate_hz) if sample_rate_hz > 0 else DEFAULT_EVENT_SAMPLE_RATE_HZ
    return {
        "schema": EVENT_ANNOTATIONS_SCHEMA,
        "timestamp_reference": EVENT_TIMESTAMP_REFERENCE,
        "sample_rate_hz": sample_rate,
        "sample_index_reference": EVENT_SAMPLE_INDEX_REFERENCE,
        "events": [_event_entry(event, sample_rate_hz=sample_rate) for event in events],
    }


def _event_entry(event: EventMarker, *, sample_rate_hz: float) -> dict[str, Any]:
    marker = event.normalized()
    return {
        "event_id": event_id(marker, sample_rate_hz=sample_rate_hz),
        "timestamp_seconds": marker.timestamp_seconds,
        "start_seconds": marker.timestamp_seconds,
        "end_seconds": marker.end_seconds,
        "duration_seconds": marker.duration_seconds,
        **event_sample_indices(marker, sample_rate_hz),
        "event_type": "interval" if marker.duration_seconds > 0 else "point",
        "label": marker.label,
        "notes": marker.notes,
    }


def _event_from_mapping(item: dict[str, Any]) -> EventMarker:
    start = item.get("timestamp_seconds", item.get("start_seconds", 0.0))
    duration = item.get("duration_seconds")
    if duration in (None, ""):
        start_value = float(item.get("start_seconds", start) or 0.0)
        end_value = float(item.get("end_seconds", start_value) or start_value)
        duration = max(0.0, end_value - start_value)
        start = start_value
    return EventMarker(
        timestamp_seconds=float(start or 0.0),
        duration_seconds=float(duration or 0.0),
        label=str(item.get("label", "")),
        notes=str(item.get("notes", "")),
    ).normalized()


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _float_with_default(value: Any, default: float) -> float:
    if value in (None, ""):
        return float(default)
    return float(value)
