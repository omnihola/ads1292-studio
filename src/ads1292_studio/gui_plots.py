from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from typing import Any

from ads1292_studio.matplotlib_runtime import configure_matplotlib_cache

configure_matplotlib_cache()

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import numpy as np
import seaborn as sns

from ads1292_studio.display import (
    EcgDisplaySettings,
    SoftwareFilterSettings,
    display_mode_label,
    ecg_paper_grid_key,
    ecg_paper_grid_spec,
)
from ads1292_studio.gui_state import (
    display_scale_reference_label,
    live_axis_titles,
    set_axis_xlim_if_changed,
    set_axis_ylim_if_changed,
)
from ads1292_studio.gui_specs import (
    empty_plot_messages,
    empty_plot_style,
    live_axis_spec,
    log_panel_spec,
    plot_axis_style,
    plot_canvas_widget_style,
    plot_figure_layouts,
    plot_panel_spec,
    plot_trace_styles,
    pqrst_plot_style,
    scrollbar_chrome_spec,
    status_axis_spec,
)
from ads1292_studio.event_overlay import (
    EVENT_INTERVAL_ALPHA,
    EVENT_INTERVAL_COLOR,
    EVENT_LABEL_Y,
    EVENT_POINT_ALPHA,
    EVENT_POINT_COLOR,
    EventOverlayItem,
)
from ads1292_studio.live_render import LiveRenderFrame
from ads1292_studio.models import PqrstReview
from ads1292_studio.plots import robust_ylim, stable_ylim
from ads1292_studio.plot_theme import APP_VISUAL_TOKENS, PLOT_TRACE_COLORS, apply_seaborn_plot_theme
from ads1292_studio.review_render import ReviewRenderFrame
from ads1292_studio.spectrum import SpectrumAnalysis


@dataclass(frozen=True)
class PendingReviewPlot:
    frame: ReviewRenderFrame
    display_settings: EcgDisplaySettings
    ecg_label: str
    resp_label: str
    contact_label: str
    ecg_inverted: bool


def build_live_plot_panel(app: Any) -> None:
    fig = new_plot_figure(figsize=(10, 7))
    fig.subplots_adjust(**plot_figure_layouts()["three_panel"])
    app.ax_live_ecg = fig.add_subplot(311)
    app.ax_live_resp = fig.add_subplot(312, sharex=app.ax_live_ecg)
    app.ax_live_status = fig.add_subplot(313, sharex=app.ax_live_ecg)
    for ax in (app.ax_live_ecg, app.ax_live_resp, app.ax_live_status):
        ax.label_outer()
    style_signal_axes((app.ax_live_ecg, app.ax_live_resp, app.ax_live_status))
    configure_status_axes((app.ax_live_status,))
    add_signal_reference_lines((app.ax_live_ecg, app.ax_live_resp))
    app.ax_live_ecg.set_ylabel("display counts")
    app.ax_live_resp.set_ylabel("counts")
    app.ax_live_status.set_xlabel("Time (s)")
    configure_live_time_axis((app.ax_live_ecg, app.ax_live_resp, app.ax_live_status))
    configure_initial_ecg_paper_grid((app.ax_live_ecg,))
    trace_styles = plot_trace_styles()
    app.live_ecg_line, = app.ax_live_ecg.plot([], [], color=PLOT_TRACE_COLORS["ecg"], **trace_styles["ecg"])
    app.live_peak_line, = app.ax_live_ecg.plot([], [], color=PLOT_TRACE_COLORS["peak"], **trace_styles["peak"])
    app.live_resp_line, = app.ax_live_resp.plot(
        [],
        [],
        color=PLOT_TRACE_COLORS["respiration"],
        **trace_styles["respiration"],
    )
    app.live_status_line, = app.ax_live_status.plot(
        [],
        [],
        color=PLOT_TRACE_COLORS["contact"],
        **trace_styles["contact"],
    )
    show_empty_plot_state(app.empty_plot_artists, "live", (app.ax_live_ecg, app.ax_live_resp, app.ax_live_status))
    app.live_canvas = build_plot_canvas(app, app.live_tab, fig, name="live")


