from types import SimpleNamespace

import numpy as np
from matplotlib.figure import Figure

from ads1292_studio.display import EcgDisplaySettings
from ads1292_studio.gui_plots import (
    apply_ecg_paper_grid,
    apply_live_render_frame,
    apply_review_render_frame,
    calibration_pulse_needs_update,
    draw_calibration_pulse,
    draw_pqrst_review,
    live_contact_trace_color,
    restore_data_axis_chrome,
    set_axis_xlabel_if_changed,
    set_line_data_if_changed,
    set_line_color_if_changed,
    set_line_visible_if_changed,
    sparse_time_tick_label,
    flush_pending_pqrst_review,
    show_empty_plot_state,
)
from ads1292_studio.live_render import LiveRenderFrame
from ads1292_studio.models import HeartRateSummary, PqrstReview
from ads1292_studio.plot_theme import APP_VISUAL_TOKENS, PLOT_TRACE_COLORS


class FakeCanvas:
    def __init__(self) -> None:
        self.draw_idle_calls = 0

    def draw_idle(self) -> None:
        self.draw_idle_calls += 1


class FakeMappedWidget:
    def __init__(self, mapped: bool) -> None:
        self.mapped = mapped

    def winfo_ismapped(self) -> bool:
        return self.mapped


class CountingLine:
    def __init__(self, *, color: str = PLOT_TRACE_COLORS["contact"], visible: bool = True) -> None:
        self.x = np.array([], dtype=float)
        self.y = np.array([], dtype=float)
        self.color = color
        self.visible = visible
        self.set_data_calls = 0
        self.set_color_calls = 0
        self.set_visible_calls = 0

    def get_xdata(self) -> np.ndarray:
        return self.x

    def get_ydata(self) -> np.ndarray:
        return self.y

    def set_data(self, x: np.ndarray, y: np.ndarray) -> None:
        self.x = x
        self.y = y
        self.set_data_calls += 1

    def get_color(self) -> str:
        return self.color

    def set_color(self, color: str) -> None:
        self.color = color
        self.set_color_calls += 1

    def get_visible(self) -> bool:
        return self.visible

    def set_visible(self, visible: bool) -> None:
        self.visible = visible
        self.set_visible_calls += 1


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


def test_draw_spectrum_analysis_renders_fft_and_histogram() -> None:
    from ads1292_studio import gui_plots
    from ads1292_studio.spectrum import SpectrumAnalysis

    draw_spectrum_analysis = getattr(gui_plots, "draw_spectrum_analysis")
    fig = Figure()
    ax_fft = fig.add_subplot(211)
    ax_hist = fig.add_subplot(212)
    canvas = FakeCanvas()
    analysis = SpectrumAnalysis(
        ecg_label="CH2",
        ecg_frequency_hz=np.array([0.0, 10.0, 20.0]),
        ecg_power=np.array([0.0, 5.0, 1.0]),
        histogram_counts=np.array([2, 4, 2]),
        histogram_bin_edges=np.array([-1.0, 0.0, 1.0, 2.0]),
    )

    draw_spectrum_analysis(ax_fft, ax_hist, canvas, analysis)

    assert canvas.draw_idle_calls == 1
    assert "FFT spectrum: CH2" in ax_fft.get_title()
    assert ax_fft.get_xlabel() == "Frequency (Hz)"
    assert ax_hist.get_xlabel() == "Raw counts"
    assert len(ax_fft.lines) == 1
    assert len(ax_hist.patches) == 3


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


def test_empty_plot_state_uses_quiet_background_until_data_arrives() -> None:
    from matplotlib.colors import to_rgba

    from ads1292_studio.gui_specs import empty_plot_style

    fig = Figure()
    ax = fig.add_subplot(111)
    artists: list[object] = []

    show_empty_plot_state(artists, "pqrst", (ax,))

    assert ax.get_facecolor() == to_rgba(empty_plot_style()["axis_face"])


def test_empty_plot_state_adds_muted_reference_guides() -> None:
    from ads1292_studio.gui_specs import empty_plot_style

    fig = Figure()
    ax = fig.add_subplot(111)
    artists: list[object] = []

    show_empty_plot_state(artists, "pqrst", (ax,))

    guide_lines = [line for line in ax.lines if line.get_visible()]
    assert len(guide_lines) == 1
    assert guide_lines[0] in artists
    assert guide_lines[0].get_alpha() == empty_plot_style()["guide_alpha"]
    assert guide_lines[0].get_color() == empty_plot_style()["guide_color"]


def test_empty_plot_state_skips_duplicate_artists_for_same_panel() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)
    artists: list[object] = []

    show_empty_plot_state(artists, "pqrst", (ax,))
    first_artist_count = len(artists)
    first_line_count = len(ax.lines)
    first_text_count = len(ax.texts)

    show_empty_plot_state(artists, "pqrst", (ax,))

    assert len(artists) == first_artist_count
    assert len(ax.lines) == first_line_count
    assert len(ax.texts) == first_text_count


