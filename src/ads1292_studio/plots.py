from __future__ import annotations

import numpy as np


def robust_ylim(values) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return -1.0, 1.0
    if arr.size > 50:
        lo, hi = np.percentile(arr, [1, 99])
    else:
        lo, hi = float(np.min(arr)), float(np.max(arr))
    if lo == hi:
        lo -= 1
        hi += 1
    pad = max(1.0, 0.15 * (hi - lo))
    return float(lo - pad), float(hi + pad)
