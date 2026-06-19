from __future__ import annotations

import numpy as np


def decimate_for_plot(x, y, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    x_arr = np.asarray(x)
    y_arr = np.asarray(y)
    if y_arr.size <= max_points:
        return x_arr, y_arr
    step = int(np.ceil(y_arr.size / max_points))
    return x_arr[::step], y_arr[::step]


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
