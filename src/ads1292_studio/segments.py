from __future__ import annotations

from dataclasses import dataclass

from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality import compute_quality_metrics
from ads1292_studio.quality_gate import QualityGate


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


@dataclass(frozen=True)
class SegmentQualityResult:
    label: str
    passed: bool
    failures: tuple[str, ...]

    @property
    def status(self) -> str:
        return "Pass" if self.passed else "Fail"


@dataclass(frozen=True)
class SegmentQualityGateResult:
    passed: bool
    segment_results: tuple[SegmentQualityResult, ...]
    failures: tuple[str, ...]

    @property
    def label(self) -> str:
        return "Pass" if self.passed else "Fail"


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


def evaluate_segment_quality_gates(
    segments: tuple[SegmentMetrics, ...] | list[SegmentMetrics],
    gate: QualityGate | None = None,
) -> SegmentQualityGateResult:
    # Normalize like evaluate_quality_gate so an out-of-range gate yields the
    # same verdict at the segment and recording levels.
    gate = (gate or QualityGate()).normalized()
    segment_results = tuple(_evaluate_segment(segment, gate) for segment in segments)
    failures = tuple(failure for result in segment_results for failure in result.failures)
    return SegmentQualityGateResult(
        passed=not failures,
        segment_results=segment_results,
        failures=failures,
    )


def _evaluate_segment(segment: SegmentMetrics, gate: QualityGate) -> SegmentQualityResult:
    failures: list[str] = []
    if segment.sample_count <= 0:
        failures.append(f"{segment.label}: no data")
        return SegmentQualityResult(label=segment.label, passed=False, failures=tuple(failures))
    if segment.contact_ok_percent < gate.min_contact_ok_percent:
        failures.append(
            f"{segment.label}: contact {segment.contact_ok_percent:.2f}% < {gate.min_contact_ok_percent:.2f}%"
        )
    if segment.r_peaks < gate.min_r_peaks:
        failures.append(f"{segment.label}: R peaks {segment.r_peaks} < {gate.min_r_peaks}")
    if segment.hr_median_bpm > 0 and segment.hr_median_bpm < gate.min_hr_bpm:
        failures.append(f"{segment.label}: median HR {segment.hr_median_bpm:.1f} bpm < {gate.min_hr_bpm:.1f} bpm")
    if segment.hr_median_bpm > gate.max_hr_bpm:
        failures.append(f"{segment.label}: median HR {segment.hr_median_bpm:.1f} bpm > {gate.max_hr_bpm:.1f} bpm")
    if gate.max_baseline_drift_counts is not None and segment.baseline_drift_counts > gate.max_baseline_drift_counts:
        failures.append(
            f"{segment.label}: baseline drift {segment.baseline_drift_counts:.1f} counts > "
            f"{gate.max_baseline_drift_counts:.1f} counts"
        )
    if gate.max_noise_rms_counts is not None and segment.noise_rms_counts > gate.max_noise_rms_counts:
        failures.append(
            f"{segment.label}: noise RMS {segment.noise_rms_counts:.1f} counts > "
            f"{gate.max_noise_rms_counts:.1f} counts"
        )
    if gate.max_peak_to_peak_counts is not None and segment.peak_to_peak_counts > gate.max_peak_to_peak_counts:
        failures.append(
            f"{segment.label}: peak-to-peak {segment.peak_to_peak_counts:.1f} counts > "
            f"{gate.max_peak_to_peak_counts:.1f} counts"
        )
    return SegmentQualityResult(label=segment.label, passed=not failures, failures=tuple(failures))
