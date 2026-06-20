from __future__ import annotations

import numpy as np

from ads1292_studio.plots import (
    decimate_aligned_for_plot,
    decimate_extrema_for_plot,
    decimate_for_plot,
    endpoint_indices,
    extrema_bin_edges,
    robust_ylim,
    smooth_for_plot,
    smoothing_kernel,
    stable_ylim,
)


def test_endpoint_indices_preserve_latest_sample_within_budget() -> None:
    indices = endpoint_indices(1000, 100)

    assert 0 < indices.size <= 100
    assert indices[0] == 0
    assert indices[-1] == 999


def test_smooth_for_plot_returns_original_values_when_window_is_too_small() -> None:
    values = np.array([1.0, 4.0, 1.0])

    out = smooth_for_plot(values, window=1)

    np.testing.assert_array_equal(out, values)


def test_smooth_for_plot_keeps_length_and_reduces_single_sample_spikes() -> None:
    values = np.array([0.0, 0.0, 9.0, 0.0, 0.0])

    out = smooth_for_plot(values, window=3)

    assert out.size == values.size
    assert out[2] < values[2]
    assert out[2] == 3.0


def test_smoothing_kernel_is_cached_for_live_render_reuse() -> None:
    smoothing_kernel.cache_clear()

    first = smoothing_kernel(11)
    second = smoothing_kernel(11)

    assert first is second
    np.testing.assert_allclose(first, np.full(11, 1.0 / 11.0))


def test_smooth_for_plot_even_window_uses_cached_odd_kernel() -> None:
    smoothing_kernel.cache_clear()
    values = np.arange(8, dtype=float)

    smooth_for_plot(values, window=4)

    assert smoothing_kernel.cache_info().misses == 1
    assert smoothing_kernel.cache_info().currsize == 1
    assert smoothing_kernel(5).size == 5


def test_extrema_bin_edges_are_cached_for_stable_live_windows() -> None:
    extrema_bin_edges.cache_clear()

    first = extrema_bin_edges(4002, 2500)
    second = extrema_bin_edges(4002, 2500)

    assert first is second
    assert first[0] == 0
    assert first[-1] == 4002
    assert extrema_bin_edges.cache_info().hits == 1


def test_decimate_extrema_for_plot_reuses_cached_bin_edges() -> None:
    extrema_bin_edges.cache_clear()
    x = np.arange(1000)
    y = np.sin(np.linspace(0, 20, 1000))

    decimate_extrema_for_plot(x, y, max_points=100)
    decimate_extrema_for_plot(x, y, max_points=100)

    assert extrema_bin_edges.cache_info().hits == 1


def test_robust_ylim_can_keep_flat_noise_from_being_overzoomed() -> None:
    values = np.array([-1.0, -0.8, -1.1, -0.9])

    lo, hi = robust_ylim(values, min_span=8.0)

    assert hi - lo >= 8.0
    assert lo < -1.0
    assert hi > -0.8


def test_stable_ylim_keeps_current_range_for_small_inside_changes() -> None:
    assert stable_ylim((-5.0, 5.0), (-4.0, 4.0)) == (-5.0, 5.0)


def test_stable_ylim_expands_when_signal_leaves_current_range() -> None:
    assert stable_ylim((-5.0, 5.0), (-6.0, 5.0)) == (-6.0, 5.0)
    assert stable_ylim((-5.0, 5.0), (-5.0, 6.0)) == (-5.0, 6.0)


def test_stable_ylim_shrinks_after_large_range_change() -> None:
    assert stable_ylim((-10.0, 10.0), (-3.0, 3.0)) == (-3.0, 3.0)


def test_decimate_for_plot_returns_unchanged_arrays_when_within_budget() -> None:
    x = np.arange(10)
    y = np.arange(10, dtype=float)

    out_x, out_y = decimate_for_plot(x, y, max_points=20)

    assert list(out_x) == list(x)
    assert list(out_y) == list(y)


def test_decimate_for_plot_decimates_large_arrays_to_budget() -> None:
    x = np.arange(1000)
    y = np.arange(1000, dtype=float)

    out_x, out_y = decimate_for_plot(x, y, max_points=100)

    assert 0 < out_x.size <= 100
    assert out_x.size == out_y.size
    assert list(out_x) == [int(value) for value in out_y]
    assert out_x[0] == x[0]
    assert out_x[-1] == x[-1]


def test_decimate_aligned_for_plot_uses_one_stride_for_all_traces() -> None:
    x = np.arange(1000)
    ecg = x + 10
    resp = x + 20
    status = x % 4

    out_x, out_ecg, out_resp, out_status = decimate_aligned_for_plot(x, ecg, resp, status, max_points=100)

    assert 0 < out_x.size <= 100
    assert out_x.size == out_ecg.size == out_resp.size == out_status.size
    assert out_x[0] == x[0]
    assert out_x[-1] == x[-1]
    np.testing.assert_array_equal(out_ecg, out_x + 10)
    np.testing.assert_array_equal(out_resp, out_x + 20)
    np.testing.assert_array_equal(out_status, out_x % 4)


def test_decimate_extrema_for_plot_preserves_narrow_spikes() -> None:
    x = np.arange(1000)
    y = np.zeros(1000)
    y[427] = 12.0
    y[428] = -5.0

    out_x, out_y = decimate_extrema_for_plot(x, y, max_points=100)

    assert out_x.size <= 100
    assert out_x[0] == x[0]
    assert out_x[-1] == x[-1]
    assert 427 in set(out_x.tolist())
    assert 428 in set(out_x.tolist())
    assert 12.0 in set(out_y.tolist())
    assert -5.0 in set(out_y.tolist())


def test_decimate_extrema_for_plot_returns_unchanged_arrays_within_budget() -> None:
    x = np.arange(8)
    y = np.linspace(-1, 1, 8)

    out_x, out_y = decimate_extrema_for_plot(x, y, max_points=20)

    np.testing.assert_array_equal(out_x, x)
    np.testing.assert_array_equal(out_y, y)
