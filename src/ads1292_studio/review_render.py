from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings, display_mode_label
from ads1292_studio.live_render import display_signal_values
from ads1292_studio.models import PqrstReview, ReviewResult, StreamSample
from ads1292_studio.plots import decimate_extrema_for_plot, decimate_for_plot, robust_ylim, smooth_for_plot
from ads1292_studio.quality import QualityMetrics, compute_quality_metrics
from ads1292_studio.signal_processing import pqrst_review, review_channels


@dataclass(frozen=True)
class ReviewRenderFrame:
    source: str
    mode: str
    sample_count: int
    duration_seconds: float
    status_values: tuple[int, ...]
    plot_ecg_x: np.ndarray
    plot_ecg: np.ndarray
    plot_resp_x: np.ndarray
    plot_resp: np.ndarray
    plot_status_x: np.ndarray
    plot_status: np.ndarray
    peak_x: np.ndarray
    peak_y: np.ndarray
    x_right: float
    ecg_ylim: tuple[float, float]
    resp_ylim: tuple[float, float]
    status_ylim: tuple[float, float]
    review: ReviewResult
    pqrst: PqrstReview
    metrics: QualityMetrics


def build_review_render_frame(
    samples: tuple[StreamSample, ...],
    *,
    display_settings: EcgDisplaySettings,
    filter_settings: SoftwareFilterSettings,
    source: str,
    sample_rate_hz: float,
    smoothing_window: int,
    max_points: int,
    ecg_inverted: bool,
    min_ecg_span_counts: float,
    min_resp_span_counts: float,
) -> ReviewRenderFrame:
    full_ch1 = np.asarray([sample.ch1 for sample in samples], dtype=float)
    full_ch2 = np.asarray([sample.ch2 for sample in samples], dtype=float)
    status_values = tuple(sample.lead_off_bits for sample in samples)
    status_arr = np.asarray(status_values, dtype=float)
    ecg = display_signal_values(
        full_ch2,
        filter_enabled=bool(filter_settings.bandpass_enabled),
        filter_settings=filter_settings,
        invert=ecg_inverted,
        gain=display_settings.gain,
        sample_rate_hz=sample_rate_hz,
    )
    resp = display_signal_values(
        full_ch1,
        filter_enabled=bool(filter_settings.bandpass_enabled),
        filter_settings=filter_settings,
        sample_rate_hz=sample_rate_hz,
    )
    review = review_channels(full_ch1, full_ch2, sample_rate_hz, source)
    metrics = compute_quality_metrics(samples, sample_rate_hz, source)
    pqrst = pqrst_review(ecg, review.peaks, sample_rate_hz)
    x = np.arange(ecg.size) / sample_rate_hz
    display_ecg = smooth_for_plot(ecg, window=smoothing_window)
    display_resp = smooth_for_plot(resp, window=smoothing_window)
    plot_ecg_x, plot_ecg = decimate_extrema_for_plot(x, display_ecg, max_points)
    plot_resp_x, plot_resp = decimate_extrema_for_plot(x, display_resp, max_points)
    plot_status_x, plot_status = decimate_for_plot(x, status_arr, max_points)
    peak_indices = list(review.peaks)
    peak_x = np.asarray(review.peaks, dtype=float) / sample_rate_hz if review.peaks else np.array([], dtype=float)
    peak_y = ecg[peak_indices] if review.peaks else np.array([], dtype=float)
    x_right = max(1.0, float(x[-1]) if x.size else 1.0)
    status_top = max(1.0, float(status_arr.max()) + 0.5 if status_arr.size else 1.0)
    return ReviewRenderFrame(
        source=source,
        mode=f"{display_mode_label(display_settings, filter_settings)}, display-smoothed",
        sample_count=len(samples),
        duration_seconds=len(samples) / sample_rate_hz,
        status_values=status_values,
        plot_ecg_x=plot_ecg_x,
        plot_ecg=plot_ecg,
        plot_resp_x=plot_resp_x,
        plot_resp=plot_resp,
        plot_status_x=plot_status_x,
        plot_status=plot_status,
        peak_x=peak_x,
        peak_y=peak_y,
        x_right=x_right,
        ecg_ylim=robust_ylim(display_ecg, min_span=min_ecg_span_counts * display_settings.gain),
        resp_ylim=robust_ylim(display_resp, min_span=min_resp_span_counts),
        status_ylim=(-0.5, status_top),
        review=review,
        pqrst=pqrst,
        metrics=metrics,
    )
