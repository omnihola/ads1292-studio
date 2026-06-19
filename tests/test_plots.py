from __future__ import annotations

import numpy as np

from ads1292_studio.plots import decimate_for_plot


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
