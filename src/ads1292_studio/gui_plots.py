from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import seaborn as sns

from ads1292_studio.display import EcgDisplaySettings, ecg_paper_grid_key, ecg_paper_grid_spec
from ads1292_studio.gui_state import display_scale_reference_label, set_axis_xlim_if_changed, set_axis_ylim_if_changed
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
from ads1292_studio.live_render import LiveRenderFrame
from ads1292_studio.models import PqrstReview
from ads1292_studio.plots import robust_ylim, stable_ylim
from ads1292_studio.plot_theme import APP_VISUAL_TOKENS, PLOT_TRACE_COLORS, apply_seaborn_plot_theme


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


def apply_live_render_frame(
    app: Any,
    frame: LiveRenderFrame,
    *,
    display_settings: EcgDisplaySettings,
    autoscale: bool,
    min_ecg_span_counts: float,
    min_resp_span_counts: float,
) -> None:
    restore_data_axis_chrome((app.ax_live_ecg, app.ax_live_resp, app.ax_live_status))
    app.live_ecg_line.set_data(frame.plot_ecg_x, frame.plot_ecg)
    app.live_peak_line.set_data(frame.peaks_x, frame.peaks_y)
    app.live_resp_line.set_data(frame.plot_resp_x, frame.plot_resp)
    app.live_status_line.set_data(frame.plot_status_x, frame.plot_status)
    for ax in (app.ax_live_ecg, app.ax_live_resp, app.ax_live_status):
        set_axis_xlim_if_changed(ax, (frame.left, frame.right))
    if autoscale:
        ecg_ylim = robust_ylim(frame.visible_ecg_plot, min_span=min_ecg_span_counts * display_settings.gain)
        resp_ylim = robust_ylim(frame.visible_resp_plot, min_span=min_resp_span_counts)
        set_axis_ylim_if_changed(app.ax_live_ecg, stable_ylim(app.ax_live_ecg.get_ylim(), ecg_ylim))
        set_axis_ylim_if_changed(app.ax_live_resp, stable_ylim(app.ax_live_resp.get_ylim(), resp_ylim))
        status_top = float(frame.visible_status.max()) + 0.5 if frame.visible_status.size else 1.0
        set_axis_ylim_if_changed(app.ax_live_status, (-0.5, max(1.0, status_top)))
    apply_ecg_paper_grid(app.ax_live_ecg, display_settings, app.ecg_paper_grid_cache)
    draw_calibration_pulse(
        app.ax_live_ecg,
        app.live_calibration_artists,
        display_settings,
        app.calibration_pulse_cache,
    )
    app.live_canvas.draw_idle()


def draw_pqrst_review(ax: object, canvas: object, review: PqrstReview) -> None:
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
    canvas.draw_idle()


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
    app.log_scrollbar = ttk.Scrollbar(panel, orient=str(spec["scrollbar"]), style=str(scrollbar_spec["vertical"]))
    text_padding = spec["text_padding"]
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


def restore_data_axis_chrome(axes: tuple[object, ...]) -> None:
    if not any(bool(getattr(ax, "_ads1292_empty_axis_chrome", False)) for ax in axes):
        return
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


def soften_empty_axis_chrome(axes: tuple[object, ...]) -> None:
    for ax in axes:
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
) -> None:
    spec = ecg_paper_grid_spec(settings)
    cache_key = ecg_paper_grid_key(settings, ax.get_ylim())
    axis_id = id(ax)
    if cache.get(axis_id) == cache_key:
        return
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


def show_empty_plot_state(artists: list[object], key: str, axes: tuple[object, ...]) -> None:
    soften_empty_axis_chrome(axes)
    style = empty_plot_style()
    messages = empty_plot_messages()
    for ax, message in zip(axes, messages[key]):
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
        artists.append(artist)
