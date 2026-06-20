from __future__ import annotations

from functools import lru_cache

import numpy as np
from scipy import signal

from ads1292_studio.display import SoftwareFilterSettings
from ads1292_studio.models import ChannelChoice, HeartRateSummary, PqrstReview, ReviewResult


def as_float_array(values) -> np.ndarray:
    return np.asarray(values, dtype=float)


def bandpass(values, sample_rate_hz: float, low_hz: float = 0.7, high_hz: float = 35.0) -> np.ndarray:
    arr = as_float_array(values)
    if arr.size < 16:
        return arr - np.median(arr) if arr.size else arr
    b, a = _bandpass_coefficients(float(sample_rate_hz), float(low_hz), float(high_hz))
    return signal.filtfilt(b, a, arr)


def highpass(values, sample_rate_hz: float, cutoff_hz: float = 0.5) -> np.ndarray:
    arr = as_float_array(values)
    if arr.size < 16:
        return arr - np.median(arr) if arr.size else arr
    b, a = _highpass_coefficients(float(sample_rate_hz), float(cutoff_hz))
    return signal.filtfilt(b, a, arr)


def lowpass(values, sample_rate_hz: float, cutoff_hz: float = 40.0) -> np.ndarray:
    arr = as_float_array(values)
    if arr.size < 16:
        return arr
    b, a = _lowpass_coefficients(float(sample_rate_hz), float(cutoff_hz))
    return signal.filtfilt(b, a, arr)


def notch(values, sample_rate_hz: float, notch_hz: float = 60.0, q: float = 30.0) -> np.ndarray:
    arr = as_float_array(values)
    if arr.size < 16:
        return arr
    b, a = _notch_coefficients(float(sample_rate_hz), float(notch_hz), float(q))
    return signal.filtfilt(b, a, arr)


