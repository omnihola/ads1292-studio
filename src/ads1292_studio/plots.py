from __future__ import annotations

from functools import lru_cache

import numpy as np


def endpoint_indices(size: int, max_points: int) -> np.ndarray:
    if size <= 0 or max_points <= 0:
        return np.asarray([], dtype=int)
    if size <= max_points:
        return np.arange(size, dtype=int)
    count = max(1, int(max_points))
    return np.unique(np.linspace(0, size - 1, count, dtype=int))


def smooth_for_plot(values, window: int = 5) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if window <= 1 or arr.size < window:
        return arr
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.pad(arr, pad_width=pad, mode="edge")
    return np.convolve(padded, smoothing_kernel(window), mode="valid")


@lru_cache(maxsize=16)
def smoothing_kernel(window: int) -> np.ndarray:
    return np.full(window, 1.0 / window)


@lru_cache(maxsize=64)
def extrema_bin_edges(size: int, max_points: int) -> np.ndarray:
    bin_count = max(1, (int(max_points) - 2) // 2)
    return np.linspace(0, int(size), bin_count + 1, dtype=int)


def decimate_for_plot(x, y, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    x_arr = np.asarray(x)
    y_arr = np.asarray(y)
    if x_arr.size != y_arr.size:
        raise ValueError("x and y must have the same length")
    if y_arr.size <= max_points:
        return x_arr, y_arr
    indices = endpoint_indices(y_arr.size, max_points)
    return x_arr[indices], y_arr[indices]


def decimate_aligned_for_plot(x, *ys, max_points: int) -> tuple[np.ndarray, ...]:
    x_arr = np.asarray(x)
    y_arrays = tuple(np.asarray(y) for y in ys)
    if x_arr.size <= max_points:
        return (x_arr, *y_arrays)
    if any(y_arr.size != x_arr.size for y_arr in y_arrays):
        raise ValueError("x and y arrays must have the same length")
    indices = endpoint_indices(x_arr.size, max_points)
    return (x_arr[indices], *(y_arr[indices] for y_arr in y_arrays))


def decimate_extrema_for_plot(x, y, max_points: int) -> tuple[np.ndarray, np.ndarray]:
    x_arr = np.asarray(x)
    y_arr = np.asarray(y)
    if x_arr.size != y_arr.size:
        raise ValueError("x and y must have the same length")
    if y_arr.size <= max_points:
        return x_arr, y_arr
    if max_points < 4:
        return decimate_for_plot(x_arr, y_arr, max_points=max_points)

    edges = extrema_bin_edges(y_arr.size, max_points)
    keep: list[int] = [0, y_arr.size - 1]
    for start, stop in zip(edges[:-1], edges[1:]):
        if stop <= start:
            continue
        segment = y_arr[start:stop]
        local_min = start + int(np.argmin(segment))
        local_max = start + int(np.argmax(segment))
        keep.extend(sorted({local_min, local_max}))
    indices = np.asarray(sorted(set(keep)), dtype=int)
    return x_arr[indices], y_arr[indices]


def robust_ylim(values, *, min_span: float = 0.0) -> tuple[float, float]:
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
    span = hi - lo
    if span < min_span:
        center = (hi + lo) / 2.0
        half_span = min_span / 2.0
        lo = center - half_span
        hi = center + half_span
    pad = max(1.0, 0.15 * (hi - lo))
    return float(lo - pad), float(hi + pad)


def stable_ylim(
    current_ylim: tuple[float, float],
    target_ylim: tuple[float, float],
    *,
    shrink_ratio: float = 0.55,
) -> tuple[float, float]:
    current_lo, current_hi = current_ylim
    target_lo, target_hi = target_ylim
    current_span = current_hi - current_lo
    target_span = target_hi - target_lo
    if current_span <= 0 or target_span <= 0:
        return target_ylim
    if target_lo < current_lo or target_hi > current_hi:
        return target_ylim
    if target_span < current_span * shrink_ratio:
        return target_ylim
    return current_ylim
