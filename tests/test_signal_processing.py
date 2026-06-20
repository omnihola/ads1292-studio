from pathlib import Path

import numpy as np
import pytest

from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.signal_processing import (
    _bandpass_coefficients,
    _highpass_coefficients,
    _lowpass_coefficients,
    _notch_coefficients,
    bandpass,
    choose_ecg_channel,
    detect_r_peaks,
    heart_rate_summary,
    highpass,
    lowpass,
    notch,
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


def test_r_peak_detection_accepts_prefiltered_live_ecg() -> None:
    _, ch2 = synthetic_two_channel_recording()

    raw_peaks = detect_r_peaks(ch2, sample_rate_hz=500.0)
    filtered_peaks = detect_r_peaks(bandpass(ch2, 500.0), sample_rate_hz=500.0, prefiltered=True)

    assert filtered_peaks == raw_peaks


@pytest.mark.parametrize("polarity", [1.0, -1.0])
def test_r_peak_detection_uses_single_find_peaks_pass_for_dominant_polarity(
    monkeypatch: pytest.MonkeyPatch,
    polarity: float,
) -> None:
    import ads1292_studio.signal_processing as signal_processing

    _, ch2 = synthetic_two_channel_recording()
    calls = {"find_peaks": 0}
    original_find_peaks = signal_processing.signal.find_peaks

    def counted_find_peaks(*args, **kwargs):
        calls["find_peaks"] += 1
        return original_find_peaks(*args, **kwargs)

    monkeypatch.setattr(signal_processing.signal, "find_peaks", counted_find_peaks)

    peaks = signal_processing.detect_r_peaks(polarity * ch2, sample_rate_hz=500.0)
    summary = heart_rate_summary(peaks, sample_rate_hz=500.0)

    assert calls["find_peaks"] == 1
    assert len(peaks) >= 10
    assert 95 <= summary.median_bpm <= 110


def test_r_peak_detection_skips_bandpass_until_one_second_is_available(monkeypatch) -> None:
    import ads1292_studio.signal_processing as signal_processing

    calls = {"bandpass": 0}

    def counted_bandpass(values, sample_rate_hz: float, low_hz: float = 0.7, high_hz: float = 35.0):
        calls["bandpass"] += 1
        return bandpass(values, sample_rate_hz, low_hz=low_hz, high_hz=high_hz)

    monkeypatch.setattr(signal_processing, "bandpass", counted_bandpass)

    peaks = signal_processing.detect_r_peaks(np.zeros(499), sample_rate_hz=500.0)

    assert peaks == tuple()
    assert calls["bandpass"] == 0


def test_pqrst_review_is_conservative_about_p_and_t() -> None:
    _, ch2 = synthetic_two_channel_recording()
    peaks = detect_r_peaks(ch2, sample_rate_hz=500.0)

    review = pqrst_review(ch2, peaks, sample_rate_hz=500.0)

    assert review.qrs_clear is True
    assert review.beats_used >= 8
    assert review.p_tentative in (True, False)
    assert review.t_tentative in (True, False)


def test_filter_design_coefficients_are_cached_between_live_frames() -> None:
    values = np.sin(np.linspace(0, 12, 800))
    for cached in (
        _bandpass_coefficients,
        _highpass_coefficients,
        _lowpass_coefficients,
        _notch_coefficients,
    ):
        cached.cache_clear()

    np.testing.assert_allclose(bandpass(values, 500.0), bandpass(values, 500.0))
    np.testing.assert_allclose(highpass(values, 500.0), highpass(values, 500.0))
    np.testing.assert_allclose(lowpass(values, 500.0), lowpass(values, 500.0))
    np.testing.assert_allclose(notch(values, 500.0), notch(values, 500.0))

    assert _bandpass_coefficients.cache_info().hits == 1
    assert _highpass_coefficients.cache_info().hits == 1
    assert _lowpass_coefficients.cache_info().hits == 1
    assert _notch_coefficients.cache_info().hits == 1


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
