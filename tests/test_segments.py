import numpy as np

from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.segments import (
    SegmentMetrics,
    analyze_protocol_segments,
    evaluate_segment_quality_gates,
)


def _protocol_samples(sample_rate_hz: float = 500.0) -> tuple[StreamSample, ...]:
    t = np.arange(0, 9, 1 / sample_rate_hz)
    ch2 = np.zeros_like(t)
    for peak in np.arange(0.4, 8.8, 0.6):
        ch2 += 460 * np.exp(-0.5 * ((t - peak) / 0.011) ** 2)
    motion_mask = (t >= 3.0) & (t < 6.0)
    ch2[motion_mask] += 180 * np.sin(2 * np.pi * 12 * t[motion_mask])
    ch2[motion_mask] += 120 * (t[motion_mask] - 3.0) / 3.0
    samples: list[StreamSample] = []
    for index, value in enumerate(ch2):
        samples.append(
            StreamSample(
                timestamp=index / sample_rate_hz,
                ch1=0,
                ch2=int(round(value)),
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            )
        )
    return tuple(samples)


def test_analyze_protocol_segments_returns_metrics_per_step() -> None:
    protocol = TestProtocol(
        name="motion challenge",
        steps=(
            ProtocolStep(0.0, 3.0, "baseline", "Sit still."),
            ProtocolStep(3.0, 3.0, "motion", "Move arm."),
            ProtocolStep(6.0, 3.0, "recovery", "Sit still again."),
        ),
    )

    segments = analyze_protocol_segments(_protocol_samples(), protocol, sample_rate_hz=500.0, source="CH2")

    assert tuple(segment.label for segment in segments) == ("baseline", "motion", "recovery")
    assert all(segment.sample_count == 1500 for segment in segments)
    assert all(segment.contact_ok_percent == 100.0 for segment in segments)
    assert all(segment.r_peaks >= 4 for segment in segments)
    assert segments[1].noise_rms_counts > segments[0].noise_rms_counts
    assert segments[1].baseline_drift_counts > segments[0].baseline_drift_counts
    assert segments[1].quality_label in {"Good ECG/QRS", "Usable ECG/QRS", "Needs review"}


def test_analyze_protocol_segments_marks_out_of_range_step_empty() -> None:
    protocol = TestProtocol(
        name="too long",
        steps=(ProtocolStep(20.0, 5.0, "late", "No data here."),),
    )

    segments = analyze_protocol_segments(_protocol_samples(), protocol, sample_rate_hz=500.0, source="CH2")

    assert len(segments) == 1
    assert segments[0].label == "late"
    assert segments[0].sample_count == 0
    assert segments[0].quality_label == "No data"


def test_evaluate_segment_quality_gates_marks_motion_failures() -> None:
    protocol = TestProtocol(
        name="motion challenge",
        steps=(
            ProtocolStep(0.0, 3.0, "baseline", "Sit still."),
            ProtocolStep(3.0, 3.0, "motion", "Move arm."),
        ),
    )
    segments = analyze_protocol_segments(_protocol_samples(), protocol, sample_rate_hz=500.0, source="CH2")
    noise_limit = (segments[0].noise_rms_counts + segments[1].noise_rms_counts) / 2.0

    result = evaluate_segment_quality_gates(
        segments,
        QualityGate(min_contact_ok_percent=95.0, min_r_peaks=3, max_noise_rms_counts=noise_limit),
    )

    assert result.passed is False
    assert result.label == "Fail"
    assert result.segment_results[0].label == "baseline"
    assert result.segment_results[0].passed is True
    assert result.segment_results[1].label == "motion"
    assert result.segment_results[1].passed is False
    assert any("motion: noise RMS" in failure for failure in result.failures)


def test_evaluate_segment_quality_gates_normalizes_out_of_range_gate() -> None:
    """The segment gate must clamp an out-of-range gate like the recording-level
    evaluate_quality_gate does, so the two QC verdicts agree on the same data.

    Regression: evaluate_segment_quality_gates used the gate raw, so an invalid
    min_contact_ok_percent (e.g. 150) was applied as-is to segments while the
    recording-level gate clamped it to 100 — divergent verdicts.
    """
    seg = SegmentMetrics(
        label="baseline", start_seconds=0.0, duration_seconds=10.0, sample_count=5000,
        ecg_source="CH2", contact_ok_percent=100.0, r_peaks=10, hr_median_bpm=60.0,
        baseline_drift_counts=1.0, noise_rms_counts=1.0, peak_to_peak_counts=100.0,
        quality_label="Good",
    )
    gate = QualityGate(min_contact_ok_percent=150.0)  # invalid; normalizes to 100

    result = evaluate_segment_quality_gates([seg], gate)

    assert result.passed is True
    assert not any("contact" in failure for failure in result.failures)


def test_evaluate_segment_quality_gates_fails_empty_segments() -> None:
    protocol = TestProtocol(name="missing", steps=(ProtocolStep(20.0, 5.0, "late", "No data."),))
    segments = analyze_protocol_segments(_protocol_samples(), protocol, sample_rate_hz=500.0, source="CH2")

    result = evaluate_segment_quality_gates(segments, QualityGate())

    assert result.passed is False
    assert result.segment_results[0].failures == ("late: no data",)