def build_review_plot_panel(app: Any) -> None:
    fig = new_plot_figure(figsize=(10, 7))
    fig.subplots_adjust(**plot_figure_layouts()["three_panel"])
    app.ax_review_ecg = fig.add_subplot(311)
    app.ax_review_resp = fig.add_subplot(312, sharex=app.ax_review_ecg)
    app.ax_review_status = fig.add_subplot(313, sharex=app.ax_review_ecg)
    for ax in (app.ax_review_ecg, app.ax_review_resp, app.ax_review_status):
        ax.label_outer()
    style_signal_axes((app.ax_review_ecg, app.ax_review_resp, app.ax_review_status))
    configure_status_axes((app.ax_review_status,))
    configure_initial_ecg_paper_grid((app.ax_review_ecg,))
    add_signal_reference_lines((app.ax_review_ecg, app.ax_review_resp))
    app.ax_review_status.set_xlabel("Time (s)")
    app.ax_review_ecg.set_ylabel("display counts")
    app.ax_review_resp.set_ylabel("counts")
    trace_styles = plot_trace_styles()
    app.review_ecg_line, = app.ax_review_ecg.plot([], [], color=PLOT_TRACE_COLORS["ecg"], **trace_styles["ecg"])
    app.review_peak_line, = app.ax_review_ecg.plot([], [], color=PLOT_TRACE_COLORS["peak"], **trace_styles["peak"])
    app.review_resp_line, = app.ax_review_resp.plot(
        [],
        [],
        color=PLOT_TRACE_COLORS["respiration"],
        **trace_styles["respiration"],
    )
    app.review_status_line, = app.ax_review_status.plot(
        [],
        [],
        color=PLOT_TRACE_COLORS["contact"],
        **trace_styles["contact"],
    )
    show_empty_plot_state(
        app.empty_plot_artists,
        "review",
        (app.ax_review_ecg, app.ax_review_resp, app.ax_review_status),
    )
    app.review_canvas = build_plot_canvas(app, app.review_tab, fig, name="review")


def build_pqrst_plot_panel(app: Any) -> None:
    fig = new_plot_figure(figsize=(10, 6))
    fig.subplots_adjust(**plot_figure_layouts()["single_panel"])
    app.ax_pqrst = fig.add_subplot(111)
    style_signal_axes((app.ax_pqrst,))
    app.ax_pqrst.set_xlabel("Time relative to R peak (ms)")
    app.ax_pqrst.set_ylabel("Filtered counts")
    show_empty_plot_state(app.empty_plot_artists, "pqrst", (app.ax_pqrst,))
    app.pqrst_canvas = build_plot_canvas(app, app.pqrst_tab, fig, name="pqrst")


def build_spectrum_plot_panel(app: Any) -> None:
    fig = new_plot_figure(figsize=(10, 6))
    fig.subplots_adjust(**plot_figure_layouts()["two_panel"])
    app.ax_spectrum_fft = fig.add_subplot(211)
    app.ax_spectrum_hist = fig.add_subplot(212)
    style_signal_axes((app.ax_spectrum_fft, app.ax_spectrum_hist))
    app.ax_spectrum_fft.set_xlabel("Frequency (Hz)")
    app.ax_spectrum_fft.set_ylabel("Power")
    app.ax_spectrum_hist.set_xlabel("Raw counts")
    app.ax_spectrum_hist.set_ylabel("Samples")
    show_empty_plot_state(app.empty_plot_artists, "spectrum", (app.ax_spectrum_fft, app.ax_spectrum_hist))
    app.spectrum_canvas = build_plot_canvas(app, app.spectrum_tab, fig, name="spectrum")


