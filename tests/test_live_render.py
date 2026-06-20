from collections import deque
import inspect

import numpy as np

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings
from ads1292_studio.live_render import build_live_render_frame, deque_tail_array, display_signal_values


def test_deque_tail_array_limits_live_plot_work_to_visible_tail() -> None:
    values = deque(range(10), maxlen=10)

    assert deque_tail_array(values, 4, dtype=float).tolist() == [6.0, 7.0, 8.0, 9.0]
    assert deque_tail_array(values, 50, dtype=int).tolist() == list(range(10))
    assert deque_tail_array(values, 0, dtype=float).tolist() == []


def test_display_signal_gain_is_display_only() -> None:
    values = np.array([10.0, -20.0, 30.0])

    display = display_signal_values(
        values,
        filter_enabled=False,
        filter_settings=SoftwareFilterSettings(),
        gain=2.0,
    )

    np.testing.assert_array_equal(display, np.array([20.0, -40.0, 60.0]))
    np.testing.assert_array_equal(values, np.array([10.0, -20.0, 30.0]))


def test_build_live_render_frame_uses_only_visible_tail_and_decimates() -> None:
    indices = deque(range(20), maxlen=20)
    ch1 = deque((float(index) for index in range(20)), maxlen=20)
    ch2 = deque((1000.0 if index in {12, 16} else 0.0 for index in range(20)), maxlen=20)
    status = deque((0 if index < 18 else 3 for index in range(20)), maxlen=20)

    frame = build_live_render_frame(
        indices=indices,
        ch1=ch1,
        ch2=ch2,
        status=status,
        display_settings=EcgDisplaySettings(time_window_seconds=0.01),
        filter_settings=SoftwareFilterSettings(),
        source="CH2",
        sample_rate_hz=500.0,
        smoothing_window=1,
        max_render_points=4,
        ecg_inverted=False,
    )

    assert frame is not None
    assert frame.source == "CH2"
    assert frame.visible_x.tolist() == [
        13 / 500.0,
        14 / 500.0,
        15 / 500.0,
        16 / 500.0,
        17 / 500.0,
        18 / 500.0,
        19 / 500.0,
    ]
    assert np.isclose(frame.left, 0.028)
    assert np.isclose(frame.right, 0.038)
    assert frame.visible_status.tolist() == [0.0, 0.0, 0.0, 0.0, 0.0, 3.0, 3.0]
    assert len(frame.plot_ecg) <= 4
    assert len(frame.plot_resp) <= 4
    assert len(frame.plot_status) <= 4
    assert frame.visible_ecg[3] == 1000.0


def test_build_live_render_frame_returns_none_without_samples() -> None:
    frame = build_live_render_frame(
        indices=deque(),
        ch1=deque(),
        ch2=deque(),
        status=deque(),
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(),
        source="CH2",
        sample_rate_hz=500.0,
        smoothing_window=1,
        max_render_points=100,
        ecg_inverted=False,
    )

    assert frame is None


def test_live_render_reuses_bandpass_display_for_peak_detection() -> None:
    source = inspect.getsource(build_live_render_frame)

    assert "prefiltered=bool(filter_settings.bandpass_enabled)" in source