def test_empty_plot_state_allows_new_artists_when_panel_key_changes() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)
    artists: list[object] = []

    show_empty_plot_state(artists, "pqrst", (ax,))
    show_empty_plot_state(artists, "live", (ax,))

    assert len(artists) == 4
    assert ax.texts[-1].get_text() == "Connect, then Start for CH2 ECG"


def test_restore_data_axis_chrome_reenables_axis_and_lines() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)
    line, = ax.plot([0.0, 1.0], [0.0, 1.0])
    artists: list[object] = []
    show_empty_plot_state(artists, "pqrst", (ax,))

    restored = restore_data_axis_chrome((ax,))

    assert restored is True
    assert ax.xaxis.label.get_visible()
    assert ax.yaxis.label.get_visible()
    assert line.get_visible()
    assert ax.spines["left"].get_visible()
    assert ax.spines["bottom"].get_visible()


def test_restore_data_axis_chrome_skips_when_axis_is_already_active(monkeypatch) -> None:
    import ads1292_studio.gui_plots as gui_plots

    fig = Figure()
    ax = fig.add_subplot(111)
    artists: list[object] = []
    calls = {"style": 0}
    original_style = gui_plots.style_signal_axes

    def counted_style(axes: tuple[object, ...]) -> None:
        calls["style"] += 1
        original_style(axes)

    monkeypatch.setattr(gui_plots, "style_signal_axes", counted_style)
    show_empty_plot_state(artists, "pqrst", (ax,))

    restored = restore_data_axis_chrome((ax,))
    skipped = restore_data_axis_chrome((ax,))

    assert restored is True
    assert skipped is False
    assert calls["style"] == 1
    assert getattr(ax, "_ads1292_empty_axis_chrome") is False


def test_calibration_pulse_needs_update_uses_artist_and_label_cache() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)
    artists: list[object] = []
    cache: dict[int, str] = {}
    settings = EcgDisplaySettings(gain=1.0)

    assert calibration_pulse_needs_update(ax, artists, settings, cache) is True

    draw_calibration_pulse(ax, artists, settings, cache)

    assert artists
    assert calibration_pulse_needs_update(ax, artists, settings, cache) is False
    assert calibration_pulse_needs_update(ax, artists, EcgDisplaySettings(gain=2.0), cache) is True


def test_ecg_paper_grid_keeps_sparse_two_second_time_labels() -> None:
    fig = Figure()
    ax = fig.add_subplot(111)

    apply_ecg_paper_grid(ax, EcgDisplaySettings(sweep_speed_mm_s=25), {})

    formatter = ax.xaxis.get_major_formatter()
    assert sparse_time_tick_label(30.6, None) == ""
    assert formatter(30.8, None) == ""
    assert formatter(32.0, None) == "32"
    assert formatter(34.0, None) == "34"


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
    assert peak_line.get_visible() is True
    assert resp_line.get_ydata().tolist() == [10.0, 11.0, 12.0]
    assert ax_ecg.get_xlim() == (1.0, 9.0)
    assert ax_resp.get_xlim() == (1.0, 9.0)
    assert canvas.draw_idle_calls == 1