def apply_live_render_frame(
    app: Any,
    frame: LiveRenderFrame,
    *,
    display_settings: EcgDisplaySettings,
    autoscale: bool,
    min_ecg_span_counts: float,
    min_resp_span_counts: float,
) -> None:
    restored_axis_chrome = restore_data_axis_chrome((app.ax_live_ecg, app.ax_live_resp, app.ax_live_status))
    trace_changed = (
        set_line_data_if_changed(app.live_ecg_line, frame.plot_ecg_x, frame.plot_ecg),
        set_line_data_if_changed(app.live_peak_line, frame.peaks_x, frame.peaks_y),
        set_line_visible_if_changed(app.live_peak_line, bool(frame.peaks)),
        set_line_data_if_changed(app.live_resp_line, frame.plot_resp_x, frame.plot_resp),
        set_line_data_if_changed(app.live_status_line, frame.plot_status_x, frame.plot_status),
        set_line_color_if_changed(app.live_status_line, live_contact_trace_color(frame.visible_status)),
    )
    xlim_changed = (
        set_axis_xlim_if_changed(app.ax_live_ecg, (frame.left, frame.right)),
        set_axis_xlim_if_changed(app.ax_live_resp, (frame.left, frame.right)),
        set_axis_xlim_if_changed(app.ax_live_status, (frame.left, frame.right)),
    )
    ylim_changed: tuple[bool, ...] = tuple()
    if autoscale:
        ecg_ylim = robust_ylim(frame.visible_ecg_plot, min_span=min_ecg_span_counts * display_settings.gain)
        resp_ylim = robust_ylim(frame.visible_resp_plot, min_span=min_resp_span_counts)
        status_top = float(frame.visible_status.max()) + 0.5 if frame.visible_status.size else 1.0
        ylim_changed = (
            set_axis_ylim_if_changed(app.ax_live_ecg, stable_ylim(app.ax_live_ecg.get_ylim(), ecg_ylim)),
            set_axis_ylim_if_changed(app.ax_live_resp, stable_ylim(app.ax_live_resp.get_ylim(), resp_ylim)),
            set_axis_ylim_if_changed(app.ax_live_status, (-0.5, max(1.0, status_top))),
        )
    grid_changed = apply_ecg_paper_grid(app.ax_live_ecg, display_settings, app.ecg_paper_grid_cache)
    calibration_changed = restored_axis_chrome or calibration_pulse_needs_update(
        app.ax_live_ecg,
        app.live_calibration_artists,
        display_settings,
        app.calibration_pulse_cache,
    )
    if calibration_changed:
        draw_calibration_pulse(
            app.ax_live_ecg,
            app.live_calibration_artists,
            display_settings,
            app.calibration_pulse_cache,
        )
    if any((*trace_changed, *xlim_changed, *ylim_changed, grid_changed, calibration_changed)):
        draw_canvas_idle_if_visible(app.live_canvas, getattr(app, "live_tab", None))


def draw_canvas_idle_if_visible(canvas: object, owner: object | None = None) -> bool:
    if not widget_is_visible(owner):
        return False
    canvas.draw_idle()
    return True


def widget_is_visible(owner: object | None = None) -> bool:
    if owner is None:
        return True
    try:
        return not hasattr(owner, "winfo_ismapped") or bool(owner.winfo_ismapped())
    except tk.TclError:
        return False


def live_contact_trace_color(status_values: np.ndarray) -> str:
    if status_values.size and np.any(status_values != 0.0):
        return APP_VISUAL_TOKENS["warning"]
    return PLOT_TRACE_COLORS["contact"]


def set_line_color_if_changed(line: object, color: str) -> bool:
    if line.get_color() == color:
        return False
    line.set_color(color)
    return True


def set_line_visible_if_changed(line: object, visible: bool) -> bool:
    if bool(line.get_visible()) == bool(visible):
        return False
    line.set_visible(bool(visible))
    return True


def set_line_data_if_changed(line: object, x: np.ndarray, y: np.ndarray) -> bool:
    x_unchanged = np.array_equal(np.asarray(line.get_xdata()), x)
    y_unchanged = np.array_equal(np.asarray(line.get_ydata()), y)
    if x_unchanged and y_unchanged:
        return False
    line.set_data(x, y)
    return True


def apply_live_axis_titles(
    app: Any,
    display_settings: EcgDisplaySettings,
    filter_settings: SoftwareFilterSettings,
    *,
    ecg_label: str,
    resp_label: str,
    contact_label: str,
    ecg_inverted: bool,
) -> None:
    mode = f"{display_mode_label(display_settings, filter_settings)}, display-smoothed"
    titles = live_axis_titles(
        ecg_label=ecg_label,
        resp_label=resp_label,
        contact_label=contact_label,
        mode=mode,
        inverted=ecg_inverted,
    )
    if app.last_live_axis_titles == titles:
        return
    app.last_live_axis_titles = titles
    ecg_title, resp_title, contact_title = titles
    set_signal_axis_title(app.ax_live_ecg, ecg_title)
    set_signal_axis_title(app.ax_live_resp, resp_title)
    set_signal_axis_title(app.ax_live_status, contact_title)


