from types import SimpleNamespace

import numpy as np
from matplotlib.figure import Figure

from ads1292_studio.display import EcgDisplaySettings
from ads1292_studio.gui_plots import (
    apply_live_render_frame,
    apply_review_render_frame,
    calibration_pulse_needs_update,
    draw_calibration_pulse,
    draw_pqrst_review,
    live_contact_trace_color,
    restore_data_axis_chrome,
    set_line_data_if_changed,
    set_line_color_if_changed,
    set_line_visible_if_changed,
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
    assert ax.texts[-1].get_text() == "1 Select ADS1292 port"


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
    assert status_line.get_ydata().tolist() == [0.0, 2.0, 2.0]
    assert status_line.get_color() == APP_VISUAL_TOKENS["warning"]
    assert ax_ecg.get_xlim() == (1.0, 9.0)
    assert ax_resp.get_xlim() == (1.0, 9.0)
    assert ax_status.get_xlim() == (1.0, 9.0)
    assert ax_status.get_ylim() == (-0.5, 2.5)
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
    assert app.live_status_line.set_data_calls == 1
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
        contact_label="lead-off bits",
        ecg_inverted=False,
    )

    assert ecg_line.get_ydata().tolist() == [0.0, 2.0, 0.0]
    assert peak_line.get_xdata().tolist() == [1.0]
    assert resp_line.get_ydata().tolist() == [10.0, 11.0, 12.0]
    assert status_line.get_ydata().tolist() == [0.0, 1.0, 1.0]
    assert ax_ecg.get_xlim() == (0.0, 2.0)
    assert ax_ecg.get_ylim() == (-3.0, 3.0)
    assert ax_status.get_xlabel() == "Time (s)"
    assert "Offline ECG: CH2 ECG Lead I" in ax_ecg.get_title()
    assert review_canvas.draw_idle_calls == 1
    assert pqrst_canvas.draw_idle_calls == 1


def test_apply_review_render_frame_skips_unchanged_pqrst_redraw() -> None:
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
            contact_label="lead-off bits",
            ecg_inverted=False,
        )

    assert review_canvas.draw_idle_calls == 2
    assert pqrst_canvas.draw_idle_calls == 1


def test_apply_review_render_frame_skips_unchanged_peak_marker_writes() -> None:
    class CountingLine:
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
            contact_label="lead-off bits",
            ecg_inverted=False,
        )

    assert peak_line.set_data_calls == 1
