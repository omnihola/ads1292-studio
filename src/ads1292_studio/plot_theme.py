from __future__ import annotations

from ads1292_studio.matplotlib_runtime import configure_matplotlib_cache

configure_matplotlib_cache()

from matplotlib.figure import Figure
import seaborn as sns


APP_VISUAL_TOKENS = {
    "surface": "#F6F8FB",
    "panel": "#FFFFFF",
    "panel_alt": "#EEF3FA",
    "ink": "#172033",
    "muted": "#657084",
    "border": "#D9E1EC",
    "accent": "#2F6FED",
    "accent_dark": "#1F4FB2",
    "success": "#1E7A46",
    "warning": "#A76400",
    "danger": "#B3261E",
}
PLOT_TRACE_COLORS = {
    "ecg": "#0B6FA4",
    "respiration": "#7A5CDB",
    "contact": "#64748B",
    "peak": "#E4572E",
}
SEABORN_PLOT_THEME = {
    "style": "whitegrid",
    "context": "notebook",
    "palette": "colorblind",
    "rc": {
        "axes.facecolor": "#FFFFFF",
        "axes.edgecolor": "#D9E1EC",
        "axes.grid": True,
        "axes.labelcolor": "#293247",
        "axes.titlecolor": "#172033",
        "figure.facecolor": "#F6F8FB",
        "grid.color": "#D9E1EC",
        "grid.linewidth": 0.62,
        "agg.path.chunksize": 10000,
        "lines.antialiased": True,
        "path.simplify": True,
        "path.simplify_threshold": 0.18,
        "xtick.color": "#657084",
        "ytick.color": "#657084",
    },
}
PLOT_TRACE_STYLES = {
    "ecg": {"linewidth": 1.45, "alpha": 0.96, "antialiased": True, "solid_capstyle": "round", "solid_joinstyle": "round"},
    "respiration": {
        "linewidth": 1.0,
        "alpha": 0.86,
        "antialiased": True,
        "solid_capstyle": "round",
        "solid_joinstyle": "round",
    },
    "contact": {"linewidth": 1.0, "alpha": 0.88, "drawstyle": "steps-post", "antialiased": True},
    "peak": {
        "linestyle": "None",
        "marker": "o",
        "markersize": 4.2,
        "markeredgecolor": "#FFFFFF",
        "markeredgewidth": 0.7,
        "alpha": 0.95,
    },
}
PQRST_PLOT_STYLE = {
    "average": {
        "linewidth": 2.25,
        "label": "average beat",
        "antialiased": True,
        "solid_capstyle": "round",
        "solid_joinstyle": "round",
    },
    "r_marker": {"linestyle": "--", "linewidth": 1.0, "label": "R"},
    "p_search": {"start_ms": -220, "end_ms": -80, "color": "#1E7A46", "alpha": 0.075, "label": "P search"},
    "t_search": {"start_ms": 120, "end_ms": 380, "color": "#A76400", "alpha": 0.075, "label": "T search"},
    "legend": {
        "loc": "upper right",
        "frameon": True,
        "fontsize": 9,
        "facecolor": "#FFFFFF",
        "edgecolor": "#D9E1EC",
        "framealpha": 0.96,
        "labelcolor": "#293247",
        "borderpad": 0.55,
        "labelspacing": 0.42,
        "handlelength": 2.0,
        "handletextpad": 0.7,
        "borderaxespad": 0.8,
    },
}


def seaborn_plot_theme() -> dict[str, object]:
    theme = {key: value for key, value in SEABORN_PLOT_THEME.items() if key != "rc"}
    return {"rc": dict(SEABORN_PLOT_THEME["rc"]), **theme}


def plot_trace_colors() -> dict[str, str]:
    return dict(PLOT_TRACE_COLORS)


def plot_trace_styles() -> dict[str, dict[str, object]]:
    return {name: dict(values) for name, values in PLOT_TRACE_STYLES.items()}


def pqrst_plot_style() -> dict[str, dict[str, object]]:
    return {name: dict(values) for name, values in PQRST_PLOT_STYLE.items()}


def apply_seaborn_plot_theme() -> None:
    theme = seaborn_plot_theme()
    sns.set_theme(
        style=str(theme["style"]),
        context=str(theme["context"]),
        palette=str(theme["palette"]),
        rc=theme["rc"],
    )


def new_export_figure(*, figsize: tuple[float, float], dpi: int = 160) -> Figure:
    apply_seaborn_plot_theme()
    fig = Figure(figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor(APP_VISUAL_TOKENS["surface"])
    return fig


def style_export_axes(axes: tuple[object, ...]) -> None:
    for ax in axes:
        ax.set_facecolor(APP_VISUAL_TOKENS["panel"])
        ax.set_axisbelow(True)
        ax.grid(True, color=APP_VISUAL_TOKENS["border"], linewidth=0.7, alpha=0.65)
        ax.tick_params(colors=APP_VISUAL_TOKENS["muted"], direction="out")
        ax.xaxis.label.set_color("#293247")
        ax.yaxis.label.set_color("#293247")
        ax.title.set_color(APP_VISUAL_TOKENS["ink"])
        sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(APP_VISUAL_TOKENS["border"])
            ax.spines[side].set_linewidth(0.9)