def apply_review_render_frame(
    app: Any,
    frame: ReviewRenderFrame,
    *,
    display_settings: EcgDisplaySettings,
    ecg_label: str,
    resp_label: str,
    contact_label: str,
    ecg_inverted: bool,
    force_visible: bool = False,
) -> None:
    if not force_visible and not widget_is_visible(getattr(app, "review_tab", None)):
        app.pending_review_plot = PendingReviewPlot(
            frame=frame,
            display_settings=display_settings,
            ecg_label=ecg_label,
            resp_label=resp_label,
            contact_label=contact_label,
            ecg_inverted=ecg_inverted,
        )
        draw_pqrst_review_if_changed(app, frame.pqrst)
        return
    app.pending_review_plot = None
    review_owner = None if force_visible else getattr(app, "review_tab", None)
    restored_axis_chrome = restore_data_axis_chrome((app.ax_review_ecg, app.ax_review_resp, app.ax_review_status))
    trace_changed = (
        set_line_data_if_changed(app.review_ecg_line, frame.plot_ecg_x, frame.plot_ecg),
        set_line_data_if_changed(app.review_resp_line, frame.plot_resp_x, frame.plot_resp),
        set_line_data_if_changed(app.review_status_line, frame.plot_status_x, frame.plot_status),
        set_line_data_if_changed(app.review_peak_line, frame.peak_x, frame.peak_y),
    )
    polarity = ", inverted" if ecg_inverted else ""
    set_signal_axis_title(
        app.ax_review_ecg,
        f"Offline ECG: {ecg_label} | {frame.mode}{polarity} | "
        f"HR {frame.review.heart_rate.median_bpm:.1f} bpm | peaks {len(frame.review.peaks)}",
    )
    set_signal_axis_title(app.ax_review_resp, resp_label)
    set_signal_axis_title(app.ax_review_status, contact_label)
    axis_changed = (
        set_axis_xlim_if_changed(app.ax_review_ecg, (0, frame.x_right)),
        set_axis_ylim_if_changed(app.ax_review_ecg, frame.ecg_ylim),
        set_axis_xlim_if_changed(app.ax_review_resp, (0, frame.x_right)),
        set_axis_ylim_if_changed(app.ax_review_resp, frame.resp_ylim),
        set_axis_xlim_if_changed(app.ax_review_status, (0, frame.x_right)),
        set_axis_ylim_if_changed(app.ax_review_status, frame.status_ylim),
    )
    label_changed = set_axis_xlabel_if_changed(app.ax_review_status, "Time (s)")
    grid_changed = apply_ecg_paper_grid(app.ax_review_ecg, display_settings, app.ecg_paper_grid_cache)
    calibration_changed = restored_axis_chrome or calibration_pulse_needs_update(
        app.ax_review_ecg,
        app.review_calibration_artists,
        display_settings,
        app.calibration_pulse_cache,
    )
    if calibration_changed:
        draw_calibration_pulse(
            app.ax_review_ecg,
            app.review_calibration_artists,
            display_settings,
            app.calibration_pulse_cache,
        )
    if any((*trace_changed, *axis_changed, label_changed, grid_changed, calibration_changed)):
        draw_canvas_idle_if_visible(app.review_canvas, review_owner)
    draw_pqrst_review_if_changed(app, frame.pqrst)


def _draw_event_overlay(
    axes: tuple,
    label_axis: object,
    items: tuple[EventOverlayItem, ...],
    prior_artists: list,
) -> list:
    """Replace ``prior_artists`` with span/line/label artists for ``items``.

    Interval annotations become shaded spans and point annotations become dashed
    vertical lines across every supplied axis so an annotated window is visible
    across each signal at once; the text label is placed once on ``label_axis``.
    Artists live in data coordinates, so a rolling x-axis scrolls them for free.
    """
    for artist in prior_artists:
        artist.remove()
    new_artists: list = []
    for item in items:
        if item.is_interval:
            for axis in axes:
                new_artists.append(
                    axis.axvspan(
                        item.start_seconds,
                        item.end_seconds,
                        color=EVENT_INTERVAL_COLOR,
                        alpha=EVENT_INTERVAL_ALPHA,
                        linewidth=0,
                    )
                )
        else:
            for axis in axes:
                new_artists.append(
                    axis.axvline(
                        item.start_seconds,
                        color=EVENT_POINT_COLOR,
                        alpha=EVENT_POINT_ALPHA,
                        linewidth=1.0,
                        linestyle="--",
                    )
                )
        new_artists.append(
            label_axis.text(
                item.label_x,
                EVENT_LABEL_Y,
                item.label,
                transform=label_axis.get_xaxis_transform(),
                ha="center",
                va="top",
                fontsize=8,
                color=EVENT_POINT_COLOR,
                rotation=0,
            )
        )
    return new_artists


