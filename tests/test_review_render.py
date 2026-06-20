import numpy as np

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings
from ads1292_studio.models import PqrstReview, StreamSample
from ads1292_studio.review_render import build_review_render_frame


def _samples(count: int = 1200) -> tuple[StreamSample, ...]:
    rows: list[StreamSample] = []
    for index in range(count):
        spike = 1200 if index % 250 == 0 else 0
        rows.append(
            StreamSample(
                timestamp=index / 500.0,
                ch1=int(200 * np.sin(index / 35.0)),
                ch2=spike + int(35 * np.sin(index / 18.0)),
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0 if index < count - 10 else 1,
            )
        )
    return tuple(rows)


def test_build_review_render_frame_precomputes_plot_quality_and_pqrst() -> None:
    samples = _samples()

    frame = build_review_render_frame(
        samples,
        display_settings=EcgDisplaySettings(time_window_seconds=8, gain=2.0, sweep_speed_mm_s=25),
        filter_settings=SoftwareFilterSettings(),
        source="CH2",
        sample_rate_hz=500.0,
        smoothing_window=11,
        max_points=300,
        ecg_inverted=False,
        min_ecg_span_counts=8.0,
        min_resp_span_counts=40.0,
    )

    assert frame.sample_count == len(samples)
    assert frame.duration_seconds == len(samples) / 500.0
    assert frame.source == "CH2"
    assert frame.mode == "raw | 2x | 8s | 25 mm/s, display-smoothed"
    assert frame.status_values[-10:] == (1,) * 10
    assert frame.metrics.sample_count == len(samples)
    assert frame.metrics.ecg_source == "CH2"
    assert len(frame.review.peaks) >= 3
    assert frame.pqrst.beats_used >= 1
    assert len(frame.plot_ecg_x) <= 300
    assert len(frame.plot_resp_x) <= 300
    assert len(frame.plot_status_x) <= 300
    assert frame.ecg_ylim[0] < frame.ecg_ylim[1]
    assert frame.resp_ylim[0] < frame.resp_ylim[1]
    assert frame.status_ylim == (-0.5, 1.5)


def test_review_pqrst_uses_raw_ecg_channel_not_display_filtered_values(monkeypatch) -> None:
    import ads1292_studio.review_render as review_render

    samples = _samples()
    captured: dict[str, np.ndarray] = {}

    def capture_pqrst(values, peaks, sample_rate_hz: float = 500.0):
        captured["values"] = np.asarray(values, dtype=float)
        return PqrstReview(False, False, False, 0, tuple(), tuple())

    monkeypatch.setattr(review_render, "pqrst_review", capture_pqrst)

    build_review_render_frame(
        samples,
        display_settings=EcgDisplaySettings(time_window_seconds=8, gain=5.0, sweep_speed_mm_s=25),
        filter_settings=SoftwareFilterSettings(bandpass_enabled=True),
        source="CH2",
        sample_rate_hz=500.0,
        smoothing_window=11,
        max_points=300,
        ecg_inverted=True,
        min_ecg_span_counts=8.0,
        min_resp_span_counts=40.0,
    )

    np.testing.assert_allclose(captured["values"], np.asarray([sample.ch2 for sample in samples], dtype=float))
