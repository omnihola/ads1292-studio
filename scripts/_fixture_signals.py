from __future__ import annotations

import numpy as np


def synthetic_ecg(n: int, sample_rate_hz: float, *, bpm: float = 72.0, seed: int = 1292) -> list[float]:
    """Deterministic synthetic ECG: periodic QRS-like Gaussians + small seeded noise.

    Generated ONCE at fixture-build time and stored verbatim in the fixture.
    The C++ side consumes the stored array; it never calls this function.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n) / sample_rate_hz
    rr = 60.0 / bpm
    signal = np.zeros(n, dtype=float)
    beat_times = np.arange(0.4, t[-1] if n else 0.0, rr)
    for bt in beat_times:
        signal += 600.0 * np.exp(-((t - bt) ** 2) / (2 * 0.012 ** 2))   # R
        signal += -80.0 * np.exp(-((t - (bt - 0.03)) ** 2) / (2 * 0.010 ** 2))  # Q
        signal += -120.0 * np.exp(-((t - (bt + 0.03)) ** 2) / (2 * 0.012 ** 2))  # S
        signal += 90.0 * np.exp(-((t - (bt + 0.20)) ** 2) / (2 * 0.040 ** 2))   # T
    signal += rng.normal(0.0, 6.0, size=n)
    return [float(v) for v in signal]