def apply_event_overlay_artists(
    app: Any,
    items: tuple[EventOverlayItem, ...],
    *,
    key: tuple,
) -> bool:
    """Draw event annotations on the shared-x offline review axes (changed-only).

    Returns ``True`` when the overlay was rebuilt, ``False`` when the cached key
    matched and nothing was touched.
    """
    if getattr(app, "review_event_overlay_key", None) == key:
        return False
    app.review_event_overlay_artists = _draw_event_overlay(
        (app.ax_review_ecg, app.ax_review_resp, app.ax_review_status),
        app.ax_review_ecg,
        items,
        getattr(app, "review_event_overlay_artists", []),
    )
    app.review_event_overlay_key = key
    return True


def apply_live_event_overlay_artists(
    app: Any,
    items: tuple[EventOverlayItem, ...],
    *,
    key: tuple,
) -> bool:
    """Draw event annotations on the shared-x live axes (changed-only).

    Artists are placed in data coordinates, so they scroll with the rolling live
    window for free as the x-limits advance each frame; the overlay is only
    rebuilt when the annotation set changes, never per render frame.
    """
    if getattr(app, "live_event_overlay_key", None) == key:
        return False
    app.live_event_overlay_artists = _draw_event_overlay(
        (app.ax_live_ecg, app.ax_live_resp, app.ax_live_status),
        app.ax_live_ecg,
        items,
        getattr(app, "live_event_overlay_artists", []),
    )
    app.live_event_overlay_key = key
    return True


def flush_pending_review_render(app: Any, *, force: bool = False) -> bool:
    pending = getattr(app, "pending_review_plot", None)
    if pending is None or (not force and not widget_is_visible(getattr(app, "review_tab", None))):
        return False
    app.pending_review_plot = None
    apply_review_render_frame(
        app,
        pending.frame,
        display_settings=pending.display_settings,
        ecg_label=pending.ecg_label,
        resp_label=pending.resp_label,
        contact_label=pending.contact_label,
        ecg_inverted=pending.ecg_inverted,
        force_visible=force,
    )
    return True


def draw_pqrst_review_if_changed(app: Any, review: PqrstReview, *, force_visible: bool = False) -> bool:
    if getattr(app, "last_pqrst_review", None) == review and getattr(app, "pending_pqrst_review", None) is None:
        return False
    owner = getattr(app, "pqrst_tab", None)
    if not force_visible and not widget_is_visible(owner):
        if getattr(app, "last_pqrst_review", None) != review:
            app.pending_pqrst_review = review
        return False
    app.pending_pqrst_review = None
    if getattr(app, "last_pqrst_review", None) == review:
        return False
    app.last_pqrst_review = review
    draw_pqrst_review(app.ax_pqrst, app.pqrst_canvas, review, owner=None if force_visible else owner)
    return True


def flush_pending_pqrst_review(app: Any, *, force: bool = False) -> bool:
    review = getattr(app, "pending_pqrst_review", None)
    if review is None or (not force and not widget_is_visible(getattr(app, "pqrst_tab", None))):
        return False
    return draw_pqrst_review_if_changed(app, review, force_visible=force)


def draw_pqrst_review(ax: object, canvas: object, review: PqrstReview, *, owner: object | None = None) -> None:
    ax.clear()
    style_signal_axes((ax,))
    ax.set_xlabel("Time relative to R peak (ms)")
    ax.set_ylabel("Filtered counts")
    if review.average_beat:
        pqrst_style = pqrst_plot_style()
        ax.plot(
            review.time_ms,
            review.average_beat,
            color=PLOT_TRACE_COLORS["ecg"],
            **pqrst_style["average"],
        )
        ax.axvline(
            0,
            color=PLOT_TRACE_COLORS["peak"],
            **pqrst_style["r_marker"],
        )
        p_search = pqrst_style["p_search"]
        ax.axvspan(
            p_search["start_ms"],
            p_search["end_ms"],
            color=p_search["color"],
            alpha=p_search["alpha"],
            label=p_search["label"],
        )
        t_search = pqrst_style["t_search"]
        ax.axvspan(
            t_search["start_ms"],
            t_search["end_ms"],
            color=t_search["color"],
            alpha=t_search["alpha"],
            label=t_search["label"],
        )
        ax.legend(**pqrst_style["legend"])
    set_signal_axis_title(
        ax,
        f"PQRST review: QRS={review.qrs_clear}, P tentative={review.p_tentative}, "
        f"T tentative={review.t_tentative}, beats={review.beats_used}",
    )
    draw_canvas_idle_if_visible(canvas, owner)


