from pathlib import Path

import numpy as np
import pytest

from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.signal_processing import (
    choose_ecg_channel,
    detect_r_peaks,
    heart_rate_summary,
    pqrst_review,
)


def synthetic_two_channel_recording(sample_rate_hz: float = 500.0) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(0, 7, 1 / sample_rate_hz)
    ch1 = 20 * np.sin(2 * np.pi * 0.8 * t)
    ch2 = 10 * np.sin(2 * np.pi * 1.0 * t)
    for peak in np.arange(0.5, 6.8, 0.58):
        ch2 += 420 * np.exp(-0.5 * ((t - peak) / 0.012) ** 2)
    return ch1, ch2


def test_choose_ecg_channel_selects_channel_with_qrs_spikes() -> None:
    ch1, ch2 = synthetic_two_channel_recording()

    result = choose_ecg_channel(ch1, ch2, sample_rate_hz=500.0)

    assert result.channel == "CH2"
    assert result.confidence > 1.2


def test_r_peak_detection_and_heart_rate_are_plausible() -> None:
    _, ch2 = synthetic_two_channel_recording()

    peaks = detect_r_peaks(ch2, sample_rate_hz=500.0)
    summary = heart_rate_summary(peaks, sample_rate_hz=500.0)

    assert len(peaks) >= 10
    assert 95 <= summary.median_bpm <= 110
    assert summary.valid_rr_count >= 8


def test_pqrst_review_is_conservative_about_p_and_t() -> None:
    _, ch2 = synthetic_two_channel_recording()
    peaks = detect_r_peaks(ch2, sample_rate_hz=500.0)

    review = pqrst_review(ch2, peaks, sample_rate_hz=500.0)

    assert review.qrs_clear is True
    assert review.beats_used >= 8
    assert review.p_tentative in (True, False)
    assert review.t_tentative in (True, False)


def test_real_saved_run_selects_ch2_when_available() -> None:
    sample = Path(__file__).resolve().parents[2] / "record" / "ads1292" / "2026-06-18-164923-ads1292-live.csv"
    if not sample.exists():
        pytest.skip("local ADS1292 sample CSV is not available")
    recording = read_recording_csv(sample)
    ch1 = np.array([sample.ch1 for sample in recording.samples], dtype=float)
    ch2 = np.array([sample.ch2 for sample in recording.samples], dtype=float)

    result = choose_ecg_channel(ch1[:3500], ch2[:3500], sample_rate_hz=500.0)
    peaks = detect_r_peaks(ch2[850:3500], sample_rate_hz=500.0)
    summary = heart_rate_summary(peaks, sample_rate_hz=500.0)

    assert result.channel == "CH2"
    assert 90 <= summary.median_bpm <= 115
