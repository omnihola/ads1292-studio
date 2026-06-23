from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from itertools import islice

import numpy as np

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings
from ads1292_studio.plots import decimate_extrema_for_plot, decimate_for_plot, smooth_for_plot
from ads1292_studio.quality import SignalNoiseEstimate, estimate_realtime_snr
from ads1292_studio.signal_processing import HeartRateSummary, apply_software_filters, detect_r_peaks, heart_rate_summary


MIN_PEAK_DETECTION_SECONDS = 1.0
MIN_PEAK_DETECTION_SPAN_COUNTS = 1e-9
# Contact is good enough for live peak detection when at least this fraction of
# the visible window is fully attached (status == 0). Matches the quality gate's
# min_contact_ok_percent default of 95%.
MIN_CONTACT_OK_FRACTION = 0.95


@dataclass(frozen=True)
class LiveRenderFrame:
    source: str
    left: float
    right: float
    visible_x: np.ndarray
    visible_ecg: np.ndarray
    visible_ecg_plot: np.ndarray
    visible_resp_plot: np.ndarray
    visible_status: np.ndarray
    peaks: tuple[int, ...]
    peaks_x: np.ndarray
    peaks_y: np.ndarray
    plot_ecg_x: np.ndarray
    plot_ecg: np.ndarray
    plot_resp_x: np.ndarray
    plot_resp: np.ndarray
    plot_status_x: np.ndarray
    plot_status: np.ndarray
    heart_rate: HeartRateSummary
    snr: SignalNoiseEstimate | None = None


def display_signal_values(
    values: np.ndarray,
    *,
    filter_enabled: bool,
    filter_settings: SoftwareFilterSettings | None = None,
    invert: bool = False,
    gain: float = 1.0,
    sample_rate_hz: float = 500.0,
) -> np.ndarray:
    settings = filter_settings or SoftwareFilterSettings(bandpass_enabled=filter_enabled)
    display = apply_software_filters(values, sample_rate_hz, settings)
    display = np.asarray(display, dtype=float)
    scale = -float(gain) if invert else float(gain)
    if scale == 1.0:
        return display
    return display * scale


def deque_tail_array(values: deque[float] | deque[int], count: int, *, dtype: object = float) -> np.ndarray:
    visible_count = max(0, min(len(values), int(count)))
    start = len(values) - visible_count
    return np.fromiter(islice(values, start, None), dtype=dtype, count=visible_count)


def build_live_render_frame(
    *,
    indices: deque[int],
    ch1: deque[float],
    ch2: deque[float],
    status: deque[int],
    display_settings: EcgDisplaySettings,
    filter_settings: SoftwareFilterSettings,
    source: str,
    sample_rate_hz: float,
    smoothing_window: int,
    max_render_points: int,
    ecg_inverted: bool,
) -> LiveRenderFrame | None:
    if not np.isfinite(sample_rate_hz) or sample_rate_hz <= 0:
        return None  # a bad/uninitialized rate would poison the x-axis with inf/nan
    visible_count = min(
        len(indices),
        len(ch1),
        len(ch2),
        len(status),
        int(display_settings.time_window_seconds * sample_rate_hz) + 2,
    )
    if visible_count <= 0:
        return None

    visible_x = deque_tail_array(indices, visible_count, dtype=float) / sample_rate_hz
    left = max(0.0, float(visible_x[-1]) - display_settings.time_window_seconds)
    right = max(display_settings.time_window_seconds, float(visible_x[-1]))
    ecg_raw = deque_tail_array(ch2, visible_count, dtype=float)
    resp_raw = deque_tail_array(ch1, visible_count, dtype=float)
    visible_ecg = display_signal_values(
        ecg_raw,
        filter_enabled=bool(filter_settings.bandpass_enabled),
        filter_settings=filter_settings,
        invert=ecg_inverted,
        gain=display_settings.gain,
        sample_rate_hz=sample_rate_hz,
    )
    visible_resp = display_signal_values(
        resp_raw,
        filter_enabled=bool(filter_settings.bandpass_enabled),
        filter_settings=filter_settings,
        sample_rate_hz=sample_rate_hz,
    )
    visible_ecg_plot = smooth_for_plot(visible_ecg, window=smoothing_window)
    visible_resp_plot = smooth_for_plot(visible_resp, window=smoothing_window)
    visible_status = deque_tail_array(status, visible_count, dtype=float)
    # Contact is OK only when most of the window is attached, not when a single
    # sample happens to read 0 (np.any would let one good sample mask total
    # lead-off and run R-peak detection on a disconnected trace).
    contact_ok = bool(visible_status.size and np.mean(visible_status == 0.0) >= MIN_CONTACT_OK_FRACTION)
    ecg_has_signal = bool(np.ptp(visible_ecg) > MIN_PEAK_DETECTION_SPAN_COUNTS)
    if contact_ok and ecg_has_signal and visible_count >= int(MIN_PEAK_DETECTION_SECONDS * sample_rate_hz):
        peaks = tuple(
            detect_r_peaks(
                visible_ecg,
                sample_rate_hz,
                prefiltered=bool(filter_settings.bandpass_enabled),
            )
        )
    else:
        peaks = ()
    peak_indices = list(peaks)
    peaks_x = visible_x[peak_indices] if peaks else np.array([], dtype=float)
    peaks_y = visible_ecg_plot[peak_indices] if peaks else np.array([], dtype=float)
    plot_ecg_x, plot_ecg = decimate_extrema_for_plot(visible_x, visible_ecg_plot, max_render_points)
    plot_resp_x, plot_resp = decimate_extrema_for_plot(visible_x, visible_resp_plot, max_render_points)
    plot_status_x, plot_status = decimate_for_plot(visible_x, visible_status, max_render_points)
    return LiveRenderFrame(
        source=source,
        left=left,
        right=right,
        visible_x=visible_x,
        visible_ecg=visible_ecg,
        visible_ecg_plot=visible_ecg_plot,
        visible_resp_plot=visible_resp_plot,
        visible_status=visible_status,
        peaks=peaks,
        peaks_x=peaks_x,
        peaks_y=peaks_y,
        plot_ecg_x=plot_ecg_x,
        plot_ecg=plot_ecg,
        plot_resp_x=plot_resp_x,
        plot_resp=plot_resp,
        plot_status_x=plot_status_x,
        plot_status=plot_status,
        heart_rate=heart_rate_summary(peaks, sample_rate_hz),
        snr=estimate_realtime_snr(visible_ecg, sample_rate_hz=sample_rate_hz),
    )
