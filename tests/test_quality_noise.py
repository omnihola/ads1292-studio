"""Noise metric must reflect real noise, not the QRS slope (robust estimator)."""
from __future__ import annotations

import numpy as np

from ads1292_studio.models import StreamSample
from ads1292_studio.quality import compute_quality_metrics, estimate_realtime_snr


def _ecg(noise_sigma: float, *, motion: bool = False, seed: int = 0):
    fs = 500.0
    t = np.arange(0, 10, 1 / fs)
    x = np.zeros_like(t)
    for k in np.arange(0.4, 8.8, 0.6):
        x += 460 * np.exp(-0.5 * ((t - k) / 0.011) ** 2)  # tall QRS
    if motion:
        x += 180 * np.sin(2 * np.pi * 12 * t)  # 12 Hz in-band motion artifact
    x += np.random.RandomState(seed).normal(0, noise_sigma, len(t))
    return tuple(
        StreamSample(timestamp=i / fs, ch1=0, ch2=int(round(v)),
                     board_heart_rate=0, board_respiration_rate=0, status_byte=0)
        for i, v in enumerate(x)
    )


def test_noise_not_inflated_by_qrs_slope():
    # a clean, high-amplitude ECG (true noise ~5) must NOT report a huge noise
    m = compute_quality_metrics(_ecg(5.0), sample_rate_hz=500.0)
    assert m.noise_rms_counts < 20.0, f"QRS slope inflated noise: {m.noise_rms_counts}"


def test_noise_still_detects_in_band_motion_artifact():
    clean = compute_quality_metrics(_ecg(5.0, seed=1), sample_rate_hz=500.0)
    motion = compute_quality_metrics(_ecg(5.0, motion=True, seed=1), sample_rate_hz=500.0)
    assert motion.noise_rms_counts > clean.noise_rms_counts * 1.5


def test_realtime_snr_higher_for_cleaner_signal():
    import numpy as np
    quiet = np.array([s.ch2 for s in _ecg(3.0, seed=2)], dtype=float)
    noisy = np.array([s.ch2 for s in _ecg(40.0, seed=2)], dtype=float)
    assert estimate_realtime_snr(quiet, sample_rate_hz=500.0).snr_db > \
        estimate_realtime_snr(noisy, sample_rate_hz=500.0).snr_db
