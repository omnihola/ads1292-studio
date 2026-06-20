from __future__ import annotations

from typing import Protocol

from ads1292_studio.calibration import Calibration
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.protocol import ProtocolStep, TestProtocol, protocol_template
from ads1292_studio.quality_gate import QualityGate


class StringVariable(Protocol):
    def get(self) -> str: ...


def _float_from_var(variable: StringVariable, fallback: float) -> float:
    try:
        return float(variable.get())
    except ValueError:
        return fallback


def _metadata_from_values(
    *,
    session_id: str,
    subject_id: str,
    electrode: str,
    montage: str,
    operator: str,
    notes: str,
) -> SessionMetadata:
    return SessionMetadata(
        session_id=session_id,
        subject_id=subject_id,
        electrode=electrode,
        montage=montage,
        operator=operator,
        notes=notes,
    ).normalized()


def _calibration_from_values(*, label: str, vref_mv: str, pga_gain: str) -> Calibration:
    return Calibration(
        vref_mv=_float_value(vref_mv, 2420.0),
        pga_gain=_float_value(pga_gain, 6.0),
        adc_bits=24,
        label=label,
    ).normalized()


def _protocol_from_values(
    *,
    name: str,
    objective: str,
    steps_text: str,
    acceptance_notes: str,
) -> TestProtocol:
    return TestProtocol(
        name=name,
        objective=objective,
        operator_instructions="Follow the listed protocol steps.",
        steps=_parse_protocol_steps(steps_text),
        acceptance_notes=acceptance_notes,
    ).normalized()


def _quality_gate_from_values(values: dict[str, object]) -> QualityGate:
    return QualityGate(
        min_duration_seconds=_float_value(values.get("min_duration_seconds"), 8.0),
        min_contact_ok_percent=_float_value(values.get("min_contact_ok_percent"), 95.0),
        min_r_peaks=_int_value(values.get("min_r_peaks"), 5),
        min_hr_bpm=_float_value(values.get("min_hr_bpm"), 35.0),
        max_hr_bpm=_float_value(values.get("max_hr_bpm"), 180.0),
        require_qrs_clear=bool(values.get("require_qrs_clear", True)),
        max_baseline_drift_counts=_optional_float_value(values.get("max_baseline_drift_counts")),
        max_noise_rms_counts=_optional_float_value(values.get("max_noise_rms_counts")),
        max_peak_to_peak_counts=_optional_float_value(values.get("max_peak_to_peak_counts")),
    ).normalized()


def _quality_gate_to_values(gate: QualityGate) -> dict[str, object]:
    normalized = gate.normalized()
    return {
        "min_duration_seconds": _format_number(normalized.min_duration_seconds),
        "min_contact_ok_percent": _format_number(normalized.min_contact_ok_percent),
        "min_r_peaks": str(normalized.min_r_peaks),
        "min_hr_bpm": _format_number(normalized.min_hr_bpm),
        "max_hr_bpm": _format_number(normalized.max_hr_bpm),
        "require_qrs_clear": normalized.require_qrs_clear,
        "max_baseline_drift_counts": _format_optional_number(normalized.max_baseline_drift_counts),
        "max_noise_rms_counts": _format_optional_number(normalized.max_noise_rms_counts),
        "max_peak_to_peak_counts": _format_optional_number(normalized.max_peak_to_peak_counts),
    }


def _float_value(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _int_value(value: object, fallback: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _optional_float_value(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    return f"{value:g}"


def _format_optional_number(value: float | None) -> str:
    return "" if value is None else _format_number(value)


def _format_protocol_steps(steps: tuple[ProtocolStep, ...]) -> str:
    return "; ".join(
        f"{step.start_seconds:g},{step.duration_seconds:g},{step.label},{step.instruction}" for step in steps
    )


def _parse_protocol_steps(text: str) -> tuple[ProtocolStep, ...]:
    steps: list[ProtocolStep] = []
    for chunk in text.split(";"):
        parts = [part.strip() for part in chunk.split(",", 3)]
        if len(parts) != 4:
            continue
        try:
            start = float(parts[0])
            duration = float(parts[1])
        except ValueError:
            continue
        steps.append(ProtocolStep(start, duration, parts[2], parts[3]).normalized())
    if steps:
        return tuple(steps)
    return protocol_template().steps