def draw_spectrum_analysis(
    ax_fft: object,
    ax_hist: object,
    canvas: object,
    analysis: SpectrumAnalysis,
    *,
    owner: object | None = None,
) -> None:
    for ax in (ax_fft, ax_hist):
        ax.clear()
    style_signal_axes((ax_fft, ax_hist))
    trace_styles = plot_trace_styles()
    if analysis.ecg_frequency_hz.size:
        ax_fft.plot(
            analysis.ecg_frequency_hz,
            analysis.ecg_power,
            color=PLOT_TRACE_COLORS["ecg"],
            **trace_styles["ecg"],
        )
    if analysis.histogram_counts.size:
        widths = np.diff(analysis.histogram_bin_edges)
        ax_hist.bar(
            analysis.histogram_bin_edges[:-1],
            analysis.histogram_counts,
            width=widths,
            align="edge",
            color=PLOT_TRACE_COLORS["respiration"],
            alpha=0.72,
            linewidth=0,
        )
    set_signal_axis_title(ax_fft, f"FFT spectrum: {analysis.ecg_label}")
    set_signal_axis_title(ax_hist, f"Amplitude histogram: {analysis.ecg_label} raw counts")
    ax_fft.set_xlabel("Frequency (Hz)")
    ax_fft.set_ylabel("Power")
    ax_hist.set_xlabel("Raw counts")
    ax_hist.set_ylabel("Samples")
    draw_canvas_idle_if_visible(canvas, owner)


def build_plot_canvas(app: Any, parent: ttk.Frame, fig: Figure, *, name: str) -> FigureCanvasTkAgg:
    spec = plot_panel_spec()
    shell = ttk.Frame(parent, padding=spec["padding"], style=str(spec["shell"]))
    shell.pack(fill=tk.BOTH, expand=True)
    panel = ttk.Frame(shell, padding=spec["panel_padding"], style=str(spec["panel"]))
    panel.pack(fill=tk.BOTH, expand=True)
    setattr(app, f"{name}_plot_shell", shell)
    setattr(app, f"{name}_plot_panel", panel)
    canvas = FigureCanvasTkAgg(fig, master=panel)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.configure(**plot_canvas_widget_style())
    canvas_widget.pack(fill=tk.BOTH, expand=True)
    return canvas


def build_log_panel(app: Any) -> None:
    spec = log_panel_spec()
    shell = ttk.Frame(app.log_tab, padding=spec["padding"], style=str(spec["shell"]))
    shell.pack(fill=tk.BOTH, expand=True)
    panel = ttk.Frame(shell, padding=spec["panel_padding"], style=str(spec["panel"]))
    panel.pack(fill=tk.BOTH, expand=True)
    app.log_shell = shell
    app.log_panel = panel
    scrollbar_spec = scrollbar_chrome_spec()
    ttk.Label(panel, text="Event annotations", style="SectionHeading.TLabel").pack(anchor=tk.W)
    event_frame = ttk.Frame(panel, style=str(spec["panel"]))
    event_frame.pack(fill=tk.BOTH, expand=False, pady=(4, 10))
    app.event_log_scrollbar = ttk.Scrollbar(
        event_frame,
        orient=str(spec["scrollbar"]),
        style=str(scrollbar_spec["vertical"]),
    )
    app.log_scrollbar = ttk.Scrollbar(panel, orient=str(spec["scrollbar"]), style=str(scrollbar_spec["vertical"]))
    text_padding = spec["text_padding"]
    app.event_log_text = tk.Text(
        event_frame,
        height=8,
        bg=str(spec["background"]),
        fg=str(spec["foreground"]),
        insertbackground=str(spec["insert"]),
        selectbackground=str(spec["select_background"]),
        selectforeground=str(spec["select_foreground"]),
        borderwidth=int(spec["borderwidth"]),
        highlightthickness=int(spec["highlightthickness"]),
        relief=str(spec["relief"]),
        padx=text_padding[0],
        pady=text_padding[1],
        spacing1=spec["spacing"][0],
        spacing3=spec["spacing"][1],
        wrap=str(spec["wrap"]),
        font=spec["font"],
        yscrollcommand=app.event_log_scrollbar.set,
    )
    app.event_log_scrollbar.configure(command=app.event_log_text.yview)
    app.event_log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    app.event_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Label(panel, text="Runtime log", style="SectionHeading.TLabel").pack(anchor=tk.W)
    app.log_text = tk.Text(
        panel,
        height=int(spec["height"]),
        bg=str(spec["background"]),
        fg=str(spec["foreground"]),
        insertbackground=str(spec["insert"]),
        selectbackground=str(spec["select_background"]),
        selectforeground=str(spec["select_foreground"]),
        borderwidth=int(spec["borderwidth"]),
        highlightthickness=int(spec["highlightthickness"]),
        relief=str(spec["relief"]),
        padx=text_padding[0],
        pady=text_padding[1],
        spacing1=spec["spacing"][0],
        spacing3=spec["spacing"][1],
        wrap=str(spec["wrap"]),
        font=spec["font"],
        yscrollcommand=app.log_scrollbar.set,
    )
    app.log_scrollbar.configure(command=app.log_text.yview)
    app.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    app.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


