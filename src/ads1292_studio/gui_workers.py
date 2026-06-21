from __future__ import annotations

from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path
import queue
from typing import Protocol, TypeVar

from ads1292_studio.calibration import LiveStreamCalibration
from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings
from ads1292_studio.gui_specs import ADS1292R_ECG_SOURCE
from ads1292_studio.models import Recording, StreamSample
from ads1292_studio.quality import QualityMetrics, compute_quality_metrics
from ads1292_studio.review_render import ReviewRenderFrame, build_review_render_frame


DEFAULT_WORKER_SAMPLE_RATE_HZ = 500.0
DEFAULT_WORKER_MAX_POINTS = 10000
DEFAULT_WORKER_ECG_INVERTED = False
DEFAULT_WORKER_SMOOTHING_WINDOW = 11
DEFAULT_WORKER_MIN_ECG_SPAN_COUNTS = 8.0
DEFAULT_WORKER_MIN_RESP_SPAN_COUNTS = 40.0


class GeneratedResult(Protocol):
    generation: int


GeneratedResultT = TypeVar("GeneratedResultT", bound=GeneratedResult)


@dataclass(frozen=True)
class CsvLoadResult:
    path: Path
    recording: Recording | None = None
    review_frame: ReviewRenderFrame | None = None
    display_settings: EcgDisplaySettings | None = None
    filter_settings: SoftwareFilterSettings | None = None
    error: str | None = None


@dataclass(frozen=True)
class ConnectResult:
    port: str
    detail: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class LiveCalibrationResult:
    port: str
    calibration: LiveStreamCalibration | None = None
    error: str | None = None


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


@dataclass(frozen=True)
class ReviewRenderUpdatePlan:
    generation: int
    pending_samples: tuple[StreamSample, ...] | None
    should_submit: bool


@dataclass(frozen=True)
class LiveQualityUpdatePlan:
    generation: int
    should_submit: bool


def live_quality_worker_available(future: Future[LiveQualityResult] | None) -> bool:
    return future is None or future.done()


def live_quality_sample_count_ready(sample_count: int, sample_rate_hz: float) -> bool:
    return sample_rate_hz > 0 and int(sample_count) >= int(sample_rate_hz)


def live_quality_update_plan(
    *,
    future: Future[LiveQualityResult] | None,
    generation: int,
    sample_count: int,
    sample_rate_hz: float,
) -> LiveQualityUpdatePlan:
    if not live_quality_worker_available(future):
        return LiveQualityUpdatePlan(generation=int(generation), should_submit=False)
    if not live_quality_sample_count_ready(sample_count, sample_rate_hz):
        return LiveQualityUpdatePlan(generation=int(generation), should_submit=False)
    return LiveQualityUpdatePlan(generation=int(generation) + 1, should_submit=True)


def review_render_update_plan(
    *,
    future: Future[ReviewRenderResult] | None,
    generation: int,
    samples: tuple[StreamSample, ...],
) -> ReviewRenderUpdatePlan:
    next_generation = int(generation) + 1
    if future is not None and not future.done():
        return ReviewRenderUpdatePlan(
            generation=next_generation,
            pending_samples=samples,
            should_submit=False,
        )
    return ReviewRenderUpdatePlan(
        generation=next_generation,
        pending_samples=None,
        should_submit=True,
    )


def review_render_pending_ready(
    *,
    future: Future[ReviewRenderResult] | None,
    pending_samples: tuple[StreamSample, ...] | None,
) -> tuple[StreamSample, ...] | None:
    if pending_samples is None:
        return None
    if future is not None and not future.done():
        return None
    return pending_samples


def drain_latest_generation_result(
    results: queue.Queue[GeneratedResultT],
    *,
    generation: int,
) -> GeneratedResultT | None:
    latest: GeneratedResultT | None = None
    while True:
        try:
            result = results.get_nowait()
        except queue.Empty:
            break
        if result.generation == generation:
            latest = result
    return latest


def drain_latest_live_quality_result(
    results: queue.Queue[LiveQualityResult],
    *,
    generation: int,
) -> LiveQualityResult | None:
    return drain_latest_generation_result(results, generation=generation)


def drain_latest_review_render_result(
    results: queue.Queue[ReviewRenderResult],
    *,
    generation: int,
) -> ReviewRenderResult | None:
    return drain_latest_generation_result(results, generation=generation)


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
    derived_valid_rr = max(0, metrics.r_peaks - 1)
    return LiveQualityResult(
        generation,
        source,
        max(int(valid_rr), derived_valid_rr),
        samples,
        status_values,
        metrics=metrics,
    )


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