def test_apply_live_render_frame_skips_redundant_main_trace_writes() -> None:
    class FakeLine:
        def __init__(self, *, color: str = PLOT_TRACE_COLORS["contact"]) -> None:
            self.x = np.array([], dtype=float)
            self.y = np.array([], dtype=float)
            self.color = color
            self.visible = True
            self.set_data_calls = 0

        def get_xdata(self) -> np.ndarray:
            return self.x

        def get_ydata(self) -> np.ndarray:
            return self.y

        def set_data(self, x: np.ndarray, y: np.ndarray) -> None:
            self.x = x
            self.y = y
            self.set_data_calls += 1

        def get_color(self) -> str:
            return self.color

        def set_color(self, color: str) -> None:
            self.color = color

        def get_visible(self) -> bool:
            return self.visible

        def set_visible(self, visible: bool) -> None:
            self.visible = visible

    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    app = SimpleNamespace(
        live_ecg_line=FakeLine(),
        live_peak_line=FakeLine(),
        live_resp_line=FakeLine(),
        live_status_line=FakeLine(),
        ax_live_ecg=ax_ecg,
        ax_live_resp=ax_resp,
        ax_live_status=ax_status,
        ecg_paper_grid_cache={},
        live_calibration_artists=[],
        calibration_pulse_cache={},
        live_canvas=FakeCanvas(),
    )
    frame = LiveRenderFrame(
        source="CH2",
        left=1.0,
        right=9.0,
        visible_x=np.array([1.0, 2.0, 3.0]),
        visible_ecg=np.array([0.0, 2.0, 0.0]),
        visible_ecg_plot=np.array([0.0, 2.0, 0.0]),
        visible_resp_plot=np.array([10.0, 11.0, 12.0]),
        visible_status=np.array([0.0, 0.0, 0.0]),
        peaks=tuple(),
        peaks_x=np.array([], dtype=float),
        peaks_y=np.array([], dtype=float),
        plot_ecg_x=np.array([1.0, 2.0, 3.0]),
        plot_ecg=np.array([0.0, 2.0, 0.0]),
        plot_resp_x=np.array([1.0, 2.0, 3.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([1.0, 2.0, 3.0]),
        plot_status=np.array([0.0, 0.0, 0.0]),
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
    apply_live_render_frame(
        app,
        frame,
        display_settings=EcgDisplaySettings(time_window_seconds=8.0),
        autoscale=True,
        min_ecg_span_counts=8.0,
        min_resp_span_counts=40.0,
    )

    assert app.live_ecg_line.set_data_calls == 1
    assert app.live_resp_line.set_data_calls == 1
    assert app.live_canvas.draw_idle_calls == 1


def test_apply_live_render_frame_defers_canvas_draw_when_live_tab_is_hidden() -> None:
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
        live_tab=FakeMappedWidget(mapped=False),
    )
    frame = LiveRenderFrame(
        source="CH2",
        left=1.0,
        right=9.0,
        visible_x=np.array([1.0, 2.0, 3.0]),
        visible_ecg=np.array([0.0, 2.0, 0.0]),
        visible_ecg_plot=np.array([0.0, 2.0, 0.0]),
        visible_resp_plot=np.array([10.0, 11.0, 12.0]),
        visible_status=np.array([0.0, 0.0, 0.0]),
        peaks=(),
        peaks_x=np.array([], dtype=float),
        peaks_y=np.array([], dtype=float),
        plot_ecg_x=np.array([1.0, 2.0, 3.0]),
        plot_ecg=np.array([0.0, 2.0, 0.0]),
        plot_resp_x=np.array([1.0, 2.0, 3.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([1.0, 2.0, 3.0]),
        plot_status=np.array([0.0, 0.0, 0.0]),
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
    assert ax_ecg.get_xlim() == (1.0, 9.0)
    assert canvas.draw_idle_calls == 0


def test_apply_live_render_frame_hides_empty_peak_marker_artist() -> None:
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
        visible_ecg=np.array([0.0, 0.0, 0.0]),
        visible_ecg_plot=np.array([0.0, 0.0, 0.0]),
        visible_resp_plot=np.array([10.0, 11.0, 12.0]),
        visible_status=np.array([0.0, 0.0, 0.0]),
        peaks=(),
        peaks_x=np.array([], dtype=float),
        peaks_y=np.array([], dtype=float),
        plot_ecg_x=np.array([1.0, 2.0, 3.0]),
        plot_ecg=np.array([0.0, 0.0, 0.0]),
        plot_resp_x=np.array([1.0, 2.0, 3.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([1.0, 2.0, 3.0]),
        plot_status=np.array([0.0, 0.0, 0.0]),
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

    assert peak_line.get_visible() is False
    assert peak_line.get_xdata().tolist() == []
    assert peak_line.get_ydata().tolist() == []


def test_live_contact_trace_color_flags_visible_lead_off() -> None:
    assert live_contact_trace_color(np.array([], dtype=float)) == PLOT_TRACE_COLORS["contact"]
    assert live_contact_trace_color(np.array([0.0, 0.0])) == PLOT_TRACE_COLORS["contact"]
    assert live_contact_trace_color(np.array([0.0, 2.0])) == APP_VISUAL_TOKENS["warning"]


def test_set_line_color_if_changed_skips_redundant_matplotlib_writes() -> None:
    class FakeLine:
        def __init__(self) -> None:
            self.color = "blue"
            self.set_color_calls = 0

        def get_color(self) -> str:
            return self.color

        def set_color(self, color: str) -> None:
            self.color = color
            self.set_color_calls += 1

    line = FakeLine()

    assert set_line_color_if_changed(line, "blue") is False
    assert line.set_color_calls == 0
    assert set_line_color_if_changed(line, "orange") is True
    assert line.color == "orange"
    assert line.set_color_calls == 1


def test_set_line_visible_if_changed_skips_redundant_matplotlib_writes() -> None:
    class FakeLine:
        def __init__(self) -> None:
            self.visible = True
            self.set_visible_calls = 0

        def get_visible(self) -> bool:
            return self.visible

        def set_visible(self, visible: bool) -> None:
            self.visible = visible
            self.set_visible_calls += 1

    line = FakeLine()

    assert set_line_visible_if_changed(line, True) is False
    assert line.set_visible_calls == 0
    assert set_line_visible_if_changed(line, False) is True
    assert line.visible is False
    assert line.set_visible_calls == 1


def test_set_line_data_if_changed_skips_redundant_peak_marker_writes() -> None:
    class FakeLine:
        def __init__(self) -> None:
            self.x = np.array([], dtype=float)
            self.y = np.array([], dtype=float)
            self.set_data_calls = 0

        def get_xdata(self) -> np.ndarray:
            return self.x

        def get_ydata(self) -> np.ndarray:
            return self.y

        def set_data(self, x: np.ndarray, y: np.ndarray) -> None:
            self.x = x
            self.y = y
            self.set_data_calls += 1

    line = FakeLine()

    assert set_line_data_if_changed(line, np.array([], dtype=float), np.array([], dtype=float)) is False
    assert line.set_data_calls == 0
    assert set_line_data_if_changed(line, np.array([1.0]), np.array([2.0])) is True
    assert line.set_data_calls == 1
    assert set_line_data_if_changed(line, np.array([1.0]), np.array([2.0])) is False
    assert line.set_data_calls == 1


def test_set_axis_xlabel_if_changed_skips_redundant_matplotlib_writes() -> None:
    class FakeAxis:
        def __init__(self) -> None:
            self.xlabel = "Time (s)"
            self.set_xlabel_calls = 0

        def get_xlabel(self) -> str:
            return self.xlabel

        def set_xlabel(self, value: str) -> None:
            self.xlabel = value
            self.set_xlabel_calls += 1

    axis = FakeAxis()

    assert set_axis_xlabel_if_changed(axis, "Time (s)") is False
    assert axis.set_xlabel_calls == 0
    assert set_axis_xlabel_if_changed(axis, "Time relative to R peak (ms)") is True
    assert axis.xlabel == "Time relative to R peak (ms)"
    assert axis.set_xlabel_calls == 1


def test_apply_review_render_frame_updates_review_lines_axes_and_pqrst() -> None:
    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    ax_pqrst = Figure().add_subplot(111)
    ecg_line, = ax_ecg.plot([], [])
    peak_line, = ax_ecg.plot([], [])
    resp_line, = ax_resp.plot([], [])
    status_line, = ax_status.plot([], [])
    review_canvas = FakeCanvas()
    pqrst_canvas = FakeCanvas()
    app = SimpleNamespace(
        review_ecg_line=ecg_line,
        review_peak_line=peak_line,
        review_resp_line=resp_line,
        review_status_line=status_line,
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
        ax_review_status=ax_status,
        ax_pqrst=ax_pqrst,
        ecg_paper_grid_cache={},
        review_calibration_artists=[],
        calibration_pulse_cache={},
        review_canvas=review_canvas,
        pqrst_canvas=pqrst_canvas,
    )
    frame = SimpleNamespace(
        mode="raw, display-smoothed",
        plot_ecg_x=np.array([0.0, 1.0, 2.0]),
        plot_ecg=np.array([0.0, 2.0, 0.0]),
        plot_resp_x=np.array([0.0, 1.0, 2.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([0.0, 1.0, 2.0]),
        plot_status=np.array([0.0, 1.0, 1.0]),
        peak_x=np.array([1.0]),
        peak_y=np.array([2.0]),
        x_right=2.0,
        ecg_ylim=(-3.0, 3.0),
        resp_ylim=(8.0, 14.0),
        status_ylim=(-0.5, 1.5),
        review=SimpleNamespace(
            heart_rate=HeartRateSummary(72.0, 0.0, 0.0, 1),
            peaks=(1,),
        ),
        pqrst=PqrstReview(
            qrs_clear=True,
            p_tentative=True,
            t_tentative=False,
            beats_used=1,
            average_beat=(0.0, 1.0, 0.0),
            time_ms=(-10.0, 0.0, 10.0),
        ),
    )

    apply_review_render_frame(
        app,
        frame,
        display_settings=EcgDisplaySettings(time_window_seconds=8.0),
        ecg_label="CH2 ECG Lead I",
        resp_label="CH1 respiration",
        ecg_inverted=False,
    )

    assert ecg_line.get_ydata().tolist() == [0.0, 2.0, 0.0]
    assert peak_line.get_xdata().tolist() == [1.0]
    assert resp_line.get_ydata().tolist() == [10.0, 11.0, 12.0]
    assert ax_ecg.get_xlim() == (0.0, 2.0)
    assert ax_ecg.get_ylim() == (-3.0, 3.0)
    assert ax_resp.get_xlabel() == "Time (s)"
    assert ax_ecg.get_title() == "CH2-ECG"
    assert ax_resp.get_title() == "CH1-Respiration"
    assert review_canvas.draw_idle_calls == 1
    assert pqrst_canvas.draw_idle_calls == 1


def test_apply_review_render_frame_skips_unchanged_pqrst_redraw() -> None:
    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    ax_pqrst = Figure().add_subplot(111)
    ecg_line = CountingLine()
    peak_line = CountingLine()
    resp_line = CountingLine()
    status_line = CountingLine()
    review_canvas = FakeCanvas()
    pqrst_canvas = FakeCanvas()
    app = SimpleNamespace(
        review_ecg_line=ecg_line,
        review_peak_line=peak_line,
        review_resp_line=resp_line,
        review_status_line=status_line,
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
        ax_review_status=ax_status,
        ax_pqrst=ax_pqrst,
        ecg_paper_grid_cache={},
        review_calibration_artists=[],
        calibration_pulse_cache={},
        review_canvas=review_canvas,
        pqrst_canvas=pqrst_canvas,
    )
    pqrst = PqrstReview(
        qrs_clear=True,
        p_tentative=True,
        t_tentative=True,
        beats_used=2,
        average_beat=(0.0, 1.0, 0.0),
        time_ms=(-10.0, 0.0, 10.0),
    )
    frame = SimpleNamespace(
        mode="raw, display-smoothed",
        plot_ecg_x=np.array([0.0, 1.0, 2.0]),
        plot_ecg=np.array([0.0, 2.0, 0.0]),
        plot_resp_x=np.array([0.0, 1.0, 2.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([0.0, 1.0, 2.0]),
        plot_status=np.array([0.0, 1.0, 1.0]),
        peak_x=np.array([1.0]),
        peak_y=np.array([2.0]),
        x_right=2.0,
        ecg_ylim=(-3.0, 3.0),
        resp_ylim=(8.0, 14.0),
        status_ylim=(-0.5, 1.5),
        review=SimpleNamespace(
            heart_rate=HeartRateSummary(72.0, 0.0, 0.0, 1),
            peaks=(1,),
        ),
        pqrst=pqrst,
    )

    for _ in range(2):
        apply_review_render_frame(
            app,
            frame,
            display_settings=EcgDisplaySettings(time_window_seconds=8.0),
            ecg_label="CH2 ECG Lead I",
            resp_label="CH1 respiration",
            ecg_inverted=False,
        )

    assert ecg_line.set_data_calls == 1
    assert resp_line.set_data_calls == 1
    assert review_canvas.draw_idle_calls == 1
    assert pqrst_canvas.draw_idle_calls == 1


def test_apply_review_render_frame_defers_canvas_draw_when_review_tabs_are_hidden() -> None:
    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    ax_pqrst = Figure().add_subplot(111)
    ecg_line, = ax_ecg.plot([], [])
    peak_line, = ax_ecg.plot([], [])
    resp_line, = ax_resp.plot([], [])
    status_line, = ax_status.plot([], [])
    review_canvas = FakeCanvas()
    pqrst_canvas = FakeCanvas()
    app = SimpleNamespace(
        review_ecg_line=ecg_line,
        review_peak_line=peak_line,
        review_resp_line=resp_line,
        review_status_line=status_line,
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
        ax_review_status=ax_status,
        ax_pqrst=ax_pqrst,
        ecg_paper_grid_cache={},
        review_calibration_artists=[],
        calibration_pulse_cache={},
        review_canvas=review_canvas,
        pqrst_canvas=pqrst_canvas,
        review_tab=FakeMappedWidget(mapped=False),
        pqrst_tab=FakeMappedWidget(mapped=False),
    )
    frame = SimpleNamespace(
        mode="raw, display-smoothed",
        plot_ecg_x=np.array([0.0, 1.0, 2.0]),
        plot_ecg=np.array([0.0, 2.0, 0.0]),
        plot_resp_x=np.array([0.0, 1.0, 2.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([0.0, 1.0, 2.0]),
        plot_status=np.array([0.0, 1.0, 1.0]),
        peak_x=np.array([1.0]),
        peak_y=np.array([2.0]),
        x_right=2.0,
        ecg_ylim=(-3.0, 3.0),
        resp_ylim=(8.0, 14.0),
        status_ylim=(-0.5, 1.5),
        review=SimpleNamespace(
            heart_rate=HeartRateSummary(72.0, 0.0, 0.0, 1),
            peaks=(1,),
        ),
        pqrst=PqrstReview(
            qrs_clear=True,
            p_tentative=True,
            t_tentative=False,
            beats_used=1,
            average_beat=(0.0, 1.0, 0.0),
            time_ms=(-10.0, 0.0, 10.0),
        ),
    )

    apply_review_render_frame(
        app,
        frame,
        display_settings=EcgDisplaySettings(time_window_seconds=8.0),
        ecg_label="CH2 ECG Lead I",
        resp_label="CH1 respiration",
        ecg_inverted=False,
    )

    assert ecg_line.get_ydata().tolist() == []
    assert ax_ecg.get_xlim() != (0.0, 2.0)
    assert app.pending_review_plot.frame is frame
    assert len(ax_pqrst.lines) == 0
    assert app.pending_pqrst_review == frame.pqrst
    assert review_canvas.draw_idle_calls == 0
    assert pqrst_canvas.draw_idle_calls == 0


def test_flush_pending_review_render_draws_when_review_tab_becomes_visible() -> None:
    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    ax_pqrst = Figure().add_subplot(111)
    ecg_line, = ax_ecg.plot([], [])
    peak_line, = ax_ecg.plot([], [])
    resp_line, = ax_resp.plot([], [])
    status_line, = ax_status.plot([], [])
    review_canvas = FakeCanvas()
    pqrst_canvas = FakeCanvas()
    from ads1292_studio.gui_plots import PendingReviewPlot, flush_pending_review_render

    frame = SimpleNamespace(
        mode="raw, display-smoothed",
        plot_ecg_x=np.array([0.0, 1.0, 2.0]),
        plot_ecg=np.array([0.0, 2.0, 0.0]),
        plot_resp_x=np.array([0.0, 1.0, 2.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([0.0, 1.0, 2.0]),
        plot_status=np.array([0.0, 1.0, 1.0]),
        peak_x=np.array([1.0]),
        peak_y=np.array([2.0]),
        x_right=2.0,
        ecg_ylim=(-3.0, 3.0),
        resp_ylim=(8.0, 14.0),
        status_ylim=(-0.5, 1.5),
        review=SimpleNamespace(
            heart_rate=HeartRateSummary(72.0, 0.0, 0.0, 1),
            peaks=(1,),
        ),
        pqrst=PqrstReview(
            qrs_clear=True,
            p_tentative=True,
            t_tentative=False,
            beats_used=1,
            average_beat=(0.0, 1.0, 0.0),
            time_ms=(-10.0, 0.0, 10.0),
        ),
    )
    app = SimpleNamespace(
        review_ecg_line=ecg_line,
        review_peak_line=peak_line,
        review_resp_line=resp_line,
        review_status_line=status_line,
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
        ax_review_status=ax_status,
        ax_pqrst=ax_pqrst,
        ecg_paper_grid_cache={},
        review_calibration_artists=[],
        calibration_pulse_cache={},
        review_canvas=review_canvas,
        pqrst_canvas=pqrst_canvas,
        review_tab=FakeMappedWidget(mapped=True),
        pqrst_tab=FakeMappedWidget(mapped=False),
        pending_review_plot=PendingReviewPlot(
            frame=frame,
            display_settings=EcgDisplaySettings(time_window_seconds=8.0),
            ecg_label="CH2 ECG Lead I",
            resp_label="CH1 respiration",
            ecg_inverted=False,
        ),
    )

    assert flush_pending_review_render(app) is True
    assert app.pending_review_plot is None
    assert ecg_line.get_ydata().tolist() == [0.0, 2.0, 0.0]
    assert ax_ecg.get_xlim() == (0.0, 2.0)
    assert review_canvas.draw_idle_calls == 1
    assert app.pending_pqrst_review == frame.pqrst


def test_flush_pending_review_render_can_force_selected_tab_before_tk_maps() -> None:
    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    ecg_line, = ax_ecg.plot([], [])
    peak_line, = ax_ecg.plot([], [])
    resp_line, = ax_resp.plot([], [])
    status_line, = ax_status.plot([], [])
    from ads1292_studio.gui_plots import PendingReviewPlot, flush_pending_review_render

    frame = SimpleNamespace(
        mode="raw, display-smoothed",
        plot_ecg_x=np.array([0.0, 1.0]),
        plot_ecg=np.array([0.0, 2.0]),
        plot_resp_x=np.array([0.0, 1.0]),
        plot_resp=np.array([10.0, 11.0]),
        plot_status_x=np.array([0.0, 1.0]),
        plot_status=np.array([0.0, 0.0]),
        peak_x=np.array([1.0]),
        peak_y=np.array([2.0]),
        x_right=1.0,
        ecg_ylim=(-3.0, 3.0),
        resp_ylim=(8.0, 12.0),
        status_ylim=(-0.5, 1.5),
        review=SimpleNamespace(
            heart_rate=HeartRateSummary(72.0, 0.0, 0.0, 1),
            peaks=(1,),
        ),
        pqrst=PqrstReview(True, True, False, 1, (0.0, 1.0, 0.0), (-10.0, 0.0, 10.0)),
    )
    app = SimpleNamespace(
        review_ecg_line=ecg_line,
        review_peak_line=peak_line,
        review_resp_line=resp_line,
        review_status_line=status_line,
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
        ax_review_status=ax_status,
        ax_pqrst=Figure().add_subplot(111),
        ecg_paper_grid_cache={},
        review_calibration_artists=[],
        calibration_pulse_cache={},
        review_canvas=FakeCanvas(),
        pqrst_canvas=FakeCanvas(),
        review_tab=FakeMappedWidget(mapped=False),
        pqrst_tab=FakeMappedWidget(mapped=False),
        pending_review_plot=PendingReviewPlot(
            frame=frame,
            display_settings=EcgDisplaySettings(time_window_seconds=8.0),
            ecg_label="CH2 ECG Lead I",
            resp_label="CH1 respiration",
            ecg_inverted=False,
        ),
    )

    assert flush_pending_review_render(app, force=True) is True
    assert app.pending_review_plot is None
    assert ecg_line.get_ydata().tolist() == [0.0, 2.0]


def test_flush_pending_pqrst_review_draws_when_pqrst_tab_becomes_visible() -> None:
    ax = Figure().add_subplot(111)
    canvas = FakeCanvas()
    review = PqrstReview(
        qrs_clear=True,
        p_tentative=True,
        t_tentative=False,
        beats_used=1,
        average_beat=(0.0, 1.0, 0.0),
        time_ms=(-10.0, 0.0, 10.0),
    )
    app = SimpleNamespace(
        ax_pqrst=ax,
        pqrst_canvas=canvas,
        pqrst_tab=FakeMappedWidget(mapped=True),
        pending_pqrst_review=review,
    )

    assert flush_pending_pqrst_review(app) is True
    assert app.pending_pqrst_review is None
    assert app.last_pqrst_review == review
    assert len(ax.lines) == 2
    assert canvas.draw_idle_calls == 1


def test_flush_pending_pqrst_review_can_force_selected_tab_before_tk_maps() -> None:
    ax = Figure().add_subplot(111)
    canvas = FakeCanvas()
    review = PqrstReview(True, True, False, 1, (0.0, 1.0, 0.0), (-10.0, 0.0, 10.0))
    app = SimpleNamespace(
        ax_pqrst=ax,
        pqrst_canvas=canvas,
        pqrst_tab=FakeMappedWidget(mapped=False),
        pending_pqrst_review=review,
    )

    assert flush_pending_pqrst_review(app, force=True) is True
    assert app.pending_pqrst_review is None
    assert len(ax.lines) == 2


def test_apply_review_render_frame_skips_unchanged_peak_marker_writes() -> None:
    fig = Figure()
    ax_ecg = fig.add_subplot(311)
    ax_resp = fig.add_subplot(312)
    ax_status = fig.add_subplot(313)
    ax_pqrst = Figure().add_subplot(111)
    ecg_line, = ax_ecg.plot([], [])
    resp_line, = ax_resp.plot([], [])
    status_line, = ax_status.plot([], [])
    peak_line = CountingLine()
    app = SimpleNamespace(
        review_ecg_line=ecg_line,
        review_peak_line=peak_line,
        review_resp_line=resp_line,
        review_status_line=status_line,
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
        ax_review_status=ax_status,
        ax_pqrst=ax_pqrst,
        ecg_paper_grid_cache={},
        review_calibration_artists=[],
        calibration_pulse_cache={},
        review_canvas=FakeCanvas(),
        pqrst_canvas=FakeCanvas(),
    )
    frame = SimpleNamespace(
        mode="raw, display-smoothed",
        plot_ecg_x=np.array([0.0, 1.0, 2.0]),
        plot_ecg=np.array([0.0, 2.0, 0.0]),
        plot_resp_x=np.array([0.0, 1.0, 2.0]),
        plot_resp=np.array([10.0, 11.0, 12.0]),
        plot_status_x=np.array([0.0, 1.0, 2.0]),
        plot_status=np.array([0.0, 1.0, 1.0]),
        peak_x=np.array([1.0]),
        peak_y=np.array([2.0]),
        x_right=2.0,
        ecg_ylim=(-3.0, 3.0),
        resp_ylim=(8.0, 14.0),
        status_ylim=(-0.5, 1.5),
        review=SimpleNamespace(
            heart_rate=HeartRateSummary(72.0, 0.0, 0.0, 1),
            peaks=(1,),
        ),
        pqrst=PqrstReview(
            qrs_clear=True,
            p_tentative=True,
            t_tentative=True,
            beats_used=2,
            average_beat=(0.0, 1.0, 0.0),
            time_ms=(-10.0, 0.0, 10.0),
        ),
    )

    for _ in range(2):
        apply_review_render_frame(
            app,
            frame,
            display_settings=EcgDisplaySettings(time_window_seconds=8.0),
            ecg_label="CH2 ECG Lead I",
            resp_label="CH1 respiration",
            ecg_inverted=False,
        )

    assert peak_line.set_data_calls == 1


def _make_review_overlay_app() -> SimpleNamespace:
    fig = Figure()
    ax_ecg = fig.add_subplot(211)
    ax_resp = fig.add_subplot(212)
    ax_ecg.plot([], [])
    return SimpleNamespace(
        ax_review_ecg=ax_ecg,
        ax_review_resp=ax_resp,
        review_event_overlay_artists=[],
        review_event_overlay_key=None,
    )


def test_apply_event_overlay_artists_draws_spans_lines_and_labels() -> None:
    from ads1292_studio.event_overlay import build_event_overlay_items, event_overlay_key
    from ads1292_studio.events import EventMarker, event_from_interval
    from ads1292_studio.gui_plots import apply_event_overlay_artists

    app = _make_review_overlay_app()
    events = (
        event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion"),
        EventMarker(timestamp_seconds=4.0, label="touch"),
    )
    items = build_event_overlay_items(events, x_max_seconds=30.0)
    key = event_overlay_key(events, x_max_seconds=30.0)

    changed = apply_event_overlay_artists(app, items, key=key)

    assert changed is True
    # 1 interval span + 1 point line on each visible signal axis, plus 2 labels on ECG.
    assert len(app.review_event_overlay_artists) == 2 + 2 + 2
    assert app.review_event_overlay_key == key
    # The interval span landed on every shared-x axis.
    assert len(app.ax_review_ecg.patches) == 1
    assert len(app.ax_review_resp.patches) == 1


def test_apply_event_overlay_artists_skips_when_key_unchanged() -> None:
    from ads1292_studio.event_overlay import build_event_overlay_items, event_overlay_key
    from ads1292_studio.events import EventMarker
    from ads1292_studio.gui_plots import apply_event_overlay_artists

    app = _make_review_overlay_app()
    events = (EventMarker(timestamp_seconds=4.0, label="touch"),)
    items = build_event_overlay_items(events, x_max_seconds=30.0)
    key = event_overlay_key(events, x_max_seconds=30.0)

    apply_event_overlay_artists(app, items, key=key)
    artists_after_first = list(app.review_event_overlay_artists)

    changed = apply_event_overlay_artists(app, items, key=key)

    assert changed is False
    assert app.review_event_overlay_artists == artists_after_first


def test_apply_event_overlay_artists_replaces_artists_when_key_changes() -> None:
    from ads1292_studio.event_overlay import build_event_overlay_items, event_overlay_key
    from ads1292_studio.events import EventMarker, event_from_interval
    from ads1292_studio.gui_plots import apply_event_overlay_artists

    app = _make_review_overlay_app()
    first_events = (EventMarker(timestamp_seconds=4.0, label="touch"),)
    first_items = build_event_overlay_items(first_events, x_max_seconds=30.0)
    first_key = event_overlay_key(first_events, x_max_seconds=30.0)
    apply_event_overlay_artists(app, first_items, key=first_key)
    old_artists = list(app.review_event_overlay_artists)

    second_events = (*first_events, event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion"))
    second_items = build_event_overlay_items(second_events, x_max_seconds=30.0)
    second_key = event_overlay_key(second_events, x_max_seconds=30.0)

    changed = apply_event_overlay_artists(app, second_items, key=second_key)

    assert changed is True
    assert all(artist.axes is None for artist in old_artists)
    assert app.review_event_overlay_key == second_key


def _make_live_overlay_app() -> SimpleNamespace:
    fig = Figure()
    ax_ecg = fig.add_subplot(211)
    ax_resp = fig.add_subplot(212)
    ax_ecg.plot([], [])
    return SimpleNamespace(
        ax_live_ecg=ax_ecg,
        ax_live_resp=ax_resp,
        live_event_overlay_artists=[],
        live_event_overlay_key=None,
    )


def test_apply_live_event_overlay_artists_draws_on_live_axes() -> None:
    from ads1292_studio.event_overlay import build_event_overlay_items
    from ads1292_studio.events import EventMarker, event_from_interval
    from ads1292_studio.gui_plots import apply_live_event_overlay_artists

    app = _make_live_overlay_app()
    events = (
        event_from_interval(start_seconds=10.0, end_seconds=20.0, label="motion"),
        EventMarker(timestamp_seconds=4.0, label="touch"),
    )
    items = build_event_overlay_items(events, x_max_seconds=30.0)
    key = ("live", 2)

    changed = apply_live_event_overlay_artists(app, items, key=key)

    assert changed is True
    assert len(app.live_event_overlay_artists) == 2 + 2 + 2
    assert app.live_event_overlay_key == key
    assert len(app.ax_live_ecg.patches) == 1
    assert len(app.ax_live_resp.patches) == 1


def test_apply_live_event_overlay_artists_is_changed_only() -> None:
    from ads1292_studio.event_overlay import build_event_overlay_items
    from ads1292_studio.events import EventMarker
    from ads1292_studio.gui_plots import apply_live_event_overlay_artists

    app = _make_live_overlay_app()
    items = build_event_overlay_items((EventMarker(timestamp_seconds=4.0, label="touch"),), x_max_seconds=30.0)
    key = ("live", 1)

    apply_live_event_overlay_artists(app, items, key=key)
    artists_after_first = list(app.live_event_overlay_artists)
    changed = apply_live_event_overlay_artists(app, items, key=key)

    assert changed is False
    assert app.live_event_overlay_artists == artists_after_first


def test_apply_live_event_overlay_artists_clears_on_empty() -> None:
    from ads1292_studio.event_overlay import build_event_overlay_items
    from ads1292_studio.events import EventMarker
    from ads1292_studio.gui_plots import apply_live_event_overlay_artists

    app = _make_live_overlay_app()
    items = build_event_overlay_items((EventMarker(timestamp_seconds=4.0, label="touch"),), x_max_seconds=30.0)
    apply_live_event_overlay_artists(app, items, key=("live", 1))
    old_artists = list(app.live_event_overlay_artists)

    changed = apply_live_event_overlay_artists(app, (), key=("live", 0))

    assert changed is True
    assert app.live_event_overlay_artists == []
    assert all(artist.axes is None for artist in old_artists)