def new_plot_figure(*, figsize: tuple[float, float]) -> Figure:
    apply_seaborn_plot_theme()
    fig = Figure(figsize=figsize, dpi=100)
    fig.patch.set_facecolor(APP_VISUAL_TOKENS["surface"])
    return fig


def style_signal_axes(axes: tuple[object, ...]) -> None:
    style = plot_axis_style()
    for ax in axes:
        ax.set_facecolor(style["face"])
        ax.set_axisbelow(style["axisbelow"])
        ax.grid(True, color=style["grid"], linewidth=style["grid_linewidth"], alpha=style["grid_alpha"])
        ax.tick_params(
            colors=style["tick"],
            direction=style["tick_direction"],
            labelsize=style["tick_label_size"],
            length=style["tick_length"],
            width=style["tick_width"],
        )
        ax.xaxis.label.set_size(style["label_size"])
        ax.yaxis.label.set_size(style["label_size"])
        ax.xaxis.labelpad = style["label_pad"]
        ax.yaxis.labelpad = style["label_pad"]
        ax.xaxis.label.set_color(style["label"])
        ax.yaxis.label.set_color(style["label"])
        set_signal_axis_title(ax, ax.get_title())
        sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
        for side in ("left", "bottom"):
            ax.spines[side].set_visible(True)
            ax.spines[side].set_color(style["spine"])
            ax.spines[side].set_linewidth(style["spine_linewidth"])


def restore_data_axis_chrome(axes: tuple[object, ...]) -> bool:
    if not any(bool(getattr(ax, "_ads1292_empty_axis_chrome", False)) for ax in axes):
        return False
    style_signal_axes(axes)
    for ax in axes:
        ax.xaxis.label.set_visible(True)
        ax.yaxis.label.set_visible(True)
        ax.title.set_visible(True)
        ax.tick_params(labelleft=True, labelbottom=True, left=True, bottom=True)
        for line in ax.lines:
            line.set_visible(True)
        setattr(ax, "_ads1292_empty_axis_chrome", False)
    for ax in axes:
        ax.label_outer()
    return True