@lru_cache(maxsize=32)
def _bandpass_coefficients(
    sample_rate_hz: float,
    low_hz: float,
    high_hz: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    nyquist = sample_rate_hz / 2
    high = min(high_hz / nyquist, 0.99)
    low = max(low_hz / nyquist, 0.0001)
    b, a = signal.butter(2, [low, high], btype="band")
    return tuple(float(value) for value in b), tuple(float(value) for value in a)


@lru_cache(maxsize=32)
def _highpass_coefficients(
    sample_rate_hz: float,
    cutoff_hz: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    cutoff = max(cutoff_hz / (sample_rate_hz / 2), 0.0001)
    b, a = signal.butter(2, cutoff, btype="highpass")
    return tuple(float(value) for value in b), tuple(float(value) for value in a)


@lru_cache(maxsize=32)
def _lowpass_coefficients(
    sample_rate_hz: float,
    cutoff_hz: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    cutoff = min(cutoff_hz / (sample_rate_hz / 2), 0.99)
    b, a = signal.butter(2, cutoff, btype="lowpass")
    return tuple(float(value) for value in b), tuple(float(value) for value in a)


@lru_cache(maxsize=32)
def _notch_coefficients(
    sample_rate_hz: float,
    notch_hz: float,
    q: float,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    normalized = min(notch_hz / (sample_rate_hz / 2), 0.99)
    b, a = signal.iirnotch(normalized, q)
    return tuple(float(value) for value in b), tuple(float(value) for value in a)


def apply_software_filters(
    values,
    sample_rate_hz: float,
    settings: SoftwareFilterSettings,
) -> np.ndarray:
    display = as_float_array(values)
    if settings.bandpass_enabled:
        return bandpass(display, sample_rate_hz)
    if settings.highpass_enabled:
        display = highpass(display, sample_rate_hz, settings.highpass_hz)
    if settings.notch_enabled:
        display = notch(display, sample_rate_hz, settings.notch_hz)
    if settings.lowpass_enabled:
        display = lowpass(display, sample_rate_hz, settings.lowpass_hz)
    return display


def detrend_median(values, window: int = 500) -> np.ndarray:
    arr = as_float_array(values)
    if arr.size == 0:
        return arr
    baseline = np.median(arr[-min(window, arr.size) :])
    return arr - baseline


def qrs_like_score(values, sample_rate_hz: float = 500.0) -> float:
    filtered = bandpass(values, sample_rate_hz)
    if filtered.size < 100:
        return 0.0
    diff = np.diff(filtered - np.median(filtered))
    mad = np.median(np.abs(diff - np.median(diff))) + 1e-9
    return float(np.percentile(np.abs(diff), 99) / mad)


def choose_ecg_channel(
    ch1,
    ch2,
    sample_rate_hz: float = 500.0,
    override: str = "Auto",
) -> ChannelChoice:
    override = override.upper()
    score_ch1 = qrs_like_score(ch1, sample_rate_hz)
    score_ch2 = qrs_like_score(ch2, sample_rate_hz)
    select_ch1 = _channel_selection_score(ch1, sample_rate_hz)
    select_ch2 = _channel_selection_score(ch2, sample_rate_hz)
    denominator = max(min(select_ch1, select_ch2), 1e-9)
    confidence = max(select_ch1, select_ch2) / denominator
    if override in {"CH1", "CH2"}:
        return ChannelChoice(override, score_ch1, score_ch2, confidence)
    channel = "CH2" if select_ch2 > select_ch1 * 1.05 else "CH1"
    return ChannelChoice(channel, score_ch1, score_ch2, confidence)


def _channel_selection_score(values, sample_rate_hz: float) -> float:
    peaks = detect_r_peaks(values, sample_rate_hz)
    summary = heart_rate_summary(peaks, sample_rate_hz)
    regularity = max(1, summary.valid_rr_count)
    return qrs_like_score(values, sample_rate_hz) * regularity


def detect_r_peaks(values, sample_rate_hz: float = 500.0, *, prefiltered: bool = False) -> tuple[int, ...]:
    arr = as_float_array(values)
    if arr.size < int(sample_rate_hz):
        return tuple()
    filtered = arr if prefiltered else bandpass(arr, sample_rate_hz)
    centered = filtered - np.median(filtered)
    scale = np.std(centered)
    prominence = max(20.0, scale * 0.45)
    positive_excursion = float(np.max(centered))
    negative_excursion = abs(float(np.min(centered)))
    peak_signal = centered if positive_excursion >= negative_excursion else -centered
    peaks, _props = signal.find_peaks(
        peak_signal,
        distance=int(0.35 * sample_rate_hz),
        prominence=prominence,
    )
    return tuple(int(peak) for peak in peaks)


def heart_rate_summary(peaks, sample_rate_hz: float = 500.0) -> HeartRateSummary:
    peak_arr = np.asarray(peaks, dtype=float)
    if peak_arr.size < 2:
        return HeartRateSummary(0.0, 0.0, 0.0, 0)
    rr_seconds = np.diff(peak_arr) / sample_rate_hz
    bpm = 60.0 / rr_seconds
    valid = bpm[(bpm >= 40) & (bpm <= 180)]
    if valid.size == 0:
        return HeartRateSummary(0.0, 0.0, 0.0, 0)
    return HeartRateSummary(
        median_bpm=float(np.median(valid)),
        min_bpm=float(np.min(valid)),
        max_bpm=float(np.max(valid)),
        valid_rr_count=int(valid.size),
    )


def pqrst_review(values, peaks, sample_rate_hz: float = 500.0) -> PqrstReview:
    filtered = bandpass(values, sample_rate_hz, low_hz=0.15, high_hz=40.0)
    pre = int(0.25 * sample_rate_hz)
    post = int(0.55 * sample_rate_hz)
    beats: list[np.ndarray] = []
    for peak in peaks:
        if peak - pre < 0 or peak + post > filtered.size:
            continue
        beat = filtered[peak - pre : peak + post].copy()
        beat -= np.median(beat[: max(1, int(0.12 * sample_rate_hz))])
        beats.append(beat)
    if not beats:
        return PqrstReview(False, False, False, 0, tuple(), tuple())
    beat_arr = np.vstack(beats)
    avg = np.mean(beat_arr, axis=0)
    r_amp = abs(float(avg[pre]))
    noise = float(np.median(np.abs(avg[: pre // 2] - np.median(avg[: pre // 2])))) + 1e-9
    p_start = pre - int(0.22 * sample_rate_hz)
    p_end = pre - int(0.08 * sample_rate_hz)
    t_start = pre + int(0.12 * sample_rate_hz)
    t_end = pre + int(0.38 * sample_rate_hz)
    p_range = float(np.ptp(avg[p_start:p_end])) if p_end > p_start else 0.0
    t_range = float(np.ptp(avg[t_start:t_end])) if t_end > t_start else 0.0
    time_ms = ((np.arange(pre + post) - pre) / sample_rate_hz) * 1000
    return PqrstReview(
        qrs_clear=bool(r_amp > max(40.0, noise * 8)),
        p_tentative=bool(p_range > max(15.0, noise * 3)),
        t_tentative=bool(t_range > max(25.0, noise * 4)),
        beats_used=len(beats),
        average_beat=tuple(float(v) for v in avg),
        time_ms=tuple(float(v) for v in time_ms),
    )


def review_channels(ch1, ch2, sample_rate_hz: float = 500.0, source: str = "Auto") -> ReviewResult:
    choice = choose_ecg_channel(ch1, ch2, sample_rate_hz=sample_rate_hz, override=source)
    selected = ch2 if choice.channel == "CH2" else ch1
    peaks = detect_r_peaks(selected, sample_rate_hz=sample_rate_hz)
    heart_rate = heart_rate_summary(peaks, sample_rate_hz=sample_rate_hz)
    pqrst = pqrst_review(selected, peaks, sample_rate_hz=sample_rate_hz)
    return ReviewResult(choice, peaks, heart_rate, pqrst)
