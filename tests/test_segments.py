import numpy as np

from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol
from ads1292_studio.segments import analyze_protocol_segments


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
