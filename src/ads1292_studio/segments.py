from __future__ import annotations

from dataclasses import dataclass

from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality import compute_quality_metrics


@dataclass(frozen=True)
class SegmentMetrics:
    label: str
    start_seconds: float
    duration_seconds: float
    sample_count: int
    ecg_source: str
    contact_ok_percent: float
    r_peaks: int
    hr_median_bpm: float
    baseline_drift_counts: float
    noise_rms_counts: float
    peak_to_peak_counts: float
    quality_label: str


def analyze_protocol_segments(
    samples: tuple[StreamSample, ...] | list[StreamSample],
    protocol: TestProtocol,
    sample_rate_hz: float = 500.0,
    source: str = "Auto",
) -> tuple[SegmentMetrics, ...]:
    sample_tuple = tuple(samples)
    normalized_protocol = protocol.normalized()
    if not normalized_protocol.steps:
        return tuple()

    origin = sample_tuple[0].timestamp if sample_tuple else 0.0
    segments: list[SegmentMetrics] = []
    for step in normalized_protocol.steps:
        start = origin + step.start_seconds
        stop = start + step.duration_seconds
        segment_samples = tuple(sample for sample in sample_tuple if start <= sample.timestamp < stop)
        if not segment_samples:
            segments.append(
                SegmentMetrics(
                    label=step.label,
                    start_seconds=step.start_seconds,
                    duration_seconds=step.duration_seconds,
                    sample_count=0,
                    ecg_source=source if source != "Auto" else "Auto",
                    contact_ok_percent=0.0,
                    r_peaks=0,
                    hr_median_bpm=0.0,
                    baseline_drift_counts=0.0,
                    noise_rms_counts=0.0,
                    peak_to_peak_counts=0.0,
                    quality_label="No data",
                )
            )
            continue

        metrics = compute_quality_metrics(segment_samples, sample_rate_hz=sample_rate_hz, source=source)
        segments.append(
            SegmentMetrics(
                label=step.label,
                start_seconds=step.start_seconds,
                duration_seconds=step.duration_seconds,
                sample_count=metrics.sample_count,
                ecg_source=metrics.ecg_source,
                contact_ok_percent=metrics.contact_ok_percent,
                r_peaks=metrics.r_peaks,
                hr_median_bpm=metrics.hr_median_bpm,
                baseline_drift_counts=metrics.baseline_drift_counts,
                noise_rms_counts=metrics.noise_rms_counts,
                peak_to_peak_counts=metrics.peak_to_peak_counts,
                quality_label=metrics.quality_label,
            )
        )
    return tuple(segments)
