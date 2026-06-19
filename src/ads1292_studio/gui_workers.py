from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings
from ads1292_studio.gui_specs import ADS1292R_ECG_SOURCE
from ads1292_studio.models import StreamSample
from ads1292_studio.quality import QualityMetrics, compute_quality_metrics
from ads1292_studio.review_render import ReviewRenderFrame, build_review_render_frame


DEFAULT_WORKER_SAMPLE_RATE_HZ = 500.0
DEFAULT_WORKER_MAX_POINTS = 10000
DEFAULT_WORKER_ECG_INVERTED = False
DEFAULT_WORKER_SMOOTHING_WINDOW = 11
DEFAULT_WORKER_MIN_ECG_SPAN_COUNTS = 8.0
DEFAULT_WORKER_MIN_RESP_SPAN_COUNTS = 40.0


@dataclass(frozen=True)
class LiveQualityResult:
    generation: int
    source: str
    valid_rr: int
    samples: tuple[StreamSample, ...]
    status_values: tuple[int, ...]
    metrics: QualityMetrics | None = None
    error: str | None = None


@dataclass(frozen=True)
class ReviewRenderResult:
    generation: int
    samples: tuple[StreamSample, ...]
    frame: ReviewRenderFrame | None = None
    error: str | None = None


def live_quality_worker_available(future: Future[LiveQualityResult] | None) -> bool:
    return future is None or future.done()


def compute_live_quality_result(
    *,
    generation: int,
    source: str,
    valid_rr: int,
    ch1_values: tuple[float, ...],
    ch2_values: tuple[float, ...],
    status_values: tuple[int, ...],
    sample_rate_hz: float = DEFAULT_WORKER_SAMPLE_RATE_HZ,
    ecg_source: str = ADS1292R_ECG_SOURCE,
) -> LiveQualityResult:
    try:
        samples = build_live_quality_samples(
            ch1_values,
            ch2_values,
            status_values,
            sample_rate_hz=sample_rate_hz,
        )
        metrics = compute_quality_metrics(samples, sample_rate_hz, ecg_source)
    except Exception as exc:  # pragma: no cover - defensive worker boundary
        return LiveQualityResult(generation, source, valid_rr, tuple(), status_values, error=str(exc))
    return LiveQualityResult(generation, source, valid_rr, samples, status_values, metrics=metrics)


def compute_review_render_result(
    *,
    generation: int,
    samples: tuple[StreamSample, ...],
    display_settings: EcgDisplaySettings,
    filter_settings: SoftwareFilterSettings,
    source: str = ADS1292R_ECG_SOURCE,
    sample_rate_hz: float = DEFAULT_WORKER_SAMPLE_RATE_HZ,
    smoothing_window: int = DEFAULT_WORKER_SMOOTHING_WINDOW,
    max_points: int = DEFAULT_WORKER_MAX_POINTS,
    ecg_inverted: bool = DEFAULT_WORKER_ECG_INVERTED,
    min_ecg_span_counts: float = DEFAULT_WORKER_MIN_ECG_SPAN_COUNTS,
    min_resp_span_counts: float = DEFAULT_WORKER_MIN_RESP_SPAN_COUNTS,
) -> ReviewRenderResult:
    try:
        frame = build_review_render_frame(
            samples,
            display_settings=display_settings,
            filter_settings=filter_settings,
            source=source,
            sample_rate_hz=sample_rate_hz,
            smoothing_window=smoothing_window,
            max_points=max_points,
            ecg_inverted=ecg_inverted,
            min_ecg_span_counts=min_ecg_span_counts,
            min_resp_span_counts=min_resp_span_counts,
        )
    except Exception as exc:  # pragma: no cover - defensive worker boundary
        return ReviewRenderResult(generation=generation, samples=samples, error=str(exc))
    return ReviewRenderResult(generation=generation, samples=samples, frame=frame)


def build_live_quality_samples(
    ch1_values: tuple[float, ...],
    ch2_values: tuple[float, ...],
    status_values: tuple[int, ...],
    *,
    sample_rate_hz: float = DEFAULT_WORKER_SAMPLE_RATE_HZ,
) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(
            timestamp=index / sample_rate_hz,
            ch1=int(ch1),
            ch2=int(ch2),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=int(status),
        )
        for index, (ch1, ch2, status) in enumerate(zip(ch1_values, ch2_values, status_values))
    )
