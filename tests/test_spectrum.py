import numpy as np

from ads1292_studio.models import StreamSample


def _samples(sample_rate_hz: float = 500.0) -> tuple[StreamSample, ...]:
    t = np.arange(0, 4, 1 / sample_rate_hz)
    ch2 = 1000 * np.sin(2 * np.pi * 10.0 * t)
    return tuple(
        StreamSample(
            timestamp=float(index / sample_rate_hz),
            ch1=int(round(100 * np.sin(2 * np.pi * 0.5 * time))),
            ch2=int(round(value)),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index, (time, value) in enumerate(zip(t, ch2))
    )


def test_spectrum_analysis_detects_dominant_frequency_and_histogram_counts() -> None:
    from ads1292_studio.spectrum import build_spectrum_analysis

    analysis = build_spectrum_analysis(
        _samples(),
        source="CH2",
        sample_rate_hz=500.0,
        max_frequency_hz=50.0,
        histogram_bins=24,
    )

    peak_index = int(np.argmax(analysis.ecg_power))

    assert 9.5 <= float(analysis.ecg_frequency_hz[peak_index]) <= 10.5
    assert analysis.histogram_bin_edges.size == 25
    assert int(np.sum(analysis.histogram_counts)) == 2000
    assert analysis.ecg_label == "CH2"


def test_spectrum_analysis_handles_empty_samples() -> None:
    from ads1292_studio.spectrum import build_spectrum_analysis

    analysis = build_spectrum_analysis(tuple(), source="CH2", sample_rate_hz=500.0)

    assert analysis.ecg_frequency_hz.size == 0
    assert analysis.ecg_power.size == 0
    assert analysis.histogram_counts.size == 0
