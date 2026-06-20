from types import SimpleNamespace

import numpy as np
from matplotlib.figure import Figure

from ads1292_studio.display import EcgDisplaySettings
from ads1292_studio.gui_plots import (
    apply_live_render_frame,
    draw_pqrst_review,
    restore_data_axis_chrome,
    show_empty_plot_state,
)
from ads1292_studio.live_render import LiveRenderFrame
from ads1292_studio.models import HeartRateSummary, PqrstReview


class FakeCanvas:
    def __init__(self) -> None:
        self.draw_idle_calls = 0

    def draw_idle(self) -> None:
        self.draw_idle_calls += 1


def test_draw_pqrst_review_renders_average_beat_and_refreshes_canvas() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)
    canvas = FakeCanvas()
    review = PqrstReview(
        qrs_clear=True,
        p_tentative=True,
        t_tentative=False,
        beats_used=3,
        average_beat=(0.0, 1.0, 0.0),
        time_ms=(-10.0, 0.0, 10.0),
    )

    draw_pqrst_review(ax, canvas, review)

    assert canvas.draw_idle_calls == 1
    assert "PQRST review: QRS=True" in ax.get_title()
    assert len(ax.lines) == 2
    assert ax.get_xlabel() == "Time relative to R peak (ms)"


def test_empty_plot_state_hides_axis_chrome_and_reference_lines() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)
    line, = ax.plot([0.0, 1.0], [0.0, 1.0])
    ax.set_xlabel("Time")
    ax.set_ylabel("Counts")
    artists: list[object] = []

    show_empty_plot_state(artists, "pqrst", (ax,))

    assert artists
    assert not ax.xaxis.label.get_visible()
    assert not ax.yaxis.label.get_visible()
    assert not line.get_visible()
    assert all(not spine.get_visible() for spine in ax.spines.values())


def test_restore_data_axis_chrome_reenables_axis_and_lines() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)
    line, = ax.plot([0.0, 1.0], [0.0, 1.0])
    artists: list[object] = []
    show_empty_plot_state(artists, "pqrst", (ax,))

    restore_data_axis_chrome((ax,))

    assert ax.xaxis.label.get_visible()
    assert ax.yaxis.label.get_visible()
    assert line.get_visible()
    assert ax.spines["left"].get_visible()
    assert ax.spines["bottom"].get_visible()


def test_apply_live_render_frame_updates_lines_axes_and_canvas() -> None:
    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    ecg_line, = ax_ecg.plot([], [])
    peak_line, = ax_ecg.plot([], [])
    resp_line, = ax_resp.plot([], [])
    status_line, = ax_status.plot([], [])
    canvas = FakeCanvas()
    app = SimpleNamespace(
        live_ecg_line=ecg_line,
        live_peak_line=peak_line,
        live_resp_line=resp_line,
        live_status_line=status_line,
        ax_live_ecg=ax_ecg,
        ax_live_resp=ax_resp,
        ax_live_status=ax_status,
        ecg_paper_grid_cache={},
        live_calibration_artists=[],
        calibration_pulse_cache={},
        live_canvas=canvas,
    )
    frame = LiveRenderFrame(
        source="CH2",
        left=1.0,
        right=9.0,
        visible_x=np.array([1.0, 2.0, 3.0]),
        visible_ecg=np.array([0.0, 2.0, 0.0]),
        visible_ecg_plot=np.array([0.0, 2.0, 0.0]),
        visible_resp_plot=np.array([10.0, 11.0, 12.0]),
        visible_status=np.array([0.0, 2.0, 2.0]),
        peaks=(1,),
        peaks_x=np.array([2.0]),
        peaks_y=np.array([2.0]),
        plot_ecg_x=np.array([1.0, 2.0, 3.0]),
        plot_ecg=np.array([0.0, 2.0, 0.0]),
        plot_resp_x=np.array([1.0, 2.0, 3.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([1.0, 2.0, 3.0]),
        plot_status=np.array([0.0, 2.0, 2.0]),
        heart_rate=HeartRateSummary(0.0, 0.0, 0.0, 0),
    )

    apply_live_render_frame(
        app,
        frame,
        display_settings=EcgDisplaySettings(time_window_seconds=8.0),
        autoscale=True,
        min_ecg_span_counts=8.0,
        min_resp_span_counts=40.0,
    )

    assert ecg_line.get_xdata().tolist() == [1.0, 2.0, 3.0]
    assert peak_line.get_ydata().tolist() == [2.0]
    assert resp_line.get_ydata().tolist() == [10.0, 11.0, 12.0]
    assert status_line.get_ydata().tolist() == [0.0, 2.0, 2.0]
    assert ax_ecg.get_xlim() == (1.0, 9.0)
    assert ax_status.get_ylim() == (-0.5, 2.5)
    assert canvas.draw_idle_calls == 1
