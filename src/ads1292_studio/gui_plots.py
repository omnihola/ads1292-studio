from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import seaborn as sns

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
    scrollbar_chrome_spec,
    status_axis_spec,
)
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
            ax.spines[side].set_color(style["spine"])
            ax.spines[side].set_linewidth(style["spine_linewidth"])


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


def show_empty_plot_state(artists: list[object], key: str, axes: tuple[object, ...]) -> None:
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
