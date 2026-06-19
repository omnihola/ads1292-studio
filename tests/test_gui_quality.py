import numpy as np

from ads1292_studio.gui_quality import build_quality_text, protocol_ready_for_live_quality
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol
from ads1292_studio.quality_gate import QualityGate


def _samples(sample_rate_hz: float = 500.0) -> tuple[StreamSample, ...]:
    t = np.arange(0, 3, 1 / sample_rate_hz)
    ch2 = np.zeros_like(t)
    for peak in np.arange(0.4, 2.8, 0.6):
        ch2 += 450 * np.exp(-0.5 * ((t - peak) / 0.012) ** 2)
    return tuple(
        StreamSample(
            timestamp=index / sample_rate_hz,
            ch1=0,
            ch2=int(round(value)),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index, value in enumerate(ch2)
    )


def test_build_quality_text_includes_protocol_segment_gate_failures() -> None:
    protocol = TestProtocol(
        name="GUI protocol",
        steps=(
            ProtocolStep(0.0, 2.0, "baseline", "Sit still."),
            ProtocolStep(10.0, 2.0, "late", "No data."),
        ),
    )

    text = build_quality_text(
        samples=_samples(),
        status_values=tuple(),
        source="CH2",
        selected_source="CH2",
        valid_rr=3,
        protocol=protocol,
        gate=QualityGate(min_duration_seconds=1.0, min_r_peaks=3),
    )

    assert "Gate Pass" in text
    assert "Segment Gate Fail" in text
    assert "late: no data" in text


def test_build_quality_text_omits_segment_gate_without_protocol() -> None:
    text = build_quality_text(
        samples=_samples(),
        status_values=tuple(),
        source="CH2",
        selected_source="CH2",
        valid_rr=3,
        protocol=None,
    )

    assert "Segment Gate" not in text


def test_protocol_ready_for_live_quality_waits_until_all_steps_are_covered() -> None:
    protocol = TestProtocol(
        name="live protocol",
        steps=(
            ProtocolStep(0.0, 2.0, "baseline", "Sit still."),
            ProtocolStep(4.0, 2.0, "recovery", "Sit still."),
        ),
    )

    assert protocol_ready_for_live_quality(_samples(), protocol) is False
    assert protocol_ready_for_live_quality(_samples() * 3, protocol) is True