def soften_empty_axis_chrome(axes: tuple[object, ...]) -> None:
    style = empty_plot_style()
    for ax in axes:
        ax.set_facecolor(str(style["axis_face"]))
        ax.grid(False, which="both")
        ax.tick_params(labelleft=False, labelbottom=False, left=False, bottom=False)
        ax.xaxis.label.set_visible(False)
        ax.yaxis.label.set_visible(False)
        ax.title.set_visible(False)
        for line in ax.lines:
            line.set_visible(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        setattr(ax, "_ads1292_empty_axis_chrome", True)


def set_signal_axis_title(ax: object, title: str) -> None:
    if ax.get_title() == title:
        return
    style = plot_axis_style()
    ax.set_title(
        title,
        color=style["title"],
        fontsize=style["title_size"],
        fontweight=style["title_weight"],
        pad=style["title_pad"],
    )


def set_axis_xlabel_if_changed(ax: object, label: str) -> bool:
    if ax.get_xlabel() == label:
        return False
    ax.set_xlabel(label)
    return True


def add_signal_reference_lines(axes: tuple[object, ...]) -> None:
    style = plot_axis_style()
    for ax in axes:
        ax.axhline(
            0,
            color=style["zero_line_color"],
            linewidth=style["zero_line_width"],
            linestyle=style["zero_line_style"],
            alpha=style["zero_line_alpha"],
            zorder=0,
        )


def configure_live_time_axis(axes: tuple[object, ...]) -> None:
    spec = live_axis_spec()
    for ax in axes:
        ax.xaxis.set_major_locator(MultipleLocator(float(spec["x_major_tick_seconds"])))


def configure_status_axes(axes: tuple[object, ...]) -> None:
    spec = status_axis_spec()
    for ax in axes:
        ax.yaxis.set_major_locator(MultipleLocator(float(spec["y_major_tick_bits"])))
        ax.set_ylabel(str(spec["ylabel"]))


def configure_initial_ecg_paper_grid(axes: tuple[object, ...]) -> None:
    settings = EcgDisplaySettings()
    cache: dict[int, tuple[float, float, float, float]] = {}
    for ax in axes:
        apply_ecg_paper_grid(ax, settings, cache=cache)


def apply_ecg_paper_grid(
    ax: object,
    settings: EcgDisplaySettings,
    cache: dict[int, tuple[float, float, float, float]],
) -> bool:
    spec = ecg_paper_grid_spec(settings)
    cache_key = ecg_paper_grid_key(settings, ax.get_ylim())
    axis_id = id(ax)
    if cache.get(axis_id) == cache_key:
        return False
    cache[axis_id] = cache_key
    ax.xaxis.set_major_locator(MultipleLocator(float(spec["major_x_seconds"])))
    ax.xaxis.set_minor_locator(MultipleLocator(float(spec["minor_x_seconds"])))
    _, _, major_y, minor_y = cache_key
    ax.yaxis.set_major_locator(MultipleLocator(major_y))
    ax.yaxis.set_minor_locator(MultipleLocator(minor_y))
    ax.grid(
        True,
        which="major",
        color=spec["major_color"],
        linewidth=spec["major_linewidth"],
        alpha=spec["major_alpha"],
    )
    ax.grid(
        True,
        which="minor",
        color=spec["minor_color"],
        linewidth=spec["minor_linewidth"],
        alpha=spec["minor_alpha"],
    )
    return True


def draw_calibration_pulse(
    ax: object,
    artists: list[object],
    settings: EcgDisplaySettings,
    cache: dict[int, str],
) -> None:
    axis_id = id(ax)
    label_text = display_scale_reference_label(settings)
    if artists and cache.get(axis_id) == label_text:
        return
    if len(artists) >= 2 and hasattr(artists[1], "set_text"):
        artists[1].set_text(label_text)
        cache[axis_id] = label_text
        return
    for artist in artists:
        artist.remove()
    artists.clear()
    line, = ax.plot(
        [0.025, 0.025, 0.07, 0.07, 0.105],
        [0.12, 0.30, 0.30, 0.12, 0.12],
        transform=ax.transAxes,
        color=PLOT_TRACE_COLORS["peak"],
        linewidth=1.25,
        solid_capstyle="butt",
        clip_on=False,
    )
    label = ax.text(
        0.115,
        0.30,
        label_text,
        transform=ax.transAxes,
        color=APP_VISUAL_TOKENS["muted"],
        fontsize=8,
        va="center",
        ha="left",
        clip_on=False,
    )
    artists.extend((line, label))
    cache[axis_id] = label_text


def calibration_pulse_needs_update(
    ax: object,
    artists: list[object],
    settings: EcgDisplaySettings,
    cache: dict[int, str],
) -> bool:
    if not artists:
        return True
    return cache.get(id(ax)) != display_scale_reference_label(settings)


def show_empty_plot_state(artists: list[object], key: str, axes: tuple[object, ...]) -> None:
    state_token = (key, tuple(id(ax) for ax in axes))
    if artists and all(getattr(ax, "_ads1292_empty_state_token", None) == state_token for ax in axes):
        return
    soften_empty_axis_chrome(axes)
    style = empty_plot_style()
    messages = empty_plot_messages()
    for ax, message in zip(axes, messages[key]):
        setattr(ax, "_ads1292_empty_state_token", state_token)
        guide = ax.axhline(
            0.5,
            color=str(style["guide_color"]),
            linewidth=float(style["guide_linewidth"]),
            alpha=float(style["guide_alpha"]),
            zorder=0,
        )
        artist = ax.text(
            0.5,
            0.5,
            message,
            transform=ax.transAxes,
            ha="center",
            va="center",
            color=str(style["text_color"]),
            fontsize=int(style["font_size"]),
            fontweight=str(style["font_weight"]),
            alpha=float(style["alpha"]),
            bbox={
                "boxstyle": f"round,pad={style['box_pad']},rounding_size={style['rounding']}",
                "facecolor": style["box_face"],
                "edgecolor": style["box_edge"],
                "linewidth": style["line_width"],
            },
        )
        artists.extend((guide, artist))
