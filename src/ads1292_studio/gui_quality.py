from __future__ import annotations

from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality import compute_quality_metrics
from ads1292_studio.quality_gate import QualityGate, evaluate_quality_gate
from ads1292_studio.segments import analyze_protocol_segments, evaluate_segment_quality_gates


def build_quality_text(
    samples: tuple[StreamSample, ...],
    status_values: tuple[int, ...],
    source: str,
    selected_source: str,
    valid_rr: int,
    protocol: TestProtocol | None = None,
    sample_rate_hz: float = 500.0,
    gate: QualityGate | None = None,
) -> str:
    lead_bad = sum(1 for value in status_values if value != 0)
    contact = "OK" if lead_bad == 0 else f"{lead_bad} bad samples"
    rhythm = "detecting" if valid_rr < 2 else "R peaks detected"
    metrics = compute_quality_metrics(samples, sample_rate_hz, selected_source)
    gate_result = evaluate_quality_gate(metrics, gate)
    parts = [
        f"Gate {gate_result.label}",
        f"Contact {contact}",
        rhythm,
        f"source {source}",
        f"drift {metrics.baseline_drift_counts:.0f} ct",
        f"noise {metrics.noise_rms_counts:.1f} ct",
    ]
    if protocol is not None:
        segments = analyze_protocol_segments(samples, protocol, sample_rate_hz=sample_rate_hz, source=metrics.ecg_source)
        if segments:
            segment_result = evaluate_segment_quality_gates(segments, gate)
            failures = "; ".join(segment_result.failures[:2])
            suffix = f": {failures}" if failures else ""
            parts.append(f"Segment Gate {segment_result.label}{suffix}")
    return " | ".join(parts)


def protocol_ready_for_live_quality(
    samples: tuple[StreamSample, ...],
    protocol: TestProtocol,
    sample_rate_hz: float = 500.0,
) -> bool:
    steps = protocol.normalized().steps
    if not steps:
        return False
    required_seconds = max(step.start_seconds + step.duration_seconds for step in steps)
    observed_seconds = len(samples) / sample_rate_hz
    return observed_seconds >= required_seconds
