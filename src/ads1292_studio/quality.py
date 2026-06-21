from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ads1292_studio.models import StreamSample
from ads1292_studio.signal_processing import review_channels


@dataclass(frozen=True)
class SignalNoiseEstimate:
    snr_db: float
    signal_rms_counts: float
    noise_rms_counts: float
    peak_to_peak_counts: float
    sample_count: int
    duration_seconds: float
    valid: bool


@dataclass(frozen=True)
class QualityMetrics:
    sample_count: int
    duration_seconds: float
    ecg_source: str
    contact_ok_percent: float
    lead_off_bad_samples: int
    r_peaks: int
    hr_median_bpm: float
    hr_min_bpm: float
    hr_max_bpm: float
    qrs_clear: bool
    p_tentative: bool
    t_tentative: bool
    score_ch1: float
    score_ch2: float
    baseline_drift_counts: float = 0.0
    noise_rms_counts: float = 0.0
    peak_to_peak_counts: float = 0.0

    @property
    def quality_label(self) -> str:
        if self.contact_ok_percent < 95 or not self.qrs_clear:
            return "Needs review"
        if self.r_peaks < 5 or self.hr_median_bpm <= 0:
            return "Insufficient ECG"
        if self.contact_ok_percent >= 99 and self.qrs_clear:
            return "Good ECG/QRS"
        return "Usable ECG/QRS"


def compute_quality_metrics(
    samples: tuple[StreamSample, ...] | list[StreamSample],
    sample_rate_hz: float = 500.0,
    source: str = "Auto",
) -> QualityMetrics:
    if not samples:
        return QualityMetrics(0, 0.0, "CH1", 0.0, 0, 0, 0.0, 0.0, 0.0, False, False, False, 0.0, 0.0)
    ch1 = np.array([sample.ch1 for sample in samples], dtype=float)
    ch2 = np.array([sample.ch2 for sample in samples], dtype=float)
    result = review_channels(ch1, ch2, sample_rate_hz=sample_rate_hz, source=source)
    ecg = ch2 if result.source.channel == "CH2" else ch1
    lead_bad = sum(1 for sample in samples if sample.lead_off_bits != 0)
    duration = (len(samples) - 1) / sample_rate_hz if len(samples) > 1 else 0.0
    baseline_drift = _baseline_drift(ecg, sample_rate_hz)
    noise_rms = _noise_rms(ecg)
    peak_to_peak = float(np.max(ecg) - np.min(ecg)) if ecg.size else 0.0
    return QualityMetrics(
        sample_count=len(samples),
        duration_seconds=float(duration),
        ecg_source=result.source.channel,
        contact_ok_percent=float(100.0 * (len(samples) - lead_bad) / len(samples)),
        lead_off_bad_samples=lead_bad,
        r_peaks=len(result.peaks),
        hr_median_bpm=result.heart_rate.median_bpm,
        hr_min_bpm=result.heart_rate.min_bpm,
        hr_max_bpm=result.heart_rate.max_bpm,
        qrs_clear=result.pqrst.qrs_clear,
        p_tentative=result.pqrst.p_tentative,
        t_tentative=result.pqrst.t_tentative,
        score_ch1=result.source.score_ch1,
        score_ch2=result.source.score_ch2,
        baseline_drift_counts=baseline_drift,
        noise_rms_counts=noise_rms,
        peak_to_peak_counts=peak_to_peak,
    )


def estimate_realtime_snr(values: np.ndarray, *, sample_rate_hz: float = 500.0) -> SignalNoiseEstimate:
    finite_values = np.asarray(values, dtype=float)
    finite_values = finite_values[np.isfinite(finite_values)]
    if finite_values.size < 3:
        return SignalNoiseEstimate(0.0, 0.0, 0.0, 0.0, int(finite_values.size), 0.0, False)

    centered = finite_values - float(np.median(finite_values))
    signal_rms = float(np.sqrt(np.mean(centered * centered)))
    # First-difference RMS is sqrt(2) larger than sample noise for white noise.
    noise_rms = float(_noise_rms(finite_values) / np.sqrt(2.0))
    peak_to_peak = float(np.percentile(finite_values, 95.0) - np.percentile(finite_values, 5.0))
    duration = (finite_values.size - 1) / sample_rate_hz if sample_rate_hz > 0 else 0.0
    if signal_rms <= 1e-12:
        return SignalNoiseEstimate(0.0, signal_rms, noise_rms, peak_to_peak, int(finite_values.size), float(duration), False)
    if noise_rms <= 1e-12:
        return SignalNoiseEstimate(80.0, signal_rms, noise_rms, peak_to_peak, int(finite_values.size), float(duration), True)
    snr_db = float(20.0 * np.log10(signal_rms / noise_rms))
    return SignalNoiseEstimate(snr_db, signal_rms, noise_rms, peak_to_peak, int(finite_values.size), float(duration), True)


def _baseline_drift(values: np.ndarray, sample_rate_hz: float) -> float:
    if values.size < 2:
        return 0.0
    window = max(1, min(int(sample_rate_hz), values.size // 2))
    start = float(np.median(values[:window]))
    end = float(np.median(values[-window:]))
    return abs(end - start)


def _noise_rms(values: np.ndarray) -> float:
    if values.size < 3:
        return 0.0
    diff = np.diff(values.astype(float))
    centered = diff - float(np.median(diff))
    return float(np.sqrt(np.mean(centered * centered)))
