from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from collections import deque
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
import tempfile
from tkinter import filedialog, messagebox, ttk

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ads1292-studio-matplotlib"))

import matplotlib
import numpy as np

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import seaborn as sns

from ads1292_studio.batch import export_batch_summary
from ads1292_studio.calibration import Calibration, read_calibration_json, write_calibration_json
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.device import Ads1x9xDevice, find_ads_port, list_ads_ports
from ads1292_studio.display import (
    EcgDisplaySettings,
    SoftwareFilterSettings,
    display_gain_labels,
    display_mode_label,
    display_window_labels,
    ecg_paper_grid_key,
    ecg_paper_grid_spec,
    parse_display_gain,
    parse_display_window,
    parse_sweep_speed,
    sweep_speed_labels,
)
from ads1292_studio.events import EventMarker, read_events_json, write_events_json
from ads1292_studio.gui_quality import build_quality_text, protocol_ready_for_live_quality
from ads1292_studio.gui_session_index import build_session_index_message
from ads1292_studio.macos_stderr import install_macos_stderr_filter
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import Recording, StreamSample, StreamStartResult
from ads1292_studio.plot_theme import (
    APP_VISUAL_TOKENS,
    PLOT_TRACE_COLORS,
    PLOT_TRACE_STYLES,
    PQRST_PLOT_STYLE,
    apply_seaborn_plot_theme,
    plot_trace_colors as base_plot_trace_colors,
    plot_trace_styles as base_plot_trace_styles,
    pqrst_plot_style as base_pqrst_plot_style,
    seaborn_plot_theme as base_seaborn_plot_theme,
)
from ads1292_studio.plots import decimate_for_plot, robust_ylim, smooth_for_plot, stable_ylim
from ads1292_studio.protocol import ProtocolStep, TestProtocol, protocol_template, read_protocol_json, write_protocol_json
from ads1292_studio.quality import QualityMetrics, compute_quality_metrics
from ads1292_studio.quality_gate import QualityGate, read_quality_gate_json, write_quality_gate_json
from ads1292_studio.report import export_review_report
from ads1292_studio.session_index import export_session_index
from ads1292_studio.session_package import export_session_package, verify_session_package
from ads1292_studio.signal_processing import (
    apply_software_filters,
    detect_r_peaks,
    heart_rate_summary,
    pqrst_review,
    review_channels,
)
from ads1292_studio.workers import LiveWorker


MAX_POINTS = 10000
VISIBLE_SECONDS = 8.0
SAMPLE_RATE_HZ = 500.0
DEFAULT_FILTER_ENABLED = False
DEFAULT_ECG_INVERTED = False
DEFAULT_DISPLAY_SETTINGS = EcgDisplaySettings()
DEFAULT_FILTER_SETTINGS = SoftwareFilterSettings()
DISPLAY_SMOOTHING_WINDOW = 11
DISPLAY_MIN_ECG_SPAN_COUNTS = 8.0
DISPLAY_MIN_RESP_SPAN_COUNTS = 40.0
APP_WINDOW_SPEC = {
    "geometry": "1320x860",
    "min_size": (1120, 740),
}
PRIMARY_TOOLBAR_BUTTONS = ("Refresh", "Connect", "Start", "Stop")
TOOLBAR_BUTTON_STYLES = {
    "Refresh": "TButton",
    "Connect": "Primary.TButton",
    "Start": "Primary.TButton",
    "Stop": "Stop.TButton",
}
BUTTON_CHROME_SPEC = {
    "default": {
        "padding": (10, 6),
        "font": ("Aptos", 12),
        "foreground": "#172033",
        "background": "#FFFFFF",
        "active_foreground": "#1F4FB2",
        "active_background": "#EEF3FA",
        "disabled_foreground": "#657084",
        "disabled_background": "#D9E1EC",
        "borderwidth": 1,
        "relief": "flat",
    },
    "primary": {
        "padding": (12, 6),
        "font": ("Aptos", 12, "bold"),
        "foreground": "#FFFFFF",
        "background": "#2F6FED",
        "active_foreground": "#FFFFFF",
        "active_background": "#1F4FB2",
        "disabled_foreground": "#657084",
        "disabled_background": "#D9E1EC",
        "borderwidth": 1,
        "relief": "flat",
    },
    "stop": {
        "padding": (12, 6),
        "font": ("Aptos", 12, "bold"),
        "foreground": "#B3261E",
        "background": "#FFFFFF",
        "active_foreground": "#FFFFFF",
        "active_background": "#B3261E",
        "disabled_foreground": "#657084",
        "disabled_background": "#D9E1EC",
        "borderwidth": 1,
        "relief": "flat",
    },
    "sidebar": {
        "padding": (12, 7),
        "font": ("Aptos", 11, "bold"),
        "foreground": "#172033",
        "background": "#FFFFFF",
        "active_foreground": "#1F4FB2",
        "active_background": "#EEF3FA",
        "disabled_foreground": "#657084",
        "disabled_background": "#D9E1EC",
        "borderwidth": 1,
        "relief": "flat",
    },
}
INPUT_CHROME_SPEC = {
    "label": {
        "font": ("Aptos", 10, "bold"),
        "padding": (2, 3),
        "background": "#F6F8FB",
        "foreground": "#657084",
    },
    "entry": {
        "padding": (9, 6),
        "fieldbackground": "#FFFFFF",
        "foreground": "#172033",
        "insert": "#2F6FED",
        "focus_background": "#FFFFFF",
        "disabled_foreground": "#657084",
        "disabled_background": "#EEF3FA",
        "borderwidth": 1,
        "relief": "flat",
    },
    "combobox": {
        "padding": (8, 5),
        "fieldbackground": "#FFFFFF",
        "background": "#FFFFFF",
        "foreground": "#172033",
        "selectbackground": "#EEF3FA",
        "selectforeground": "#172033",
        "arrowcolor": "#657084",
        "active_arrowcolor": "#1F4FB2",
        "disabled_foreground": "#657084",
        "disabled_background": "#EEF3FA",
    },
    "check": {
        "padding": (3, 5),
        "font": ("Aptos", 11),
        "background": "#F6F8FB",
        "foreground": "#172033",
        "active_foreground": "#1F4FB2",
        "disabled_foreground": "#657084",
        "active_background": "#F6F8FB",
    },
    "toolbar_toggle": {
        "padding": (5, 4),
        "font": ("Aptos", 11, "bold"),
        "background": "#EEF3FA",
        "foreground": "#293247",
        "active_foreground": "#1F4FB2",
        "disabled_foreground": "#657084",
        "active_background": "#EAF1FF",
    },
}
TOOLBAR_CONTROL_STYLES = {
    "port": "Port.TCombobox",
    "toggle": "ToolbarToggle.TCheckbutton",
}
TOOLBAR_FRAME_SPEC = {
    "frame": "Toolbar.TFrame",
    "separator": "ToolbarSeparator.TFrame",
    "background": "#EEF3FA",
    "separator_background": "#D9E1EC",
    "borderwidth": 1,
    "relief": "flat",
}
TOOLBAR_LABEL_SPEC = {
    "style": "ToolbarLabel.TLabel",
    "font": ("Aptos", 12, "bold"),
    "background": "#EEF3FA",
    "foreground": "#172033",
}
TOOLBAR_HINT_STYLES = {
    "frame": "ToolbarHint.TFrame",
    "label": "ToolbarHint.TLabel",
    "background": "#EAF1FF",
    "foreground": "#293247",
    "font": ("Aptos", 11, "bold"),
    "border": "#EAF1FF",
    "borderwidth": 0,
    "relief": "flat",
}
TOOLBAR_GROUP_PADDING = {
    "separator": (12, 8),
    "tight": (4, 4),
}
TOOLBAR_LAYOUT_SPEC = {
    "frame": "Toolbar.TFrame",
    "padding": (16, 10, 16, 10),
    "port_width": 36,
    "port_padding": (8, 8),
    "refresh_padding": (0, 4),
    "primary_action_padding": (12, 4),
    "inline_action_padding": (4, 4),
    "save_padding": (8, 4),
    "toggle_padding": (4, 4),
    "display_label_padding": (4, 3),
    "display_control_padding": (4, 8),
    "display_width": 9,
    "separator_width": 1,
    "hint_padding": (12, 5),
}
SECONDARY_ACTION_BUTTONS = (
    "Load CSV",
    "Export Report",
    "Export Package",
    "Verify Package",
    "Batch Compare",
    "Session Index",
)
SIDEBAR_TABS = ("Status", "Session", "Validation", "Protocol", "Actions")
SIDEBAR_LAYOUT_SPEC = {
    "shell": "SidebarShell.TFrame",
    "width": 348,
    "padding": (12, 12),
    "scroll_width": 316,
}
WORKSPACE_LAYOUT_SPEC = {
    "main": "Main.TFrame",
    "main_padding": (8, 12, 14, 12),
    "sidebar_weight": 0,
    "main_weight": 1,
}
BASE_CHROME_SPEC = {
    "font": ("Aptos", 12),
    "background": "#F6F8FB",
    "foreground": "#172033",
    "frame": "TFrame",
    "label": "TLabel",
    "sidebar": "SidebarShell.TFrame",
    "main": "Main.TFrame",
    "borderwidth": 0,
}
BASE_NOTEBOOK_STYLES = {
    "notebook": "TNotebook",
    "tab": "TNotebook.Tab",
    "background": "#F6F8FB",
    "borderwidth": 0,
    "tab_padding": (14, 7),
    "tab_font": ("Aptos", 12, "bold"),
}
BASE_CHECKBUTTON_STYLE = {
    "style": "TCheckbutton",
    "background": "#EEF3FA",
    "foreground": "#172033",
}
MAIN_TABS = ("Live ECG", "Review CSV", "PQRST Beat", "Event Log")
STATUS_CARD_LABELS = ("Connection", "Acquisition", "Data", "Package")
SIGNAL_CARD_LABELS = ("Signal", "Contact", "Heart rate", "Artifacts")
ADS1292R_ECG_SOURCE = "CH2"
ADS1292R_CHANNEL_LABELS = {
    "CH2": "CH2 ECG Lead I (LA-RA)",
    "CH1": "CH1 Respiration raw",
}
ADS1292R_PLOT_LAYOUT_LABELS = (
    "CH2 ECG Lead I (LA-RA)",
    "CH1 Respiration raw",
    "Lead-off / contact status",
)
STATUS_TONE_STYLES = {
    "ready": "Ready.Status.TLabel",
    "running": "Running.Status.TLabel",
    "warning": "Warning.Status.TLabel",
    "neutral": "Neutral.Status.TLabel",
}
STATUS_LABEL_SPEC = {
    "font": ("Aptos", 12, "bold"),
    "padding": (8, 4),
    "backgrounds": {
        "ready": "#E9F6EE",
        "running": "#EAF1FF",
        "warning": "#FFF4E3",
        "neutral": "#EEF3FA",
    },
    "foregrounds": {
        "ready": "#1E7A46",
        "running": "#2F6FED",
        "warning": "#A76400",
        "neutral": "#657084",
    },
}
HEADER_CONNECTION_STYLES = {
    "ready": "Ready.Connection.TLabel",
    "running": "Running.Connection.TLabel",
    "warning": "Warning.Connection.TLabel",
    "neutral": "Neutral.Connection.TLabel",
}
HEADER_CONNECTION_PILL = {
    "styles": HEADER_CONNECTION_STYLES,
    "padding": (12, 5),
    "font": ("Aptos", 12, "bold"),
    "borderwidth": 1,
    "relief": "flat",
    "backgrounds": {
        "ready": "#E9F6EE",
        "running": "#EAF1FF",
        "warning": "#FFF4E3",
        "neutral": "#EEF3FA",
    },
    "foregrounds": {
        "ready": "#1E7A46",
        "running": "#2F6FED",
        "warning": "#A76400",
        "neutral": "#657084",
    },
}
HEADER_LAYOUT_SPEC = {
    "frame": "Header.TFrame",
    "separator": "HeaderSeparator.TFrame",
    "padding": (20, 14, 20, 12),
    "subtitle_padding": (14, 0),
    "separator_height": 1,
}
HEADER_FRAME_SPEC = {
    "frame": "Header.TFrame",
    "separator": "HeaderSeparator.TFrame",
    "background": "#FFFFFF",
    "separator_background": "#D9E1EC",
    "borderwidth": 0,
}
HEADER_TEXT_STYLES = {
    "title": {
        "style": "AppTitle.TLabel",
        "font": ("Aptos", 20, "bold"),
        "background": "#FFFFFF",
        "foreground": "#172033",
    },
    "subtitle": {
        "style": "AppSubtitle.TLabel",
        "font": ("Aptos", 12),
        "background": "#FFFFFF",
        "foreground": "#657084",
    },
}
STATUS_TONE_COLORS = {
    "ready": "#1E7A46",
    "running": "#2F6FED",
    "warning": "#A76400",
    "neutral": "#A9B4C3",
}
LIVE_AXIS_SPEC = {
    "x_major_tick_seconds": 1.0,
}
EMPTY_PLOT_MESSAGES = {
    "live": (
        "Connect an ADS1292 board, then press Start",
        "CH1 respiration/contact context appears here",
        "Lead-off status stays at 0 when contacts are good",
    ),
    "review": (
        "Load a CSV to review recorded ECG",
        "CH1 respiration/contact context appears here",
        "Lead-off/contact status appears here",
    ),
    "pqrst": ("Load or record data to build the averaged PQRST beat",),
}
EMPTY_PLOT_STYLE = {
    "text_color": "#516070",
    "box_face": "#F8FAFD",
    "box_edge": "#D9E1EC",
    "font_size": 10,
    "font_weight": "normal",
    "alpha": 0.95,
    "box_pad": 0.62,
    "rounding": 0.18,
    "line_width": 0.6,
}
LOG_PANEL_SPEC = {
    "shell": "Main.TFrame",
    "panel": "LogPanel.TFrame",
    "padding": (14, 14),
    "panel_padding": (10, 10),
    "height": 12,
    "wrap": "word",
    "scrollbar": "vertical",
    "font": ("Menlo", 12),
    "background": "#F8FAFD",
    "foreground": "#172033",
    "insert": "#2F6FED",
    "select_background": "#2F6FED",
    "select_foreground": "#FFFFFF",
    "text_padding": (12, 10),
    "spacing": (2, 2),
    "borderwidth": 0,
    "highlightthickness": 0,
    "relief": "flat",
}
SCROLLBAR_CHROME_SPEC = {
    "vertical": "App.Vertical.TScrollbar",
    "width": 13,
    "background": "#A9B4C3",
    "active_background": "#657084",
    "trough": "#EEF3FA",
    "border": "#EEF3FA",
    "arrow": "#657084",
    "relief": "flat",
    "borderwidth": 0,
}
PANEL_CHROME_SPEC = {
    "background": "#FFFFFF",
    "border": "#D9E1EC",
    "borderwidth": 1,
    "relief": "flat",
}
PLOT_PANEL_SPEC = {
    "shell": "Main.TFrame",
    "panel": "PlotPanel.TFrame",
    "padding": (14, 14),
    "panel_padding": (12, 12),
}
PLOT_AXIS_STYLE = {
    "face": "#FFFFFF",
    "grid": "#D9E1EC",
    "spine": "#D9E1EC",
    "tick": "#657084",
    "label": "#293247",
    "title": "#172033",
    "grid_linewidth": 0.7,
    "grid_alpha": 0.38,
    "axisbelow": True,
    "spine_linewidth": 0.7,
    "tick_label_size": 9,
    "tick_direction": "out",
    "tick_length": 3.0,
    "tick_width": 0.65,
    "label_size": 10,
    "label_pad": 7,
    "title_size": 11,
    "title_weight": "bold",
    "title_pad": 10,
}
PLOT_FIGURE_LAYOUTS = {
    "three_panel": {
        "left": 0.075,
        "right": 0.985,
        "top": 0.965,
        "bottom": 0.075,
        "hspace": 0.36,
    },
    "single_panel": {
        "left": 0.08,
        "right": 0.985,
        "top": 0.955,
        "bottom": 0.13,
    },
}
PLOT_CANVAS_WIDGET_STYLE = {
    "background": "#FFFFFF",
    "borderwidth": 0,
    "highlightthickness": 0,
}
SIDEBAR_FIELD_STYLES = {
    "label": "FieldLabel.TLabel",
    "entry": "Field.TEntry",
    "check": "FieldCheck.TCheckbutton",
}
SECTION_HEADING_STYLES = {
    "label": "SectionHeading.TLabel",
    "padding": (2, 5),
    "font": ("Aptos", 12, "bold"),
    "background": "#F6F8FB",
    "foreground": "#293247",
}
MUTED_LABEL_SPEC = {
    "style": "Muted.TLabel",
    "font": ("Aptos", 11),
    "background": "#F6F8FB",
    "foreground": "#657084",
}
SIDEBAR_ACTION_BUTTON_STYLE = "SidebarAction.TButton"
ACTION_SECTION_STYLES = {
    "frame": "ActionSection.TFrame",
    "label": "ActionSection.TLabel",
    "padding": (10, 5),
    "font": ("Aptos", 10, "bold"),
    "background": "#EEF3FA",
    "foreground": "#293247",
}
SIDEBAR_NOTEBOOK_STYLES = {
    "notebook": "Sidebar.TNotebook",
    "tab": "Sidebar.TNotebook.Tab",
    "background": "#F6F8FB",
    "borderwidth": 0,
    "tab_padding": (12, 7),
    "tab_font": ("Aptos", 10, "bold"),
    "tab_background": "#EEF3FA",
    "selected_foreground": "#2F6FED",
    "inactive_foreground": "#657084",
    "active_foreground": "#172033",
    "active_background": "#FFFFFF",
}
WORKSPACE_NOTEBOOK_STYLES = {
    "notebook": "Workspace.TNotebook",
    "tab": "Workspace.TNotebook.Tab",
    "background": "#F6F8FB",
    "borderwidth": 0,
    "tab_padding": (18, 9),
    "tab_font": ("Aptos", 12, "bold"),
    "tab_background": "#EEF3FA",
    "selected_foreground": "#2F6FED",
    "inactive_foreground": "#657084",
    "active_foreground": "#172033",
    "active_background": "#FFFFFF",
}
WORKFLOW_HINT_STYLES = {
    "frame": "WorkflowHint.TFrame",
    "label": "WorkflowHint.TLabel",
    "stripe": "#2F6FED",
    "background": "#EAF1FF",
    "foreground": "#1F4FB2",
    "font": ("Aptos", 11, "bold"),
}
SAFETY_NOTICE_STYLES = {
    "frame": "SafetyNotice.TFrame",
    "label": "SafetyNotice.TLabel",
    "stripe": "#A76400",
    "background": "#FFF4E3",
    "foreground": "#6B4700",
    "font": ("Aptos", 11, "bold"),
}
SIDEBAR_TEXT_CARD_SPEC = {
    "stripe_width": 4,
    "label_padding": (12, 8),
    "content_padding": (12, 8),
    "primary_wrap": 240,
    "detail_wrap": 230,
    "value_top_padding": (3, 0),
}
STATUS_DETAIL_STYLES = {
    "frame": "StatusDetail.TFrame",
    "label": "StatusDetailLabel.TLabel",
    "value": "StatusDetailValue.TLabel",
    "stripe": "#D9E1EC",
    "background": "#FFFFFF",
    "label_foreground": "#657084",
    "label_font": ("Aptos", 10, "bold"),
    "value_foreground": "#172033",
    "value_font": ("Aptos", 11),
    "value_wrap": 245,
}
CARD_LABEL_SPEC = {
    "style": "CardLabel.TLabel",
    "font": ("Aptos", 11),
    "background": "#FFFFFF",
    "foreground": "#657084",
    "width": 12,
    "content_padding": (12, 8),
    "stripe_width": 5,
    "row_padding": (0, 4),
    "value_padding": (8, 0),
    "signal_value_wrap": 170,
}
EVENT_COUNT_STYLES = {
    "frame": "EventCount.TFrame",
    "label": "EventCountLabel.TLabel",
    "value": "EventCountValue.TLabel",
    "stripe": "#7A5CDB",
    "background": "#FFFFFF",
    "label_foreground": "#657084",
    "label_font": ("Aptos", 10, "bold"),
    "value_foreground": "#172033",
    "value_font": ("Aptos", 11, "bold"),
}
PROTOCOL_NOTE_STYLES = {
    "frame": "ProtocolNote.TFrame",
    "label": "ProtocolNoteLabel.TLabel",
    "value": "ProtocolNoteValue.TLabel",
    "stripe": "#2F6FED",
    "background": "#FFFFFF",
    "label_foreground": "#1F4FB2",
    "label_font": ("Aptos", 10, "bold"),
    "value_foreground": "#293247",
    "value_font": ("Aptos", 11),
    "value_wrap": 245,
}


@dataclass(frozen=True)
class GuiStatusCard:
    label: str
    value: str
    tone: str


@dataclass(frozen=True)
class LiveQualityResult:
    generation: int
    source: str
    valid_rr: int
    samples: tuple[StreamSample, ...]
    status_values: tuple[int, ...]
    metrics: QualityMetrics | None = None
    error: str | None = None


@dataclass(frozen=True)
class GuiState:
    connected: bool
    streaming: bool
    has_data: bool
    has_recording_path: bool
    loading_csv: bool = False
    connecting: bool = False
    starting: bool = False

    @property
    def busy(self) -> bool:
        return self.loading_csv or self.connecting or self.starting

    @property
    def package_ready(self) -> bool:
        return self.has_data and self.has_recording_path and not self.busy


@dataclass(frozen=True)
class CsvLoadResult:
    path: Path
    recording: Recording | None = None
    error: str | None = None


@dataclass(frozen=True)
class ConnectResult:
    port: str
    detail: str | None = None
    error: str | None = None


def status_tone_style(tone: str) -> str:
    return STATUS_TONE_STYLES.get(tone, STATUS_TONE_STYLES["neutral"])


def status_label_spec() -> dict[str, object]:
    return dict(STATUS_LABEL_SPEC)


def header_connection_style(tone: str) -> str:
    return HEADER_CONNECTION_STYLES.get(tone, HEADER_CONNECTION_STYLES["neutral"])


def header_connection_styles() -> dict[str, object]:
    return {
        "styles": dict(HEADER_CONNECTION_STYLES),
        "padding": HEADER_CONNECTION_PILL["padding"],
        "font": HEADER_CONNECTION_PILL["font"],
        "borderwidth": HEADER_CONNECTION_PILL["borderwidth"],
        "relief": HEADER_CONNECTION_PILL["relief"],
        "backgrounds": dict(HEADER_CONNECTION_PILL["backgrounds"]),
        "foregrounds": dict(HEADER_CONNECTION_PILL["foregrounds"]),
    }


def header_layout_spec() -> dict[str, object]:
    return dict(HEADER_LAYOUT_SPEC)


def header_frame_spec() -> dict[str, object]:
    return dict(HEADER_FRAME_SPEC)


def header_text_styles() -> dict[str, dict[str, object]]:
    return {name: dict(values) for name, values in HEADER_TEXT_STYLES.items()}


def status_tone_color(tone: str) -> str:
    return STATUS_TONE_COLORS.get(tone, STATUS_TONE_COLORS["neutral"])


def app_visual_tokens() -> dict[str, str]:
    return dict(APP_VISUAL_TOKENS)


def base_chrome_spec() -> dict[str, object]:
    return dict(BASE_CHROME_SPEC)


def base_notebook_styles() -> dict[str, object]:
    return dict(BASE_NOTEBOOK_STYLES)


def base_checkbutton_style() -> dict[str, object]:
    return dict(BASE_CHECKBUTTON_STYLE)


def app_window_spec() -> dict[str, object]:
    return dict(APP_WINDOW_SPEC)


def plot_trace_colors() -> dict[str, str]:
    return base_plot_trace_colors()


def seaborn_plot_theme() -> dict[str, object]:
    return base_seaborn_plot_theme()


def plot_trace_styles() -> dict[str, dict[str, object]]:
    return base_plot_trace_styles()


def live_axis_spec() -> dict[str, float]:
    return dict(LIVE_AXIS_SPEC)


def pqrst_plot_style() -> dict[str, dict[str, object]]:
    return base_pqrst_plot_style()


def empty_plot_messages() -> dict[str, tuple[str, ...]]:
    return dict(EMPTY_PLOT_MESSAGES)


def empty_plot_style() -> dict[str, object]:
    return dict(EMPTY_PLOT_STYLE)


def log_panel_spec() -> dict[str, object]:
    return dict(LOG_PANEL_SPEC)


def scrollbar_chrome_spec() -> dict[str, object]:
    return dict(SCROLLBAR_CHROME_SPEC)


def panel_chrome_spec() -> dict[str, object]:
    return dict(PANEL_CHROME_SPEC)


def plot_panel_spec() -> dict[str, object]:
    return dict(PLOT_PANEL_SPEC)


def plot_axis_style() -> dict[str, object]:
    return dict(PLOT_AXIS_STYLE)


def plot_figure_layouts() -> dict[str, dict[str, float]]:
    return {name: dict(layout) for name, layout in PLOT_FIGURE_LAYOUTS.items()}


def plot_canvas_widget_style() -> dict[str, object]:
    return dict(PLOT_CANVAS_WIDGET_STYLE)


def sidebar_field_styles() -> dict[str, str]:
    return dict(SIDEBAR_FIELD_STYLES)


def section_heading_styles() -> dict[str, object]:
    return dict(SECTION_HEADING_STYLES)


def muted_label_spec() -> dict[str, object]:
    return dict(MUTED_LABEL_SPEC)


def sidebar_action_button_style() -> str:
    return SIDEBAR_ACTION_BUTTON_STYLE


def action_section_styles() -> dict[str, str]:
    return dict(ACTION_SECTION_STYLES)


def sidebar_notebook_styles() -> dict[str, object]:
    return dict(SIDEBAR_NOTEBOOK_STYLES)


def sidebar_layout_spec() -> dict[str, object]:
    return dict(SIDEBAR_LAYOUT_SPEC)


def workspace_notebook_styles() -> dict[str, object]:
    return dict(WORKSPACE_NOTEBOOK_STYLES)


def workspace_layout_spec() -> dict[str, object]:
    return dict(WORKSPACE_LAYOUT_SPEC)


def workflow_hint_styles() -> dict[str, str]:
    return dict(WORKFLOW_HINT_STYLES)


def safety_notice_styles() -> dict[str, str]:
    return dict(SAFETY_NOTICE_STYLES)


def sidebar_text_card_spec() -> dict[str, object]:
    return dict(SIDEBAR_TEXT_CARD_SPEC)


def status_detail_styles() -> dict[str, str]:
    return dict(STATUS_DETAIL_STYLES)


def card_label_spec() -> dict[str, object]:
    return dict(CARD_LABEL_SPEC)


def event_count_styles() -> dict[str, str]:
    return dict(EVENT_COUNT_STYLES)


def protocol_note_styles() -> dict[str, object]:
    return dict(PROTOCOL_NOTE_STYLES)


def ads1292r_channel_label(channel: str) -> str:
    return ADS1292R_CHANNEL_LABELS.get(channel.upper(), channel)


def ads1292r_secondary_channel_label(ecg_source: str) -> str:
    return "CH1 Respiration raw" if ecg_source.upper() == "CH2" else "CH2 ECG Lead I (LA-RA)"


def ads1292r_plot_layout_labels() -> tuple[str, str, str]:
    return ADS1292R_PLOT_LAYOUT_LABELS


def _gui_state(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
    loading_csv: bool = False,
    connecting: bool = False,
    starting: bool = False,
) -> GuiState:
    if state is not None:
        return state
    return GuiState(
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
        loading_csv=loading_csv,
        connecting=connecting,
        starting=starting,
    )


def primary_toolbar_button_labels() -> tuple[str, ...]:
    return PRIMARY_TOOLBAR_BUTTONS


def toolbar_button_style(label: str) -> str:
    return TOOLBAR_BUTTON_STYLES.get(label, "TButton")


def button_chrome_spec() -> dict[str, dict[str, object]]:
    return {name: dict(values) for name, values in BUTTON_CHROME_SPEC.items()}


def input_chrome_spec() -> dict[str, dict[str, object]]:
    return {name: dict(values) for name, values in INPUT_CHROME_SPEC.items()}


def toolbar_control_styles() -> dict[str, str]:
    return dict(TOOLBAR_CONTROL_STYLES)


def toolbar_frame_spec() -> dict[str, object]:
    return dict(TOOLBAR_FRAME_SPEC)


def toolbar_label_spec() -> dict[str, object]:
    return dict(TOOLBAR_LABEL_SPEC)


def toolbar_hint_styles() -> dict[str, str]:
    return dict(TOOLBAR_HINT_STYLES)


def toolbar_group_padding() -> dict[str, tuple[int, int]]:
    return dict(TOOLBAR_GROUP_PADDING)


def toolbar_layout_spec() -> dict[str, object]:
    return dict(TOOLBAR_LAYOUT_SPEC)


def secondary_action_button_labels() -> tuple[str, ...]:
    return SECONDARY_ACTION_BUTTONS


def sidebar_tab_labels() -> tuple[str, ...]:
    return SIDEBAR_TABS


def main_tab_labels() -> tuple[str, ...]:
    return MAIN_TABS


def gui_control_states(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
) -> dict[str, str]:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
    )
    if current.busy:
        return {
            "Refresh": tk.DISABLED,
            "Connect": tk.DISABLED,
            "Start": tk.DISABLED,
            "Stop": tk.NORMAL if current.streaming else tk.DISABLED,
            "Load CSV": tk.DISABLED,
            "Export Report": tk.DISABLED,
            "Export Package": tk.DISABLED,
            "Verify Package": tk.DISABLED,
            "Batch Compare": tk.DISABLED,
            "Session Index": tk.DISABLED,
        }
    return {
        "Refresh": tk.NORMAL,
        "Connect": tk.NORMAL,
        "Start": tk.NORMAL if current.connected and not current.streaming else tk.DISABLED,
        "Stop": tk.NORMAL if current.streaming else tk.DISABLED,
        "Load CSV": tk.NORMAL if not current.streaming else tk.DISABLED,
        "Export Report": tk.NORMAL if current.has_data else tk.DISABLED,
        "Export Package": tk.NORMAL if current.package_ready else tk.DISABLED,
        "Verify Package": tk.NORMAL,
        "Batch Compare": tk.NORMAL,
        "Session Index": tk.NORMAL,
    }


def gui_workflow_hint(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
) -> str:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
    )
    if current.connecting:
        return "Connecting: probing the selected port."
    if current.starting:
        return "Starting stream: waiting for the device to confirm."
    if current.loading_csv:
        return "Loading CSV: keep the window open; review plots will update when parsing finishes."
    if current.streaming:
        return "Streaming: monitor signal quality, add events if needed, then press Stop."
    if current.package_ready:
        return "Data ready: export a report or package the recording with its sidecars."
    if current.has_data:
        return "Data loaded: export a report; package export needs a saved CSV path."
    if current.connected:
        return "Next: press Start to begin acquisition, or load a CSV for offline review."
    return "Next: select an ADS1292 port and press Connect, or load an existing CSV."


def gui_status_overview(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
) -> str:
    cards = gui_status_cards(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
    )
    return "\n".join(f"{card.label}: {card.value}" for card in cards)


def header_connection_tone(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
    loading_csv: bool = False,
    connecting: bool = False,
    starting: bool = False,
) -> str:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
        loading_csv=loading_csv,
        connecting=connecting,
        starting=starting,
    )
    if current.connecting or current.starting or current.streaming or current.loading_csv:
        return "running"
    if current.connected:
        return "ready"
    return "warning"


def gui_status_cards(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
) -> tuple[GuiStatusCard, ...]:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
    )
    connection = GuiStatusCard(
        label="Connection",
        value="connected" if current.connected else "disconnected",
        tone="ready" if current.connected else "warning",
    )
    if current.connecting:
        acquisition_value = "connecting"
        acquisition_tone = "running"
    elif current.starting:
        acquisition_value = "starting stream"
        acquisition_tone = "running"
    elif current.loading_csv:
        acquisition_value = "loading CSV"
        acquisition_tone = "running"
    elif current.streaming:
        acquisition_value = "streaming"
        acquisition_tone = "running"
    elif current.connected:
        acquisition_value = "ready to start"
        acquisition_tone = "ready"
    else:
        acquisition_value = "idle"
        acquisition_tone = "neutral"
    data = GuiStatusCard(
        label="Data",
        value="loading CSV" if current.loading_csv else ("live or loaded" if current.has_data else "none loaded"),
        tone="running" if current.loading_csv else ("ready" if current.has_data else "neutral"),
    )
    if current.package_ready:
        package_value = "ready"
        package_tone = "ready"
    elif current.has_data:
        package_value = "needs saved CSV"
        package_tone = "warning"
    else:
        package_value = "unavailable"
        package_tone = "neutral"
    return (
        connection,
        GuiStatusCard("Acquisition", acquisition_value, acquisition_tone),
        data,
        GuiStatusCard("Package", package_value, package_tone),
    )


def display_signal_values(
    values: np.ndarray,
    *,
    filter_enabled: bool,
    filter_settings: SoftwareFilterSettings | None = None,
    invert: bool = False,
    gain: float = 1.0,
    sample_rate_hz: float = SAMPLE_RATE_HZ,
) -> np.ndarray:
    settings = filter_settings or SoftwareFilterSettings(bandpass_enabled=filter_enabled)
    display = apply_software_filters(values, sample_rate_hz, settings)
    display = np.asarray(display, dtype=float)
    display = -display if invert else display
    return display * gain


def gui_signal_quality_cards(
    *,
    quality_label: str | None = None,
    ecg_source: str | None = None,
    contact_ok_percent: float | None = None,
    lead_off_bad_samples: int | None = None,
    r_peaks: int | None = None,
    hr_median_bpm: float | None = None,
    baseline_drift_counts: float | None = None,
    noise_rms_counts: float | None = None,
    peak_to_peak_counts: float | None = None,
) -> tuple[GuiStatusCard, ...]:
    if quality_label is None:
        return (
            GuiStatusCard("Signal", "not reviewed", "neutral"),
            GuiStatusCard("Contact", "--", "neutral"),
            GuiStatusCard("Heart rate", "--", "neutral"),
            GuiStatusCard("Artifacts", "--", "neutral"),
        )

    source = ads1292r_channel_label(ecg_source) if ecg_source else "--"
    contact = 0.0 if contact_ok_percent is None else contact_ok_percent
    bad_samples = 0 if lead_off_bad_samples is None else lead_off_bad_samples
    peak_count = 0 if r_peaks is None else r_peaks
    hr = 0.0 if hr_median_bpm is None else hr_median_bpm
    drift = 0.0 if baseline_drift_counts is None else baseline_drift_counts
    noise = 0.0 if noise_rms_counts is None else noise_rms_counts
    p2p = 0.0 if peak_to_peak_counts is None else peak_to_peak_counts

    signal_tone = "ready" if quality_label in {"Good ECG/QRS", "Usable ECG/QRS"} else "warning"
    contact_tone = "ready" if contact >= 95.0 else "warning"
    hr_tone = "ready" if peak_count >= 5 and 35.0 <= hr <= 180.0 else "warning"
    artifact_tone = "warning" if drift >= 250.0 or noise >= 150.0 else "neutral"
    hr_value = f"{hr:.1f}" if hr > 0 else "--"
    return (
        GuiStatusCard("Signal", f"{quality_label} on {source}", signal_tone),
        GuiStatusCard("Contact", f"{contact:.1f}% OK, {bad_samples} bad", contact_tone),
        GuiStatusCard("Heart rate", f"{hr_value} bpm, {peak_count} R", hr_tone),
        GuiStatusCard("Artifacts", f"drift {drift:.0f} ct, noise {noise:.1f} ct, p2p {p2p:.0f} ct", artifact_tone),
    )


def compute_live_quality_result(
    *,
    generation: int,
    source: str,
    valid_rr: int,
    ch1_values: tuple[float, ...],
    ch2_values: tuple[float, ...],
    status_values: tuple[int, ...],
) -> LiveQualityResult:
    try:
        samples = build_live_quality_samples(ch1_values, ch2_values, status_values)
        metrics = compute_quality_metrics(samples, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
    except Exception as exc:  # pragma: no cover - defensive worker boundary
        return LiveQualityResult(generation, source, valid_rr, tuple(), status_values, error=str(exc))
    return LiveQualityResult(generation, source, valid_rr, samples, status_values, metrics=metrics)


def build_live_quality_samples(
    ch1_values: tuple[float, ...],
    ch2_values: tuple[float, ...],
    status_values: tuple[int, ...],
) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(
            timestamp=index / SAMPLE_RATE_HZ,
            ch1=int(ch1),
            ch2=int(ch2),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=int(status),
        )
        for index, (ch1, ch2, status) in enumerate(zip(ch1_values, ch2_values, status_values))
    )


def set_string_var_if_changed(variable: tk.StringVar, value: str) -> bool:
    if variable.get() == value:
        return False
    variable.set(value)
    return True


def _mousewheel_units(event: tk.Event) -> int:
    if getattr(event, "num", None) == 4:
        return -1
    if getattr(event, "num", None) == 5:
        return 1
    delta = int(getattr(event, "delta", 0))
    if delta == 0:
        return 0
    return -1 if delta > 0 else 1


class ScrollableFrame:
    def __init__(self, parent: tk.Widget, width: int = 280) -> None:
        scrollbar_spec = scrollbar_chrome_spec()
        self.frame = ttk.Frame(parent)
        self.canvas = tk.Canvas(self.frame, width=width, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self.frame,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
            style=str(scrollbar_spec["vertical"]),
        )
        self.content = ttk.Frame(self.canvas, padding=10)
        self._content_window = self.canvas.create_window((0, 0), window=self.content, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._fit_content_width)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_content_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._content_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not self._contains_pointer(event):
            return
        units = _mousewheel_units(event)
        if units:
            self.canvas.yview_scroll(units, "units")

    def _contains_pointer(self, event: tk.Event) -> bool:
        x = int(getattr(event, "x_root", self.canvas.winfo_pointerx()))
        y = int(getattr(event, "y_root", self.canvas.winfo_pointery()))
        left = self.canvas.winfo_rootx()
        top = self.canvas.winfo_rooty()
        right = left + self.canvas.winfo_width()
        bottom = top + self.canvas.winfo_height()
        return left <= x <= right and top <= y <= bottom


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ADS1292 Studio")
        window_spec = app_window_spec()
        self.geometry(str(window_spec["geometry"]))
        self.minsize(*window_spec["min_size"])

        self.samples: queue.Queue[StreamSample] = queue.Queue()
        self.logs: queue.Queue[str] = queue.Queue()
        self.csv_load_results: queue.Queue[CsvLoadResult] = queue.Queue()
        self.connect_results: queue.Queue[ConnectResult] = queue.Queue()
        self.live_quality_results: queue.Queue[LiveQualityResult] = queue.Queue()
        self.live_quality_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ads1292-quality")
        self.live_quality_future: Future[LiveQualityResult] | None = None
        self.live_quality_generation = 0
        self.is_connecting = False
        self.stream_start_results: queue.Queue[StreamStartResult] = queue.Queue()
        self.worker = LiveWorker(self.samples, self.logs, self.stream_start_results)
        self.connected_port: str | None = None
        self.recording_path: Path | None = None
        self.loaded_samples: tuple[StreamSample, ...] = tuple()
        self.event_markers: list[EventMarker] = []
        self.is_streaming = False
        self.is_loading_csv = False
        self.is_starting = False

        self.sample_index = 0
        self.ch1: deque[float] = deque(maxlen=MAX_POINTS)
        self.ch2: deque[float] = deque(maxlen=MAX_POINTS)
        self.status: deque[int] = deque(maxlen=MAX_POINTS)
        self.indices: deque[int] = deque(maxlen=MAX_POINTS)
        self.board_hr: deque[int] = deque(maxlen=MAX_POINTS)
        self.board_rr: deque[int] = deque(maxlen=MAX_POINTS)
        self.empty_plot_artists: list[object] = []
        self.live_calibration_artists: list[object] = []
        self.review_calibration_artists: list[object] = []
        self.ecg_paper_grid_cache: dict[int, tuple[float, float, float, float]] = {}
        self.calibration_pulse_cache: dict[int, str] = {}

        self._build_ui()
        self.refresh_ports()
        self.after(50, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self) -> None:
        self._configure_status_styles()
        self.connection_var = tk.StringVar(value="Not connected")
        self.configure(bg=APP_VISUAL_TOKENS["surface"])

        header_spec = header_layout_spec()
        header = ttk.Frame(self, padding=header_spec["padding"], style=str(header_spec["frame"]))
        header.pack(side=tk.TOP, fill=tk.X)
        self.header_frame = header
        header_text = header_text_styles()
        self.header_title_label = ttk.Label(header, text="ADS1292 Studio", style=str(header_text["title"]["style"]))
        self.header_title_label.pack(side=tk.LEFT)
        self.header_subtitle_label = ttk.Label(
            header,
            text="MOTAC ECG validation",
            style=str(header_text["subtitle"]["style"]),
        )
        self.header_subtitle_label.pack(side=tk.LEFT, padx=header_spec["subtitle_padding"])
        self.connection_label = ttk.Label(
            header,
            textvariable=self.connection_var,
            style=header_connection_style("warning"),
        )
        self.connection_label.pack(side=tk.RIGHT)
        self.header_separator = ttk.Frame(
            self,
            height=header_spec["separator_height"],
            style=str(header_spec["separator"]),
        )
        self.header_separator.pack(side=tk.TOP, fill=tk.X)

        toolbar_spec = toolbar_layout_spec()
        toolbar = ttk.Frame(self, padding=toolbar_spec["padding"], style=str(toolbar_spec["frame"]))
        toolbar.pack(side=tk.TOP, fill=tk.X)
        self.toolbar_frame = toolbar

        ttk.Label(toolbar, text="Port", style=str(toolbar_label_spec()["style"])).pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        toolbar_styles = toolbar_control_styles()
        self.port_combo = ttk.Combobox(
            toolbar,
            textvariable=self.port_var,
            width=int(toolbar_spec["port_width"]),
            style=toolbar_styles["port"],
        )
        self.port_combo.pack(side=tk.LEFT, padx=toolbar_spec["port_padding"])
        self.refresh_button = ttk.Button(
            toolbar,
            text="Refresh",
            command=self.refresh_ports,
            style=toolbar_button_style("Refresh"),
        )
        self.refresh_button.pack(side=tk.LEFT, padx=toolbar_spec["refresh_padding"])
        self.connect_button = ttk.Button(
            toolbar,
            text="Connect",
            command=self.connect,
            style=toolbar_button_style("Connect"),
        )
        self.connect_button.pack(side=tk.LEFT, padx=toolbar_spec["primary_action_padding"])
        self.start_button = ttk.Button(
            toolbar,
            text="Start",
            command=self.start,
            style=toolbar_button_style("Start"),
        )
        self.start_button.pack(side=tk.LEFT, padx=toolbar_spec["inline_action_padding"])
        self.stop_button = ttk.Button(
            toolbar,
            text="Stop",
            command=self.stop,
            style=toolbar_button_style("Stop"),
        )
        self.stop_button.pack(side=tk.LEFT)
        self.toolbar_acquisition_separator = ttk.Frame(
            toolbar,
            width=toolbar_spec["separator_width"],
            style="ToolbarSeparator.TFrame",
        )
        self.toolbar_acquisition_separator.pack(
            side=tk.LEFT,
            fill=tk.Y,
            padx=toolbar_group_padding()["separator"],
        )

        self.save_var = tk.BooleanVar(value=True)
        self.save_check = ttk.Checkbutton(
            toolbar,
            text="Save CSV",
            variable=self.save_var,
            style=toolbar_styles["toggle"],
        )
        self.save_check.pack(side=tk.LEFT, padx=toolbar_spec["save_padding"])

        display_toolbar = ttk.Frame(self, padding=toolbar_spec["padding"], style=str(toolbar_spec["frame"]))
        display_toolbar.pack(side=tk.TOP, fill=tk.X)
        self.display_toolbar_frame = display_toolbar
        toolbar = display_toolbar
        self.autoscale_var = tk.BooleanVar(value=True)
        self.autoscale_check = ttk.Checkbutton(
            toolbar,
            text="Auto scale",
            variable=self.autoscale_var,
            command=self._refresh_display_plots,
            style=toolbar_styles["toggle"],
        )
        self.autoscale_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
        self.highpass_filter_var = tk.BooleanVar(value=DEFAULT_FILTER_SETTINGS.highpass_enabled)
        self.highpass_filter_check = ttk.Checkbutton(
            toolbar,
            text="HP",
            variable=self.highpass_filter_var,
            command=self._refresh_display_plots,
            style=toolbar_styles["toggle"],
        )
        self.highpass_filter_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
        self.notch_filter_var = tk.BooleanVar(value=DEFAULT_FILTER_SETTINGS.notch_enabled)
        self.notch_filter_check = ttk.Checkbutton(
            toolbar,
            text="Notch",
            variable=self.notch_filter_var,
            command=self._refresh_display_plots,
            style=toolbar_styles["toggle"],
        )
        self.notch_filter_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
        self.lowpass_filter_var = tk.BooleanVar(value=DEFAULT_FILTER_SETTINGS.lowpass_enabled)
        self.lowpass_filter_check = ttk.Checkbutton(
            toolbar,
            text="LP",
            variable=self.lowpass_filter_var,
            command=self._refresh_display_plots,
            style=toolbar_styles["toggle"],
        )
        self.lowpass_filter_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
        self.filter_var = tk.BooleanVar(value=DEFAULT_FILTER_SETTINGS.bandpass_enabled)
        self.filter_check = ttk.Checkbutton(
            toolbar,
            text="Bandpass",
            variable=self.filter_var,
            command=self._refresh_display_plots,
            style=toolbar_styles["toggle"],
        )
        self.filter_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
        self.display_filter_separator = ttk.Frame(
            toolbar,
            width=toolbar_spec["separator_width"],
            style="ToolbarSeparator.TFrame",
        )
        self.display_filter_separator.pack(
            side=tk.LEFT,
            fill=tk.Y,
            padx=toolbar_group_padding()["separator"],
        )
        self.display_window_var = tk.StringVar(value=f"{DEFAULT_DISPLAY_SETTINGS.time_window_seconds:g} s")
        ttk.Label(toolbar, text="Window", style=str(toolbar_label_spec()["style"])).pack(
            side=tk.LEFT,
            padx=toolbar_spec["display_label_padding"],
        )
        self.display_window_combo = ttk.Combobox(
            toolbar,
            textvariable=self.display_window_var,
            width=int(toolbar_spec["display_width"]),
            values=display_window_labels(),
            state="readonly",
            style=toolbar_styles["port"],
        )
        self.display_window_combo.pack(side=tk.LEFT, padx=toolbar_spec["display_control_padding"])
        self.display_window_combo.bind("<<ComboboxSelected>>", self._refresh_display_plots)
        self.display_gain_var = tk.StringVar(value=f"{DEFAULT_DISPLAY_SETTINGS.gain:g}x")
        ttk.Label(toolbar, text="Gain", style=str(toolbar_label_spec()["style"])).pack(
            side=tk.LEFT,
            padx=toolbar_spec["display_label_padding"],
        )
        self.display_gain_combo = ttk.Combobox(
            toolbar,
            textvariable=self.display_gain_var,
            width=int(toolbar_spec["display_width"]),
            values=display_gain_labels(),
            state="readonly",
            style=toolbar_styles["port"],
        )
        self.display_gain_combo.pack(side=tk.LEFT, padx=toolbar_spec["display_control_padding"])
        self.display_gain_combo.bind("<<ComboboxSelected>>", self._refresh_display_plots)
        self.sweep_speed_var = tk.StringVar(value=f"{DEFAULT_DISPLAY_SETTINGS.sweep_speed_mm_s} mm/s")
        ttk.Label(toolbar, text="Speed", style=str(toolbar_label_spec()["style"])).pack(
            side=tk.LEFT,
            padx=toolbar_spec["display_label_padding"],
        )
        self.sweep_speed_combo = ttk.Combobox(
            toolbar,
            textvariable=self.sweep_speed_var,
            width=int(toolbar_spec["display_width"]),
            values=sweep_speed_labels(),
            state="readonly",
            style=toolbar_styles["port"],
        )
        self.sweep_speed_combo.pack(side=tk.LEFT, padx=toolbar_spec["display_control_padding"])
        self.sweep_speed_combo.bind("<<ComboboxSelected>>", self._refresh_display_plots)
        self.toolbar_context_separator = ttk.Frame(
            toolbar,
            width=toolbar_spec["separator_width"],
            style="ToolbarSeparator.TFrame",
        )
        self.toolbar_context_separator.pack(
            side=tk.LEFT,
            fill=tk.Y,
            padx=toolbar_group_padding()["separator"],
        )
        self.source_var = tk.StringVar(value=ADS1292R_ECG_SOURCE)
        self._build_toolbar_hint_chip(toolbar, "CH2 ECG / CH1 Resp / Contact")

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.body_pane = body
        workspace_spec = workspace_layout_spec()
        sidebar_spec = sidebar_layout_spec()
        side_shell = ttk.Frame(
            body,
            width=sidebar_spec["width"],
            padding=sidebar_spec["padding"],
            style=str(sidebar_spec["shell"]),
        )
        self.sidebar_shell = side_shell
        body.add(side_shell, weight=workspace_spec["sidebar_weight"])
        sidebar = self._build_sidebar(side_shell)
        status_side = sidebar["Status"]
        session_side = sidebar["Session"]
        validation_side = sidebar["Validation"]
        protocol_side = sidebar["Protocol"]
        actions_side = sidebar["Actions"]
        main = ttk.Frame(body, padding=workspace_spec["main_padding"], style=str(workspace_spec["main"]))
        self.main_workspace = main
        body.add(main, weight=workspace_spec["main_weight"])

        self.metrics_var = tk.StringVar(value="No session")
        self.quality_var = tk.StringVar(value="Quality: --")
        self.path_var = tk.StringVar(value="CSV: --")
        self.workflow_hint_var = tk.StringVar(value="")
        self.status_overview_var = tk.StringVar(value="")
        self.status_card_vars = {label: tk.StringVar(value="") for label in STATUS_CARD_LABELS}
        self.status_card_label_widgets: dict[str, ttk.Label] = {}
        self.status_card_value_labels: dict[str, ttk.Label] = {}
        self.status_card_tone_stripes: dict[str, tk.Frame] = {}
        self.status_detail_value_labels: dict[str, ttk.Label] = {}
        self.signal_card_vars = {label: tk.StringVar(value="") for label in SIGNAL_CARD_LABELS}
        self.signal_card_label_widgets: dict[str, ttk.Label] = {}
        self.signal_card_value_labels: dict[str, ttk.Label] = {}
        self.signal_card_tone_stripes: dict[str, tk.Frame] = {}
        self.session_id_var = tk.StringVar(value="untitled-session")
        self.subject_id_var = tk.StringVar(value="anonymous")
        self.electrode_var = tk.StringVar(value="commercial Ag/AgCl control")
        self.montage_var = tk.StringVar(value="RA/LA/RL torso")
        self.operator_var = tk.StringVar(value="")
        self.notes_var = tk.StringVar(value="")
        self.event_label_var = tk.StringVar(value="motion")
        self.event_notes_var = tk.StringVar(value="")
        self.event_count_var = tk.StringVar(value="0 events")
        self.event_count_label: ttk.Label | None = None
        self.calibration_label_var = tk.StringVar(value="ADS1292 default")
        self.vref_mv_var = tk.StringVar(value="2420")
        self.pga_gain_var = tk.StringVar(value="6")
        self.gate_min_duration_var = tk.StringVar(value="8")
        self.gate_min_contact_var = tk.StringVar(value="95")
        self.gate_min_r_peaks_var = tk.StringVar(value="5")
        self.gate_min_hr_var = tk.StringVar(value="35")
        self.gate_max_hr_var = tk.StringVar(value="180")
        self.gate_require_qrs_var = tk.BooleanVar(value=True)
        self.gate_max_drift_var = tk.StringVar(value="")
        self.gate_max_noise_var = tk.StringVar(value="")
        self.gate_max_ptp_var = tk.StringVar(value="")
        protocol = protocol_template()
        self.protocol_name_var = tk.StringVar(value=protocol.name)
        self.protocol_objective_var = tk.StringVar(value=protocol.objective)
        self.protocol_steps_var = tk.StringVar(value=_format_protocol_steps(protocol.steps))
        self.protocol_acceptance_var = tk.StringVar(value=protocol.acceptance_notes)
        self.protocol_note_labels: dict[str, ttk.Label] = {}
        ttk.Label(status_side, text="Next Step", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 6))
        self._build_workflow_hint(status_side)
        ttk.Label(status_side, text="Overview", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 6))
        self._build_status_cards(status_side)
        ttk.Label(status_side, text="Signal Quality", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 6))
        self._build_signal_quality_cards(status_side)
        for label, var in (
            ("Session", self.metrics_var),
            ("Quality", self.quality_var),
            ("Storage", self.path_var),
        ):
            self._build_status_detail_card(status_side, label, var)

        ttk.Label(session_side, text="Recording Notes", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
        self._metadata_entry(session_side, "Session ID", self.session_id_var)
        self._metadata_entry(session_side, "Subject", self.subject_id_var)
        self._metadata_entry(session_side, "Electrode", self.electrode_var)
        self._metadata_entry(session_side, "Montage", self.montage_var)
        self._metadata_entry(session_side, "Operator", self.operator_var)
        self._metadata_entry(session_side, "Notes", self.notes_var)
        ttk.Label(session_side, text="Events", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
        self._metadata_entry(session_side, "Event label", self.event_label_var)
        self._metadata_entry(session_side, "Event notes", self.event_notes_var)
        self.add_event_button = ttk.Button(
            session_side,
            text="Add Event",
            command=self.add_event,
            style=sidebar_action_button_style(),
        )
        self.add_event_button.pack(anchor=tk.W, fill=tk.X, pady=(6, 2))
        self._build_event_count_card(session_side)

        ttk.Label(validation_side, text="Calibration", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
        self._metadata_entry(validation_side, "Label", self.calibration_label_var)
        self._metadata_entry(validation_side, "Vref mV", self.vref_mv_var)
        self._metadata_entry(validation_side, "PGA gain", self.pga_gain_var)
        ttk.Label(validation_side, text="Quality Gate", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
        self._metadata_entry(validation_side, "Min duration s", self.gate_min_duration_var)
        self._metadata_entry(validation_side, "Min contact %", self.gate_min_contact_var)
        self._metadata_entry(validation_side, "Min R peaks", self.gate_min_r_peaks_var)
        self._metadata_entry(validation_side, "HR min bpm", self.gate_min_hr_var)
        self._metadata_entry(validation_side, "HR max bpm", self.gate_max_hr_var)
        self.gate_require_qrs_check = ttk.Checkbutton(
            validation_side,
            text="Require QRS clear",
            variable=self.gate_require_qrs_var,
            style=sidebar_field_styles()["check"],
        )
        self.gate_require_qrs_check.pack(anchor=tk.W, pady=(5, 2))
        self._metadata_entry(validation_side, "Max drift counts", self.gate_max_drift_var)
        self._metadata_entry(validation_side, "Max noise RMS", self.gate_max_noise_var)
        self._metadata_entry(validation_side, "Max peak-to-peak", self.gate_max_ptp_var)

        ttk.Label(protocol_side, text="Protocol", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
        self._metadata_entry(protocol_side, "Name", self.protocol_name_var)
        self._metadata_entry(protocol_side, "Objective", self.protocol_objective_var)
        self._build_protocol_note_card(protocol_side, "Steps", self.protocol_steps_var)
        self._build_protocol_note_card(protocol_side, "Acceptance", self.protocol_acceptance_var)

        self.action_section_labels: dict[str, ttk.Label] = {}
        self._build_action_section_heading(actions_side, "Review", top_padding=8)
        self.load_csv_button = ttk.Button(
            actions_side,
            text="Load CSV",
            command=self.load_csv,
            style=sidebar_action_button_style(),
        )
        self.load_csv_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self.export_report_button = ttk.Button(
            actions_side,
            text="Export Report",
            command=self.export_report,
            style=sidebar_action_button_style(),
        )
        self.export_report_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self._build_action_section_heading(actions_side, "Package")
        self.export_package_button = ttk.Button(
            actions_side,
            text="Export Package",
            command=self.export_package,
            style=sidebar_action_button_style(),
        )
        self.export_package_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self.verify_package_button = ttk.Button(
            actions_side,
            text="Verify Package",
            command=self.verify_package,
            style=sidebar_action_button_style(),
        )
        self.verify_package_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self._build_action_section_heading(actions_side, "Library")
        self.batch_compare_button = ttk.Button(
            actions_side,
            text="Batch Compare",
            command=self.batch_compare,
            style=sidebar_action_button_style(),
        )
        self.batch_compare_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self.session_index_button = ttk.Button(
            actions_side,
            text="Session Index",
            command=self.session_index,
            style=sidebar_action_button_style(),
        )
        self.session_index_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self._build_action_section_heading(actions_side, "Safety")
        self._build_safety_notice(actions_side)

        self.notebook = ttk.Notebook(main, style=workspace_notebook_styles()["notebook"])
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.live_tab = ttk.Frame(self.notebook)
        self.review_tab = ttk.Frame(self.notebook)
        self.pqrst_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)
        live_label, review_label, pqrst_label, log_label = main_tab_labels()
        self.notebook.add(self.live_tab, text=live_label)
        self.notebook.add(self.review_tab, text=review_label)
        self.notebook.add(self.pqrst_tab, text=pqrst_label)
        self.notebook.add(self.log_tab, text=log_label)

        self._build_live_plot()
        self._build_review_plot()
        self._build_pqrst_plot()
        self._build_log_panel()
        self.control_buttons = {
            "Refresh": self.refresh_button,
            "Connect": self.connect_button,
            "Start": self.start_button,
            "Stop": self.stop_button,
            "Load CSV": self.load_csv_button,
            "Export Report": self.export_report_button,
            "Export Package": self.export_package_button,
            "Verify Package": self.verify_package_button,
            "Batch Compare": self.batch_compare_button,
            "Session Index": self.session_index_button,
        }
        self._apply_control_states()

    def _configure_status_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        tokens = APP_VISUAL_TOKENS
        base_chrome = base_chrome_spec()
        style.configure(
            ".",
            font=base_chrome["font"],
            background=base_chrome["background"],
            foreground=base_chrome["foreground"],
        )
        style.configure(
            str(base_chrome["frame"]),
            background=base_chrome["background"],
            borderwidth=base_chrome["borderwidth"],
        )
        header_frame = header_frame_spec()
        style.configure(
            str(header_frame["frame"]),
            background=header_frame["background"],
            borderwidth=header_frame["borderwidth"],
        )
        style.configure(
            str(header_frame["separator"]),
            background=header_frame["separator_background"],
            borderwidth=header_frame["borderwidth"],
        )
        toolbar_frame = toolbar_frame_spec()
        style.configure(
            str(toolbar_frame["frame"]),
            background=toolbar_frame["background"],
            borderwidth=toolbar_frame["borderwidth"],
            relief=toolbar_frame["relief"],
        )
        style.configure(str(toolbar_frame["separator"]), background=toolbar_frame["separator_background"])
        style.configure(str(base_chrome["sidebar"]), background=base_chrome["background"])
        style.configure(str(base_chrome["main"]), background=base_chrome["background"])
        style.configure(
            str(base_chrome["label"]),
            background=base_chrome["background"],
            foreground=base_chrome["foreground"],
            borderwidth=base_chrome["borderwidth"],
        )
        for text_spec in header_text_styles().values():
            style.configure(
                str(text_spec["style"]),
                background=text_spec["background"],
                foreground=text_spec["foreground"],
                font=text_spec["font"],
            )
        connection_pill = header_connection_styles()
        connection_backgrounds = connection_pill["backgrounds"]
        connection_foregrounds = connection_pill["foregrounds"]
        style.configure(
            "Connection.TLabel",
            background=connection_backgrounds["running"],
            foreground=connection_foregrounds["running"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        style.configure(
            "Ready.Connection.TLabel",
            background=connection_backgrounds["ready"],
            foreground=connection_foregrounds["ready"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        style.configure(
            "Running.Connection.TLabel",
            background=connection_backgrounds["running"],
            foreground=connection_foregrounds["running"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        style.configure(
            "Warning.Connection.TLabel",
            background=connection_backgrounds["warning"],
            foreground=connection_foregrounds["warning"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        style.configure(
            "Neutral.Connection.TLabel",
            background=connection_backgrounds["neutral"],
            foreground=connection_foregrounds["neutral"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        toolbar_label = toolbar_label_spec()
        style.configure(
            str(toolbar_label["style"]),
            background=toolbar_label["background"],
            foreground=toolbar_label["foreground"],
            font=toolbar_label["font"],
        )
        toolbar_hint = toolbar_hint_styles()
        style.configure(
            "ToolbarHint.TFrame",
            background=toolbar_hint["background"],
            borderwidth=toolbar_hint["borderwidth"],
            relief=toolbar_hint["relief"],
            bordercolor=toolbar_hint["border"],
            lightcolor=toolbar_hint["border"],
            darkcolor=toolbar_hint["border"],
        )
        style.configure(
            "ToolbarHint.TLabel",
            background=toolbar_hint["background"],
            foreground=toolbar_hint["foreground"],
            font=toolbar_hint["font"],
        )
        input_chrome = input_chrome_spec()
        combobox_chrome = input_chrome["combobox"]
        style.configure(
            "Port.TCombobox",
            fieldbackground=combobox_chrome["fieldbackground"],
            background=combobox_chrome["background"],
            foreground=combobox_chrome["foreground"],
            selectbackground=combobox_chrome["selectbackground"],
            selectforeground=combobox_chrome["selectforeground"],
            arrowcolor=combobox_chrome["arrowcolor"],
            padding=combobox_chrome["padding"],
        )
        style.map(
            "Port.TCombobox",
            foreground=[("disabled", combobox_chrome["disabled_foreground"])],
            fieldbackground=[
                ("disabled", combobox_chrome["disabled_background"]),
                ("readonly", combobox_chrome["fieldbackground"]),
            ],
            background=[
                ("disabled", combobox_chrome["disabled_background"]),
                ("readonly", combobox_chrome["background"]),
            ],
            arrowcolor=[("active", combobox_chrome["active_arrowcolor"])],
        )
        toolbar_toggle = input_chrome["toolbar_toggle"]
        toolbar_toggle_style = toolbar_control_styles()["toggle"]
        style.configure(
            toolbar_toggle_style,
            background=toolbar_toggle["background"],
            foreground=toolbar_toggle["foreground"],
            font=toolbar_toggle["font"],
            padding=toolbar_toggle["padding"],
        )
        style.map(
            toolbar_toggle_style,
            foreground=[
                ("disabled", toolbar_toggle["disabled_foreground"]),
                ("active", toolbar_toggle["active_foreground"]),
            ],
            background=[("active", toolbar_toggle["active_background"])],
        )
        section_heading = section_heading_styles()
        style.configure(
            "SectionHeading.TLabel",
            background=section_heading["background"],
            foreground=section_heading["foreground"],
            font=section_heading["font"],
            padding=section_heading["padding"],
        )
        muted_label = muted_label_spec()
        style.configure(
            str(muted_label["style"]),
            background=muted_label["background"],
            foreground=muted_label["foreground"],
            font=muted_label["font"],
        )
        label_chrome = input_chrome["label"]
        style.configure(
            "FieldLabel.TLabel",
            background=label_chrome["background"],
            foreground=label_chrome["foreground"],
            font=label_chrome["font"],
            padding=label_chrome["padding"],
        )
        action_section = action_section_styles()
        style.configure("ActionSection.TFrame", background=action_section["background"], borderwidth=0)
        style.configure(
            "ActionSection.TLabel",
            background=action_section["background"],
            foreground=action_section["foreground"],
            font=action_section["font"],
            padding=action_section["padding"],
        )
        entry_chrome = input_chrome["entry"]
        style.configure(
            "Field.TEntry",
            fieldbackground=entry_chrome["fieldbackground"],
            foreground=entry_chrome["foreground"],
            insertcolor=entry_chrome["insert"],
            padding=entry_chrome["padding"],
            borderwidth=entry_chrome["borderwidth"],
            relief=entry_chrome["relief"],
        )
        style.map(
            "Field.TEntry",
            foreground=[("disabled", entry_chrome["disabled_foreground"])],
            fieldbackground=[
                ("disabled", entry_chrome["disabled_background"]),
                ("focus", entry_chrome["focus_background"]),
            ],
        )
        check_chrome = input_chrome["check"]
        style.configure(
            "FieldCheck.TCheckbutton",
            background=check_chrome["background"],
            foreground=check_chrome["foreground"],
            padding=check_chrome["padding"],
            font=check_chrome["font"],
        )
        style.map(
            "FieldCheck.TCheckbutton",
            foreground=[
                ("disabled", check_chrome["disabled_foreground"]),
                ("active", check_chrome["active_foreground"]),
            ],
            background=[("active", check_chrome["active_background"])],
        )
        panel_chrome = panel_chrome_spec()
        for panel_style in (
            "Card.TFrame",
            "PlotPanel.TFrame",
            "LogPanel.TFrame",
            "WorkflowHint.TFrame",
            "SafetyNotice.TFrame",
            "StatusDetail.TFrame",
            "EventCount.TFrame",
            "ProtocolNote.TFrame",
        ):
            style.configure(
                panel_style,
                background=panel_chrome["background"],
                borderwidth=panel_chrome["borderwidth"],
                relief=panel_chrome["relief"],
                bordercolor=panel_chrome["border"],
                lightcolor=panel_chrome["border"],
                darkcolor=panel_chrome["border"],
            )
        workflow_hint = workflow_hint_styles()
        safety_notice = safety_notice_styles()
        for notice_style in (workflow_hint, safety_notice):
            style.configure(
                notice_style["frame"],
                background=notice_style["background"],
                borderwidth=panel_chrome["borderwidth"],
                relief=panel_chrome["relief"],
                bordercolor=panel_chrome["border"],
                lightcolor=panel_chrome["border"],
                darkcolor=panel_chrome["border"],
            )
        scrollbar_spec = scrollbar_chrome_spec()
        style.configure(
            str(scrollbar_spec["vertical"]),
            width=scrollbar_spec["width"],
            background=scrollbar_spec["background"],
            troughcolor=scrollbar_spec["trough"],
            bordercolor=scrollbar_spec["border"],
            arrowcolor=scrollbar_spec["arrow"],
            relief=scrollbar_spec["relief"],
            borderwidth=scrollbar_spec["borderwidth"],
        )
        style.map(
            str(scrollbar_spec["vertical"]),
            background=[("active", scrollbar_spec["active_background"])],
            arrowcolor=[("active", scrollbar_spec["active_background"])],
        )
        card_label = card_label_spec()
        style.configure(
            str(card_label["style"]),
            background=card_label["background"],
            foreground=card_label["foreground"],
            font=card_label["font"],
        )
        style.configure(
            workflow_hint["label"],
            background=workflow_hint["background"],
            foreground=workflow_hint["foreground"],
            font=workflow_hint["font"],
        )
        style.configure(
            safety_notice["label"],
            background=safety_notice["background"],
            foreground=safety_notice["foreground"],
            font=safety_notice["font"],
        )
        status_detail = status_detail_styles()
        style.configure(
            status_detail["label"],
            background=status_detail["background"],
            foreground=status_detail["label_foreground"],
            font=status_detail["label_font"],
        )
        style.configure(
            status_detail["value"],
            background=status_detail["background"],
            foreground=status_detail["value_foreground"],
            font=status_detail["value_font"],
        )
        event_count = event_count_styles()
        style.configure(
            event_count["label"],
            background=event_count["background"],
            foreground=event_count["label_foreground"],
            font=event_count["label_font"],
        )
        style.configure(
            event_count["value"],
            background=event_count["background"],
            foreground=event_count["value_foreground"],
            font=event_count["value_font"],
        )
        protocol_note = protocol_note_styles()
        style.configure(
            protocol_note["label"],
            background=protocol_note["background"],
            foreground=protocol_note["label_foreground"],
            font=protocol_note["label_font"],
        )
        style.configure(
            protocol_note["value"],
            background=protocol_note["background"],
            foreground=protocol_note["value_foreground"],
            font=protocol_note["value_font"],
        )
        button_chrome = button_chrome_spec()
        default_button = button_chrome["default"]
        style.configure(
            "TButton",
            padding=default_button["padding"],
            font=default_button["font"],
            foreground=default_button["foreground"],
            background=default_button["background"],
            borderwidth=default_button["borderwidth"],
            relief=default_button["relief"],
        )
        style.map(
            "TButton",
            foreground=[
                ("disabled", default_button["disabled_foreground"]),
                ("active", default_button["active_foreground"]),
            ],
            background=[
                ("disabled", default_button["disabled_background"]),
                ("active", default_button["active_background"]),
            ],
        )
        sidebar_button = button_chrome["sidebar"]
        style.configure(
            "SidebarAction.TButton",
            padding=sidebar_button["padding"],
            font=sidebar_button["font"],
            foreground=sidebar_button["foreground"],
            background=sidebar_button["background"],
            borderwidth=sidebar_button["borderwidth"],
            relief=sidebar_button["relief"],
        )
        style.map(
            "SidebarAction.TButton",
            foreground=[
                ("disabled", sidebar_button["disabled_foreground"]),
                ("active", sidebar_button["active_foreground"]),
            ],
            background=[
                ("disabled", sidebar_button["disabled_background"]),
                ("active", sidebar_button["active_background"]),
            ],
        )
        primary_button = button_chrome["primary"]
        style.configure(
            "Primary.TButton",
            padding=primary_button["padding"],
            font=primary_button["font"],
            foreground=primary_button["foreground"],
            background=primary_button["background"],
            borderwidth=primary_button["borderwidth"],
            relief=primary_button["relief"],
        )
        style.map(
            "Primary.TButton",
            foreground=[
                ("disabled", primary_button["disabled_foreground"]),
                ("active", primary_button["active_foreground"]),
            ],
            background=[
                ("disabled", primary_button["disabled_background"]),
                ("active", primary_button["active_background"]),
            ],
        )
        stop_button = button_chrome["stop"]
        style.configure(
            "Stop.TButton",
            padding=stop_button["padding"],
            font=stop_button["font"],
            foreground=stop_button["foreground"],
            background=stop_button["background"],
            borderwidth=stop_button["borderwidth"],
            relief=stop_button["relief"],
        )
        style.map(
            "Stop.TButton",
            foreground=[
                ("disabled", stop_button["disabled_foreground"]),
                ("active", stop_button["active_foreground"]),
            ],
            background=[
                ("disabled", stop_button["disabled_background"]),
                ("active", stop_button["active_background"]),
            ],
        )
        base_checkbutton = base_checkbutton_style()
        style.configure(
            base_checkbutton["style"],
            background=base_checkbutton["background"],
            foreground=base_checkbutton["foreground"],
        )
        base_notebook = base_notebook_styles()
        style.configure(
            base_notebook["notebook"],
            background=base_notebook["background"],
            borderwidth=base_notebook["borderwidth"],
        )
        style.configure(
            base_notebook["tab"],
            padding=base_notebook["tab_padding"],
            font=base_notebook["tab_font"],
        )
        sidebar_tabs = sidebar_notebook_styles()
        style.configure(
            "Sidebar.TNotebook",
            background=sidebar_tabs["background"],
            borderwidth=sidebar_tabs["borderwidth"],
        )
        style.configure(
            "Sidebar.TNotebook.Tab",
            padding=sidebar_tabs["tab_padding"],
            font=sidebar_tabs["tab_font"],
            foreground=sidebar_tabs["inactive_foreground"],
            background=sidebar_tabs["tab_background"],
        )
        style.map(
            "Sidebar.TNotebook.Tab",
            foreground=[
                ("selected", sidebar_tabs["selected_foreground"]),
                ("active", sidebar_tabs["active_foreground"]),
            ],
            background=[
                ("selected", sidebar_tabs["active_background"]),
                ("active", sidebar_tabs["active_background"]),
            ],
        )
        workspace_tabs = workspace_notebook_styles()
        style.configure(
            "Workspace.TNotebook",
            background=workspace_tabs["background"],
            borderwidth=workspace_tabs["borderwidth"],
        )
        style.configure(
            "Workspace.TNotebook.Tab",
            padding=workspace_tabs["tab_padding"],
            font=workspace_tabs["tab_font"],
            foreground=workspace_tabs["inactive_foreground"],
            background=workspace_tabs["tab_background"],
        )
        style.map(
            "Workspace.TNotebook.Tab",
            foreground=[
                ("selected", workspace_tabs["selected_foreground"]),
                ("active", workspace_tabs["active_foreground"]),
            ],
            background=[
                ("selected", workspace_tabs["active_background"]),
                ("active", workspace_tabs["active_background"]),
            ],
        )
        status_label = status_label_spec()
        status_backgrounds = status_label["backgrounds"]
        status_foregrounds = status_label["foregrounds"]
        style.configure(
            "Ready.Status.TLabel",
            background=status_backgrounds["ready"],
            foreground=status_foregrounds["ready"],
            font=status_label["font"],
            padding=status_label["padding"],
        )
        style.configure(
            "Running.Status.TLabel",
            background=status_backgrounds["running"],
            foreground=status_foregrounds["running"],
            font=status_label["font"],
            padding=status_label["padding"],
        )
        style.configure(
            "Warning.Status.TLabel",
            background=status_backgrounds["warning"],
            foreground=status_foregrounds["warning"],
            font=status_label["font"],
            padding=status_label["padding"],
        )
        style.configure(
            "Neutral.Status.TLabel",
            background=status_backgrounds["neutral"],
            foreground=status_foregrounds["neutral"],
            font=status_label["font"],
            padding=status_label["padding"],
        )

    def _build_workflow_hint(self, parent: ttk.Frame) -> None:
        styles = workflow_hint_styles()
        spec = sidebar_text_card_spec()
        self.workflow_hint_frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        self.workflow_hint_frame.pack(anchor=tk.W, fill=tk.X, pady=(0, 4))
        self.workflow_hint_stripe = tk.Frame(
            self.workflow_hint_frame,
            width=spec["stripe_width"],
            bg=styles["stripe"],
            highlightthickness=0,
        )
        self.workflow_hint_stripe.pack(side=tk.LEFT, fill=tk.Y)
        self.workflow_hint_label = ttk.Label(
            self.workflow_hint_frame,
            textvariable=self.workflow_hint_var,
            wraplength=spec["primary_wrap"],
            justify=tk.LEFT,
            style=styles["label"],
            padding=spec["label_padding"],
        )
        self.workflow_hint_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_safety_notice(self, parent: ttk.Frame) -> None:
        styles = safety_notice_styles()
        spec = sidebar_text_card_spec()
        self.safety_notice_frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        self.safety_notice_frame.pack(anchor=tk.W, fill=tk.X, pady=(0, 4))
        self.safety_notice_stripe = tk.Frame(
            self.safety_notice_frame,
            width=spec["stripe_width"],
            bg=styles["stripe"],
            highlightthickness=0,
        )
        self.safety_notice_stripe.pack(side=tk.LEFT, fill=tk.Y)
        self.safety_notice_label = ttk.Label(
            self.safety_notice_frame,
            text="Research use only. Use battery power during human-subject measurements.",
            wraplength=spec["primary_wrap"],
            justify=tk.LEFT,
            style=styles["label"],
            padding=spec["label_padding"],
        )
        self.safety_notice_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_toolbar_hint_chip(self, parent: ttk.Frame, text: str) -> None:
        styles = toolbar_hint_styles()
        self.toolbar_hint_chip = ttk.Frame(
            parent,
            padding=toolbar_layout_spec()["hint_padding"],
            style=styles["frame"],
        )
        self.toolbar_hint_chip.pack(side=tk.LEFT)
        self.toolbar_hint_label = ttk.Label(self.toolbar_hint_chip, text=text, style=styles["label"])
        self.toolbar_hint_label.pack(side=tk.LEFT)

    def _build_action_section_heading(self, parent: ttk.Frame, text: str, *, top_padding: int = 14) -> None:
        styles = action_section_styles()
        frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        frame.pack(anchor=tk.W, fill=tk.X, pady=(top_padding, 4))
        label = ttk.Label(frame, text=text, style=styles["label"])
        label.pack(anchor=tk.W)
        self.action_section_labels[text] = label

    def _build_status_detail_card(self, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
        styles = status_detail_styles()
        spec = sidebar_text_card_spec()
        row = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        row.pack(anchor=tk.W, fill=tk.X, pady=3)
        stripe = tk.Frame(row, width=spec["stripe_width"], bg=styles["stripe"], highlightthickness=0)
        stripe.pack(side=tk.LEFT, fill=tk.Y)
        content = ttk.Frame(row, padding=spec["content_padding"], style=styles["frame"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(content, text=label, style=styles["label"]).pack(anchor=tk.W)
        value_label = ttk.Label(
            content,
            textvariable=variable,
            wraplength=styles["value_wrap"],
            justify=tk.LEFT,
            style=styles["value"],
        )
        value_label.pack(anchor=tk.W, fill=tk.X, pady=spec["value_top_padding"])
        self.status_detail_value_labels[label] = value_label

    def _build_event_count_card(self, parent: ttk.Frame) -> None:
        styles = event_count_styles()
        spec = sidebar_text_card_spec()
        row = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        row.pack(anchor=tk.W, fill=tk.X, pady=(7, 2))
        stripe = tk.Frame(row, width=spec["stripe_width"], bg=styles["stripe"], highlightthickness=0)
        stripe.pack(side=tk.LEFT, fill=tk.Y)
        content = ttk.Frame(row, padding=spec["content_padding"], style=styles["frame"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(content, text="Event markers", style=styles["label"]).pack(anchor=tk.W)
        self.event_count_label = ttk.Label(
            content,
            textvariable=self.event_count_var,
            wraplength=spec["detail_wrap"],
            justify=tk.LEFT,
            style=styles["value"],
        )
        self.event_count_label.pack(anchor=tk.W, fill=tk.X, pady=spec["value_top_padding"])

    def _build_protocol_note_card(self, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
        styles = protocol_note_styles()
        spec = sidebar_text_card_spec()
        row = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        row.pack(anchor=tk.W, fill=tk.X, pady=(8, 2))
        stripe = tk.Frame(row, width=spec["stripe_width"], bg=styles["stripe"], highlightthickness=0)
        stripe.pack(side=tk.LEFT, fill=tk.Y)
        content = ttk.Frame(row, padding=spec["content_padding"], style=styles["frame"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(content, text=label, style=styles["label"]).pack(anchor=tk.W)
        value_label = ttk.Label(
            content,
            textvariable=variable,
            wraplength=spec["detail_wrap"],
            justify=tk.LEFT,
            style=styles["value"],
        )
        value_label.pack(anchor=tk.W, fill=tk.X, pady=spec["value_top_padding"])
        self.protocol_note_labels[label] = value_label

    def _build_status_cards(self, parent: ttk.Frame) -> None:
        card_label = card_label_spec()
        for label in STATUS_CARD_LABELS:
            row = ttk.Frame(parent, padding=(0, 0), style="Card.TFrame")
            row.pack(anchor=tk.W, fill=tk.X, pady=card_label["row_padding"])
            stripe = tk.Frame(
                row,
                width=int(card_label["stripe_width"]),
                bg=status_tone_color("neutral"),
                highlightthickness=0,
            )
            stripe.pack(side=tk.LEFT, fill=tk.Y)
            content = ttk.Frame(row, padding=card_label["content_padding"], style="Card.TFrame")
            content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            label_widget = ttk.Label(content, text=label, width=int(card_label["width"]), style=str(card_label["style"]))
            label_widget.pack(side=tk.LEFT)
            value_label = ttk.Label(
                content,
                textvariable=self.status_card_vars[label],
                style=status_tone_style("neutral"),
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=card_label["value_padding"])
            self.status_card_label_widgets[label] = label_widget
            self.status_card_tone_stripes[label] = stripe
            self.status_card_value_labels[label] = value_label

    def _build_signal_quality_cards(self, parent: ttk.Frame) -> None:
        card_label = card_label_spec()
        for label in SIGNAL_CARD_LABELS:
            row = ttk.Frame(parent, padding=(0, 0), style="Card.TFrame")
            row.pack(anchor=tk.W, fill=tk.X, pady=card_label["row_padding"])
            stripe = tk.Frame(
                row,
                width=int(card_label["stripe_width"]),
                bg=status_tone_color("neutral"),
                highlightthickness=0,
            )
            stripe.pack(side=tk.LEFT, fill=tk.Y)
            content = ttk.Frame(row, padding=card_label["content_padding"], style="Card.TFrame")
            content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            label_widget = ttk.Label(content, text=label, width=int(card_label["width"]), style=str(card_label["style"]))
            label_widget.pack(side=tk.LEFT)
            value_label = ttk.Label(
                content,
                textvariable=self.signal_card_vars[label],
                style=status_tone_style("neutral"),
                wraplength=card_label["signal_value_wrap"],
                justify=tk.LEFT,
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=card_label["value_padding"])
            self.signal_card_label_widgets[label] = label_widget
            self.signal_card_tone_stripes[label] = stripe
            self.signal_card_value_labels[label] = value_label

    def _build_sidebar(self, parent: ttk.Frame) -> dict[str, ttk.Frame]:
        spec = sidebar_layout_spec()
        self.sidebar_notebook = ttk.Notebook(parent, style=sidebar_notebook_styles()["notebook"])
        self.sidebar_notebook.pack(fill=tk.BOTH, expand=True)
        self.sidebar_scrolls: dict[str, ScrollableFrame] = {}
        sections: dict[str, ttk.Frame] = {}
        for label in SIDEBAR_TABS:
            tab = ttk.Frame(self.sidebar_notebook)
            scroll = ScrollableFrame(tab, width=int(spec["scroll_width"]))
            scroll.frame.pack(fill=tk.BOTH, expand=True)
            self.sidebar_notebook.add(tab, text=label)
            self.sidebar_scrolls[label] = scroll
            sections[label] = scroll.content
        return sections

    def _metadata_entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
        styles = sidebar_field_styles()
        ttk.Label(parent, text=label, style=styles["label"]).pack(anchor=tk.W, pady=(8, 2))
        ttk.Entry(parent, textvariable=variable, style=styles["entry"]).pack(anchor=tk.W, fill=tk.X)

    def _build_live_plot(self) -> None:
        fig = self._new_plot_figure(figsize=(10, 7))
        fig.subplots_adjust(**plot_figure_layouts()["three_panel"])
        self.ax_live_ecg = fig.add_subplot(311)
        self.ax_live_resp = fig.add_subplot(312, sharex=self.ax_live_ecg)
        self.ax_live_status = fig.add_subplot(313, sharex=self.ax_live_ecg)
        for ax in (self.ax_live_ecg, self.ax_live_resp, self.ax_live_status):
            ax.label_outer()
        self._style_signal_axes((self.ax_live_ecg, self.ax_live_resp, self.ax_live_status))
        self.ax_live_ecg.set_ylabel("display counts")
        self.ax_live_resp.set_ylabel("counts")
        self.ax_live_status.set_xlabel("Time (s)")
        self._configure_live_time_axis()
        trace_styles = plot_trace_styles()
        self.live_ecg_line, = self.ax_live_ecg.plot([], [], color=PLOT_TRACE_COLORS["ecg"], **trace_styles["ecg"])
        self.live_peak_line, = self.ax_live_ecg.plot([], [], color=PLOT_TRACE_COLORS["peak"], **trace_styles["peak"])
        self.live_resp_line, = self.ax_live_resp.plot(
            [],
            [],
            color=PLOT_TRACE_COLORS["respiration"],
            **trace_styles["respiration"],
        )
        self.live_status_line, = self.ax_live_status.plot(
            [],
            [],
            color=PLOT_TRACE_COLORS["contact"],
            **trace_styles["contact"],
        )
        self._show_empty_plot_state("live", (self.ax_live_ecg, self.ax_live_resp, self.ax_live_status))
        self.live_canvas = self._build_plot_canvas(self.live_tab, fig, name="live")

    def _configure_live_time_axis(self) -> None:
        spec = live_axis_spec()
        for ax in (self.ax_live_ecg, self.ax_live_resp, self.ax_live_status):
            ax.xaxis.set_major_locator(MultipleLocator(float(spec["x_major_tick_seconds"])))

    def _build_review_plot(self) -> None:
        fig = self._new_plot_figure(figsize=(10, 7))
        fig.subplots_adjust(**plot_figure_layouts()["three_panel"])
        self.ax_review_ecg = fig.add_subplot(311)
        self.ax_review_resp = fig.add_subplot(312, sharex=self.ax_review_ecg)
        self.ax_review_status = fig.add_subplot(313, sharex=self.ax_review_ecg)
        for ax in (self.ax_review_ecg, self.ax_review_resp, self.ax_review_status):
            ax.label_outer()
        self._style_signal_axes((self.ax_review_ecg, self.ax_review_resp, self.ax_review_status))
        self.ax_review_status.set_xlabel("Time (s)")
        self.ax_review_ecg.set_ylabel("display counts")
        self.ax_review_resp.set_ylabel("counts")
        trace_styles = plot_trace_styles()
        self.review_ecg_line, = self.ax_review_ecg.plot([], [], color=PLOT_TRACE_COLORS["ecg"], **trace_styles["ecg"])
        self.review_peak_line, = self.ax_review_ecg.plot([], [], color=PLOT_TRACE_COLORS["peak"], **trace_styles["peak"])
        self.review_resp_line, = self.ax_review_resp.plot(
            [],
            [],
            color=PLOT_TRACE_COLORS["respiration"],
            **trace_styles["respiration"],
        )
        self.review_status_line, = self.ax_review_status.plot(
            [],
            [],
            color=PLOT_TRACE_COLORS["contact"],
            **trace_styles["contact"],
        )
        self._show_empty_plot_state("review", (self.ax_review_ecg, self.ax_review_resp, self.ax_review_status))
        self.review_canvas = self._build_plot_canvas(self.review_tab, fig, name="review")

    def _build_pqrst_plot(self) -> None:
        fig = self._new_plot_figure(figsize=(10, 6))
        fig.subplots_adjust(**plot_figure_layouts()["single_panel"])
        self.ax_pqrst = fig.add_subplot(111)
        self._style_signal_axes((self.ax_pqrst,))
        self.ax_pqrst.set_xlabel("Time relative to R peak (ms)")
        self.ax_pqrst.set_ylabel("Filtered counts")
        self._show_empty_plot_state("pqrst", (self.ax_pqrst,))
        self.pqrst_canvas = self._build_plot_canvas(self.pqrst_tab, fig, name="pqrst")

    def _build_plot_canvas(self, parent: ttk.Frame, fig: Figure, *, name: str) -> FigureCanvasTkAgg:
        spec = plot_panel_spec()
        shell = ttk.Frame(parent, padding=spec["padding"], style=str(spec["shell"]))
        shell.pack(fill=tk.BOTH, expand=True)
        panel = ttk.Frame(shell, padding=spec["panel_padding"], style=str(spec["panel"]))
        panel.pack(fill=tk.BOTH, expand=True)
        setattr(self, f"{name}_plot_shell", shell)
        setattr(self, f"{name}_plot_panel", panel)
        canvas = FigureCanvasTkAgg(fig, master=panel)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.configure(**plot_canvas_widget_style())
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        return canvas

    def _build_log_panel(self) -> None:
        spec = log_panel_spec()
        shell = ttk.Frame(self.log_tab, padding=spec["padding"], style=str(spec["shell"]))
        shell.pack(fill=tk.BOTH, expand=True)
        panel = ttk.Frame(shell, padding=spec["panel_padding"], style=str(spec["panel"]))
        panel.pack(fill=tk.BOTH, expand=True)
        self.log_shell = shell
        self.log_panel = panel
        scrollbar_spec = scrollbar_chrome_spec()
        self.log_scrollbar = ttk.Scrollbar(
            panel,
            orient=str(spec["scrollbar"]),
            style=str(scrollbar_spec["vertical"]),
        )
        text_padding = spec["text_padding"]
        self.log_text = tk.Text(
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
            yscrollcommand=self.log_scrollbar.set,
        )
        self.log_scrollbar.configure(command=self.log_text.yview)
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _new_plot_figure(self, *, figsize: tuple[float, float]) -> Figure:
        apply_seaborn_plot_theme()
        fig = Figure(figsize=figsize, dpi=100)
        fig.patch.set_facecolor(APP_VISUAL_TOKENS["surface"])
        return fig

    def _style_signal_axes(self, axes: tuple[object, ...]) -> None:
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
            self._set_signal_axis_title(ax, ax.get_title())
            sns.despine(ax=ax, top=True, right=True, left=False, bottom=False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(style["spine"])
                ax.spines[side].set_linewidth(style["spine_linewidth"])

    def _set_signal_axis_title(self, ax: object, title: str) -> None:
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

    def _show_empty_plot_state(self, key: str, axes: tuple[object, ...]) -> None:
        style = empty_plot_style()
        for ax, message in zip(axes, EMPTY_PLOT_MESSAGES[key]):
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
            self.empty_plot_artists.append(artist)

    def _clear_empty_plot_state(self) -> None:
        while self.empty_plot_artists:
            artist = self.empty_plot_artists.pop()
            try:
                artist.remove()
            except ValueError:
                pass

    def refresh_ports(self) -> None:
        ports = list_ads_ports()
        values = [port.device for port in ports]
        if not values:
            guess = find_ads_port()
            values = [guess] if guess else []
        self.port_combo["values"] = values
        if values and not self.port_var.get():
            self.port_var.set(values[0])
        if not values:
            self.connection_var.set("No ADS1x9x port")

    def connect(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("No port", "Select an ADS1x9x serial port first.")
            return
        if self.is_connecting:
            self._log("Connect already in progress")
            return
        self.is_connecting = True
        self.connection_var.set("Connecting...")
        self._apply_control_states()
        threading.Thread(
            target=self._connect_in_background,
            args=(port,),
            daemon=True,
        ).start()

    def _connect_in_background(self, port: str) -> None:
        try:
            with Ads1x9xDevice(port) as device:
                firmware = device.query_firmware()
                try:
                    device_id = device.read_register(0x00)
                    detail = f"firmware {firmware}, ID 0x{device_id:02X}"
                except Exception:
                    detail = f"firmware {firmware}"
            self.connect_results.put(ConnectResult(port=port, detail=detail))
        except Exception as exc:
            self.connect_results.put(ConnectResult(port=port, error=str(exc)))

    def _drain_connect_results(self) -> None:
        while True:
            try:
                result = self.connect_results.get_nowait()
            except queue.Empty:
                return
            self._finish_connect(result)

    def _finish_connect(self, result: ConnectResult) -> None:
        self.is_connecting = False
        if result.error:
            self.connected_port = None
            self.connection_var.set("Connection failed")
            self._log(f"Connect failed for {result.port}: {result.error}")
            messagebox.showerror("Connection failed", result.error)
        else:
            self.connected_port = result.port
            self.connection_var.set(f"Connected: {result.detail}")
            self._log(f"Connected to {result.port}: {result.detail}")
        self._apply_control_states()

    def start(self) -> None:
        port = self.port_var.get().strip()
        if not port:
            messagebox.showerror("No port", "Select a port and press Connect first.")
            return
        if self.connected_port != port:
            messagebox.showerror("Not connected", "Press Connect before Start.")
            return
        self._clear_buffers()
        self.recording_path = None
        csv_path = None
        if self.save_var.get():
            stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            csv_path = Path("recordings") / f"{stamp}-ads1292-studio.csv"
            self.recording_path = csv_path
            write_metadata_json(csv_path.with_suffix(".json"), self._metadata())
            write_events_json(self._events_path(csv_path), self.event_markers)
            write_calibration_json(self._calibration_path(csv_path), self._calibration())
            write_protocol_json(self._protocol_path(csv_path), self._protocol())
            write_quality_gate_json(self._quality_gate_path(csv_path), self._quality_gate())
            self.path_var.set(f"CSV: {csv_path}")
        self.is_starting = True
        self.connection_var.set("Starting stream...")
        self.worker.start(port, csv_path)
        self._apply_control_states()

    def stop(self) -> None:
        self.worker.stop()
        self.is_streaming = False
        self.connection_var.set(f"Connected: {self.connected_port}" if self.connected_port else "Stopped")
        self._apply_control_states()

    def _drain_stream_start_results(self) -> None:
        while True:
            try:
                result = self.stream_start_results.get_nowait()
            except queue.Empty:
                return
            self._finish_stream_start(result)

    def _finish_stream_start(self, result: StreamStartResult) -> None:
        self.is_starting = False
        if result.ok:
            self.is_streaming = True
            self.connection_var.set("Streaming")
        else:
            self.is_streaming = False
            self.connection_var.set(f"Connected: {self.connected_port}" if self.connected_port else "Stopped")
            messagebox.showerror("Start failed", result.error or "Unknown error starting stream")
        self._apply_control_states()

    def load_csv(self) -> None:
        if self.is_loading_csv:
            self._log("CSV load already in progress")
            return
        path = filedialog.askopenfilename(
            title="Load ADS1292 CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        csv_path = Path(path)
        self.is_loading_csv = True
        self.path_var.set(f"Loading CSV: {csv_path}")
        self.metrics_var.set("Loading CSV...")
        self.quality_var.set("Quality: waiting for CSV parse")
        self._log(f"Loading CSV in background: {csv_path}")
        self._apply_control_states()
        threading.Thread(
            target=self._read_csv_in_background,
            args=(csv_path,),
            daemon=True,
        ).start()

    def _read_csv_in_background(self, path: Path) -> None:
        try:
            recording = read_recording_csv(path)
            self.csv_load_results.put(CsvLoadResult(path=path, recording=recording))
        except Exception as exc:
            self.csv_load_results.put(CsvLoadResult(path=path, error=str(exc)))

    def _drain_csv_load_results(self) -> None:
        while True:
            try:
                result = self.csv_load_results.get_nowait()
            except queue.Empty:
                return
            self._finish_csv_load(result)

    def _finish_csv_load(self, result: CsvLoadResult) -> None:
        self.is_loading_csv = False
        if result.error or result.recording is None:
            self.path_var.set(f"CSV load failed: {result.path}")
            self._log(f"Load failed for {result.path}: {result.error}")
            self._apply_control_states()
            messagebox.showerror("Load failed", result.error or "Unknown CSV load error")
            return
        try:
            self.recording_path = result.path
            self.loaded_samples = result.recording.samples
            self._load_event_sidecar(result.path)
            self._load_calibration_sidecar(result.path)
            self._load_protocol_sidecar(result.path)
            self._load_quality_gate_sidecar(result.path)
            self._show_recording(result.recording.samples)
            self.path_var.set(f"CSV: {result.path}")
            self._log(f"Loaded {result.path}")
        except Exception as exc:
            self.path_var.set(f"CSV load failed: {result.path}")
            self._log(f"Load failed after parsing {result.path}: {exc}")
            messagebox.showerror("Load failed", str(exc))
        finally:
            self._apply_control_states()

    def add_event(self) -> None:
        marker = EventMarker(
            timestamp_seconds=self._current_event_time(),
            label=self.event_label_var.get(),
            notes=self.event_notes_var.get(),
        ).normalized()
        self.event_markers = [*self.event_markers, marker]
        self._set_event_count()
        self._save_event_sidecar()
        self._log(f"Event {marker.timestamp_seconds:.2f}s: {marker.label} {marker.notes}".strip())

    def export_report(self) -> None:
        if self.loaded_samples:
            samples = self.loaded_samples
        elif self.ch1 and self.ch2:
            samples = tuple(
                StreamSample(
                    timestamp=index / SAMPLE_RATE_HZ,
                    ch1=int(ch1),
                    ch2=int(ch2),
                    board_heart_rate=0,
                    board_respiration_rate=0,
                    status_byte=int(status),
                )
                for index, (ch1, ch2, status) in enumerate(zip(self.ch1, self.ch2, self.status))
            )
        else:
            messagebox.showerror("No data", "Load a CSV or record data before exporting a report.")
            return
        out_dir = filedialog.askdirectory(title="Choose report output folder")
        if not out_dir:
            return
        try:
            export = export_review_report(
                samples=samples,
                out_dir=Path(out_dir),
                title="ADS1292 Studio Review",
                sample_rate_hz=SAMPLE_RATE_HZ,
                source=ADS1292R_ECG_SOURCE,
                metadata=self._metadata(),
                events=tuple(self.event_markers),
                calibration=self._calibration(),
                quality_gate=self._quality_gate(),
                protocol=self._protocol(),
            )
            self._log(f"Exported report: {export.html_path}")
            messagebox.showinfo("Report exported", f"Saved report:\n{export.html_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def batch_compare(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Choose ADS1292 CSV files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not paths:
            return
        out_dir = filedialog.askdirectory(title="Choose batch output folder")
        if not out_dir:
            return
        try:
            export = export_batch_summary(
                paths=[Path(path) for path in paths],
                out_dir=Path(out_dir),
                title="ADS1292 Batch Summary",
            )
            self._log(f"Exported batch summary: {export.html_path}")
            messagebox.showinfo("Batch summary exported", f"Saved summary:\n{export.html_path}")
        except Exception as exc:
            messagebox.showerror("Batch export failed", str(exc))

    def session_index(self) -> None:
        root = filedialog.askdirectory(title="Choose recordings folder")
        if not root:
            return
        out_dir = filedialog.askdirectory(title="Choose session index output folder")
        if not out_dir:
            return
        try:
            export = export_session_index(
                root=Path(root),
                out_dir=Path(out_dir),
                title="ADS1292 Session Index",
            )
            self._log(f"Exported session index: {export.html_path}")
            messagebox.showinfo("Session index exported", build_session_index_message(export))
        except Exception as exc:
            messagebox.showerror("Session index failed", str(exc))

    def export_package(self) -> None:
        if self.recording_path is None:
            messagebox.showerror("No CSV", "Load a CSV or record with Save CSV before exporting a package.")
            return
        out_dir = filedialog.askdirectory(title="Choose package output folder")
        if not out_dir:
            return
        try:
            self._write_current_sidecars()
            export = export_session_package(
                csv_path=self.recording_path,
                out_dir=Path(out_dir),
                title="ADS1292 Session Package",
                source=ADS1292R_ECG_SOURCE,
            )
            self._log(f"Exported package: {export.manifest_path}")
            messagebox.showinfo("Package exported", f"Saved package manifest:\n{export.manifest_path}")
        except Exception as exc:
            messagebox.showerror("Package export failed", str(exc))

    def verify_package(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose package manifest",
            filetypes=[("Manifest JSON", "manifest.json"), ("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            result = verify_session_package(Path(path))
            if result.ok:
                self._log(f"Verified package: {result.checked_files} files OK")
                messagebox.showinfo("Package verified", f"{result.checked_files} files verified.")
                return
            failures = "\n".join(result.failures)
            self._log(f"Package verification failed: {failures}")
            messagebox.showerror("Package verification failed", failures)
        except Exception as exc:
            messagebox.showerror("Package verification failed", str(exc))

    def _clear_buffers(self) -> None:
        self.sample_index = 0
        self.loaded_samples = tuple()
        self.event_markers = []
        self._set_event_count()
        self._clear_signal_buffers()
        self._apply_control_states()

    def _clear_signal_buffers(self) -> None:
        for buffer in (self.ch1, self.ch2, self.status, self.indices, self.board_hr, self.board_rr):
            buffer.clear()
        self.live_quality_generation += 1
        if self.live_quality_future is not None and not self.live_quality_future.done():
            self.live_quality_future.cancel()
        while True:
            try:
                self.live_quality_results.get_nowait()
            except queue.Empty:
                break

    def _apply_control_states(self) -> None:
        if not hasattr(self, "control_buttons"):
            return
        state = GuiState(
            connected=self.connected_port is not None,
            streaming=self.is_streaming,
            has_data=bool(self.loaded_samples or (self.ch1 and self.ch2)),
            has_recording_path=self.recording_path is not None,
            loading_csv=self.is_loading_csv,
            connecting=self.is_connecting,
            starting=self.is_starting,
        )
        states = gui_control_states(state=state)
        self.workflow_hint_var.set(
            gui_workflow_hint(state=state)
        )
        self.status_overview_var.set(
            gui_status_overview(state=state)
        )
        self.connection_label.configure(
            style=header_connection_style(header_connection_tone(state=state))
        )
        for card in gui_status_cards(state=state):
            self.status_card_vars[card.label].set(card.value)
            self.status_card_value_labels[card.label].configure(
                style=status_tone_style(card.tone)
            )
            self.status_card_tone_stripes[card.label].configure(
                bg=status_tone_color(card.tone)
            )
        if not state.has_data:
            self._apply_signal_quality_cards(gui_signal_quality_cards())
        for label, button in self.control_buttons.items():
            button.configure(state=states[label])

    def _apply_signal_quality_cards(self, cards: tuple[GuiStatusCard, ...]) -> None:
        for card in cards:
            self.signal_card_vars[card.label].set(card.value)
            self.signal_card_value_labels[card.label].configure(
                style=status_tone_style(card.tone)
            )
            self.signal_card_tone_stripes[card.label].configure(
                bg=status_tone_color(card.tone)
            )

    def _metadata(self) -> SessionMetadata:
        return SessionMetadata(
            session_id=self.session_id_var.get(),
            subject_id=self.subject_id_var.get(),
            electrode=self.electrode_var.get(),
            montage=self.montage_var.get(),
            operator=self.operator_var.get(),
            notes=self.notes_var.get(),
        ).normalized()

    def _current_event_time(self) -> float:
        if self.sample_index > 0:
            return self.sample_index / SAMPLE_RATE_HZ
        if self.loaded_samples:
            return len(self.loaded_samples) / SAMPLE_RATE_HZ
        return 0.0

    def _events_path(self, csv_path: Path) -> Path:
        return csv_path.with_suffix(".events.json")

    def _calibration_path(self, csv_path: Path) -> Path:
        return csv_path.with_suffix(".calibration.json")

    def _protocol_path(self, csv_path: Path) -> Path:
        return csv_path.with_suffix(".protocol.json")

    def _quality_gate_path(self, csv_path: Path) -> Path:
        return csv_path.with_suffix(".quality-gate.json")

    def _load_event_sidecar(self, csv_path: Path) -> None:
        path = self._events_path(csv_path)
        if not path.exists():
            self.event_markers = []
            self._set_event_count()
            return
        self.event_markers = list(read_events_json(path))
        self._set_event_count()
        self._log(f"Loaded events: {path}")

    def _save_event_sidecar(self) -> None:
        if self.recording_path is None:
            return
        write_events_json(self._events_path(self.recording_path), self.event_markers)

    def _set_event_count(self) -> None:
        self.event_count_var.set(f"{len(self.event_markers)} events")

    def _calibration(self) -> Calibration:
        return Calibration(
            vref_mv=_float_from_var(self.vref_mv_var, 2420.0),
            pga_gain=_float_from_var(self.pga_gain_var, 6.0),
            adc_bits=24,
            label=self.calibration_label_var.get(),
        ).normalized()

    def _protocol(self) -> TestProtocol:
        return TestProtocol(
            name=self.protocol_name_var.get(),
            objective=self.protocol_objective_var.get(),
            operator_instructions="Follow the listed protocol steps.",
            steps=_parse_protocol_steps(self.protocol_steps_var.get()),
            acceptance_notes=self.protocol_acceptance_var.get(),
        ).normalized()

    def _quality_gate(self) -> QualityGate:
        return _quality_gate_from_values(
            {
                "min_duration_seconds": self.gate_min_duration_var.get(),
                "min_contact_ok_percent": self.gate_min_contact_var.get(),
                "min_r_peaks": self.gate_min_r_peaks_var.get(),
                "min_hr_bpm": self.gate_min_hr_var.get(),
                "max_hr_bpm": self.gate_max_hr_var.get(),
                "require_qrs_clear": self.gate_require_qrs_var.get(),
                "max_baseline_drift_counts": self.gate_max_drift_var.get(),
                "max_noise_rms_counts": self.gate_max_noise_var.get(),
                "max_peak_to_peak_counts": self.gate_max_ptp_var.get(),
            }
        )

    def _load_calibration_sidecar(self, csv_path: Path) -> None:
        path = self._calibration_path(csv_path)
        if not path.exists():
            return
        calibration = read_calibration_json(path)
        self.calibration_label_var.set(calibration.label)
        self.vref_mv_var.set(f"{calibration.vref_mv:g}")
        self.pga_gain_var.set(f"{calibration.pga_gain:g}")
        self._log(f"Loaded calibration: {path}")

    def _load_protocol_sidecar(self, csv_path: Path) -> None:
        path = self._protocol_path(csv_path)
        if not path.exists():
            return
        protocol = read_protocol_json(path)
        self.protocol_name_var.set(protocol.name)
        self.protocol_objective_var.set(protocol.objective)
        self.protocol_steps_var.set(_format_protocol_steps(protocol.steps))
        self.protocol_acceptance_var.set(protocol.acceptance_notes)
        self._log(f"Loaded protocol: {path}")

    def _load_quality_gate_sidecar(self, csv_path: Path) -> None:
        path = self._quality_gate_path(csv_path)
        if not path.exists():
            return
        values = _quality_gate_to_values(read_quality_gate_json(path))
        self.gate_min_duration_var.set(str(values["min_duration_seconds"]))
        self.gate_min_contact_var.set(str(values["min_contact_ok_percent"]))
        self.gate_min_r_peaks_var.set(str(values["min_r_peaks"]))
        self.gate_min_hr_var.set(str(values["min_hr_bpm"]))
        self.gate_max_hr_var.set(str(values["max_hr_bpm"]))
        self.gate_require_qrs_var.set(bool(values["require_qrs_clear"]))
        self.gate_max_drift_var.set(str(values["max_baseline_drift_counts"]))
        self.gate_max_noise_var.set(str(values["max_noise_rms_counts"]))
        self.gate_max_ptp_var.set(str(values["max_peak_to_peak_counts"]))
        self._log(f"Loaded quality gate: {path}")

    def _write_current_sidecars(self) -> None:
        if self.recording_path is None:
            return
        write_metadata_json(self.recording_path.with_suffix(".json"), self._metadata())
        write_events_json(self._events_path(self.recording_path), self.event_markers)
        write_calibration_json(self._calibration_path(self.recording_path), self._calibration())
        write_protocol_json(self._protocol_path(self.recording_path), self._protocol())
        write_quality_gate_json(self._quality_gate_path(self.recording_path), self._quality_gate())

    def _tick(self) -> None:
        self._drain_csv_load_results()
        self._drain_connect_results()
        self._drain_stream_start_results()
        self._drain_live_quality_results()
        latest = None
        while True:
            try:
                latest = self.samples.get_nowait()
            except queue.Empty:
                break
            self._append_sample(latest)
        if latest is not None:
            self._redraw_live()
            self._apply_control_states()
        while True:
            try:
                self._log(self.logs.get_nowait())
            except queue.Empty:
                break
        self._drain_live_quality_results()
        self.after(50, self._tick)

    def _schedule_live_quality_update(
        self,
        *,
        source: str,
        valid_rr: int,
        ch1_values: tuple[float, ...],
        ch2_values: tuple[float, ...],
        status_values: tuple[int, ...],
    ) -> None:
        self.live_quality_generation += 1
        generation = self.live_quality_generation
        if self.live_quality_future is not None and not self.live_quality_future.done():
            self.live_quality_future.cancel()
        future = self.live_quality_executor.submit(
            compute_live_quality_result,
            generation=generation,
            source=source,
            valid_rr=valid_rr,
            ch1_values=ch1_values,
            ch2_values=ch2_values,
            status_values=status_values,
        )
        future.add_done_callback(self._queue_live_quality_result)
        self.live_quality_future = future

    def _queue_live_quality_result(self, future: Future[LiveQualityResult]) -> None:
        if future.cancelled():
            return
        try:
            result = future.result()
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            result = LiveQualityResult(
                generation=self.live_quality_generation,
                source=ADS1292R_ECG_SOURCE,
                valid_rr=0,
                samples=tuple(),
                status_values=tuple(),
                error=str(exc),
            )
        self.live_quality_results.put(result)

    def _drain_live_quality_results(self) -> None:
        latest: LiveQualityResult | None = None
        while True:
            try:
                result = self.live_quality_results.get_nowait()
            except queue.Empty:
                break
            if result.generation == self.live_quality_generation:
                latest = result
        if latest is None:
            return
        self._apply_live_quality_result(latest)

    def _apply_live_quality_result(self, result: LiveQualityResult) -> None:
        if result.error or result.metrics is None:
            set_string_var_if_changed(
                self.quality_var,
                f"Quality: background update failed: {result.error or 'unknown error'}",
            )
            self._apply_signal_quality_cards(gui_signal_quality_cards())
            return
        set_string_var_if_changed(
            self.quality_var,
            self._quality_text(
                result.source,
                result.valid_rr,
                result.samples,
                result.status_values,
                metrics=result.metrics,
            ),
        )
        self._apply_signal_quality_cards(
            gui_signal_quality_cards(
                quality_label=result.metrics.quality_label,
                ecg_source=result.metrics.ecg_source,
                contact_ok_percent=result.metrics.contact_ok_percent,
                lead_off_bad_samples=result.metrics.lead_off_bad_samples,
                r_peaks=result.metrics.r_peaks,
                hr_median_bpm=result.metrics.hr_median_bpm,
                baseline_drift_counts=result.metrics.baseline_drift_counts,
                noise_rms_counts=result.metrics.noise_rms_counts,
                peak_to_peak_counts=result.metrics.peak_to_peak_counts,
            )
        )

    def _append_sample(self, sample: StreamSample) -> None:
        self.indices.append(self.sample_index)
        self.sample_index += 1
        self.ch1.append(sample.ch1)
        self.ch2.append(sample.ch2)
        self.status.append(sample.lead_off_bits)
        self.board_hr.append(sample.board_heart_rate)
        self.board_rr.append(sample.board_respiration_rate)

    def _refresh_display_plots(self, _event: tk.Event | None = None) -> None:
        if self.is_streaming and self.indices:
            self._redraw_live()
            return
        if self.loaded_samples:
            self._show_recording(self.loaded_samples)
            return
        if self.indices:
            self._redraw_live()

    def _display_settings(self) -> EcgDisplaySettings:
        return EcgDisplaySettings(
            time_window_seconds=parse_display_window(self.display_window_var.get()),
            gain=parse_display_gain(self.display_gain_var.get()),
            sweep_speed_mm_s=parse_sweep_speed(self.sweep_speed_var.get()),
        ).normalized()

    def _software_filter_settings(self) -> SoftwareFilterSettings:
        return SoftwareFilterSettings(
            highpass_enabled=bool(self.highpass_filter_var.get()),
            notch_enabled=bool(self.notch_filter_var.get()),
            lowpass_enabled=bool(self.lowpass_filter_var.get()),
            bandpass_enabled=bool(self.filter_var.get()),
        )

    def _ads1292r_display_channels(self) -> tuple[str, np.ndarray, np.ndarray]:
        ch1 = np.asarray(self.ch1, dtype=float)
        ch2 = np.asarray(self.ch2, dtype=float)
        return ADS1292R_ECG_SOURCE, ch2, ch1

    def _display_signal(self, values: np.ndarray, *, invert: bool = False, gain: float = 1.0) -> np.ndarray:
        return display_signal_values(
            values,
            filter_enabled=bool(self.filter_var.get()),
            filter_settings=self._software_filter_settings(),
            invert=invert,
            gain=gain,
            sample_rate_hz=SAMPLE_RATE_HZ,
        )

    def _apply_ecg_paper_grid(self, ax: object, settings: EcgDisplaySettings) -> None:
        spec = ecg_paper_grid_spec(settings)
        cache_key = ecg_paper_grid_key(settings, ax.get_ylim())
        axis_id = id(ax)
        if self.ecg_paper_grid_cache.get(axis_id) == cache_key:
            return
        self.ecg_paper_grid_cache[axis_id] = cache_key
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

    def _draw_calibration_pulse(
        self,
        ax: object,
        artists: list[object],
        settings: EcgDisplaySettings,
    ) -> None:
        axis_id = id(ax)
        label_text = f"1 mV | {settings.gain:g}x"
        if artists and self.calibration_pulse_cache.get(axis_id) == label_text:
            return
        if len(artists) >= 2 and hasattr(artists[1], "set_text"):
            artists[1].set_text(label_text)
            self.calibration_pulse_cache[axis_id] = label_text
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
        self.calibration_pulse_cache[axis_id] = label_text

    def _redraw_live(self) -> None:
        if not self.indices:
            return
        self._clear_empty_plot_state()
        display_settings = self._display_settings()
        filter_settings = self._software_filter_settings()
        source, ecg_raw, resp_raw = self._ads1292r_display_channels()
        ecg = self._display_signal(ecg_raw, invert=DEFAULT_ECG_INVERTED, gain=display_settings.gain)
        resp = self._display_signal(resp_raw)
        x = np.asarray(self.indices, dtype=float) / SAMPLE_RATE_HZ
        left = max(0.0, x[-1] - display_settings.time_window_seconds)
        right = max(display_settings.time_window_seconds, x[-1])
        visible = (x >= left) & (x <= right)
        visible_x = x[visible]
        visible_ecg = ecg[visible]
        visible_resp = resp[visible]
        visible_ecg_plot = smooth_for_plot(visible_ecg, window=DISPLAY_SMOOTHING_WINDOW)
        visible_resp_plot = smooth_for_plot(visible_resp, window=DISPLAY_SMOOTHING_WINDOW)
        status_arr = np.asarray(self.status, dtype=float)
        visible_status = status_arr[visible]
        peaks = detect_r_peaks(ecg[visible], SAMPLE_RATE_HZ)
        peaks_x = visible_x[list(peaks)] if peaks else []
        peaks_y = visible_ecg_plot[list(peaks)] if peaks else []

        self.live_ecg_line.set_data(visible_x, visible_ecg_plot)
        self.live_peak_line.set_data(peaks_x, peaks_y)
        self.live_resp_line.set_data(visible_x, visible_resp_plot)
        self.live_status_line.set_data(visible_x, visible_status)
        for ax in (self.ax_live_ecg, self.ax_live_resp, self.ax_live_status):
            ax.set_xlim(left, right)
        if self.autoscale_var.get():
            ecg_ylim = robust_ylim(visible_ecg_plot, min_span=DISPLAY_MIN_ECG_SPAN_COUNTS * display_settings.gain)
            resp_ylim = robust_ylim(visible_resp_plot, min_span=DISPLAY_MIN_RESP_SPAN_COUNTS)
            self.ax_live_ecg.set_ylim(*stable_ylim(self.ax_live_ecg.get_ylim(), ecg_ylim))
            self.ax_live_resp.set_ylim(*stable_ylim(self.ax_live_resp.get_ylim(), resp_ylim))
            self.ax_live_status.set_ylim(-0.5, max(1.0, float(visible_status.max()) + 0.5 if visible_status.size else 1.0))
        self._apply_ecg_paper_grid(self.ax_live_ecg, display_settings)
        self._draw_calibration_pulse(self.ax_live_ecg, self.live_calibration_artists, display_settings)
        hr = heart_rate_summary(peaks, SAMPLE_RATE_HZ)
        ecg_label, resp_label, contact_label = ads1292r_plot_layout_labels()
        mode = f"{display_mode_label(display_settings, filter_settings)}, display-smoothed"
        polarity = ", inverted" if DEFAULT_ECG_INVERTED else ""
        self._set_signal_axis_title(
            self.ax_live_ecg,
            f"ECG display: {ecg_label} | {mode}{polarity} | R peaks {len(peaks)}",
        )
        self._set_signal_axis_title(self.ax_live_resp, resp_label)
        self._set_signal_axis_title(self.ax_live_status, contact_label)
        set_string_var_if_changed(
            self.metrics_var,
            f"samples {self.sample_index} | duration {x[-1]:.1f} s | source {ecg_label} | HR {hr.median_bpm:.0f} bpm",
        )
        self._schedule_live_quality_update(
            source=source,
            valid_rr=hr.valid_rr_count,
            ch1_values=tuple(self.ch1),
            ch2_values=tuple(self.ch2),
            status_values=tuple(self.status),
        )
        self.live_canvas.draw_idle()

    def _show_recording(self, samples: tuple[StreamSample, ...]) -> None:
        self._clear_empty_plot_state()
        self._clear_signal_buffers()
        self.sample_index = 0
        display_settings = self._display_settings()
        filter_settings = self._software_filter_settings()
        full_ch1 = np.asarray([sample.ch1 for sample in samples], dtype=float)
        full_ch2 = np.asarray([sample.ch2 for sample in samples], dtype=float)
        full_status_ints = tuple(sample.lead_off_bits for sample in samples)
        source = ADS1292R_ECG_SOURCE
        ecg = self._display_signal(full_ch2, invert=DEFAULT_ECG_INVERTED, gain=display_settings.gain)
        resp = self._display_signal(full_ch1)
        result = review_channels(full_ch1, full_ch2, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
        metrics = compute_quality_metrics(samples, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
        x = np.arange(ecg.size) / SAMPLE_RATE_HZ
        status_arr = np.asarray(full_status_ints, dtype=float)
        display_ecg = smooth_for_plot(ecg, window=DISPLAY_SMOOTHING_WINDOW)
        display_resp = smooth_for_plot(resp, window=DISPLAY_SMOOTHING_WINDOW)
        plot_x, plot_ecg = decimate_for_plot(x, display_ecg, MAX_POINTS)
        _, plot_resp = decimate_for_plot(x, display_resp, MAX_POINTS)
        _, plot_status = decimate_for_plot(x, status_arr, MAX_POINTS)
        ecg_label, resp_label, contact_label = ads1292r_plot_layout_labels()
        self.review_ecg_line.set_data(plot_x, plot_ecg)
        self.review_resp_line.set_data(plot_x, plot_resp)
        self.review_status_line.set_data(plot_x, plot_status)
        peak_x = np.asarray(result.peaks, dtype=float) / SAMPLE_RATE_HZ if result.peaks else []
        self.review_peak_line.set_data(peak_x, ecg[list(result.peaks)] if result.peaks else [])
        mode = f"{display_mode_label(display_settings, filter_settings)}, display-smoothed"
        polarity = ", inverted" if DEFAULT_ECG_INVERTED else ""
        self._set_signal_axis_title(
            self.ax_review_ecg,
            f"Offline ECG: {ecg_label} | {mode}{polarity} | "
            f"HR {result.heart_rate.median_bpm:.1f} bpm | peaks {len(result.peaks)}",
        )
        self._set_signal_axis_title(self.ax_review_resp, resp_label)
        self._set_signal_axis_title(self.ax_review_status, contact_label)
        for ax, values, min_span in (
            (self.ax_review_ecg, display_ecg, DISPLAY_MIN_ECG_SPAN_COUNTS * display_settings.gain),
            (self.ax_review_resp, display_resp, DISPLAY_MIN_RESP_SPAN_COUNTS),
        ):
            ax.set_xlim(0, max(1, x[-1] if x.size else 1))
            ax.set_ylim(*robust_ylim(values, min_span=min_span))
        self.ax_review_status.set_xlim(0, max(1, x[-1] if x.size else 1))
        self.ax_review_status.set_ylim(-0.5, max(1.0, float(status_arr.max()) + 0.5 if status_arr.size else 1.0))
        self.ax_review_status.set_xlabel("Time (s)")
        self._apply_ecg_paper_grid(self.ax_review_ecg, display_settings)
        self._draw_calibration_pulse(self.ax_review_ecg, self.review_calibration_artists, display_settings)
        self.review_canvas.draw_idle()
        self._draw_pqrst(ecg, result.peaks)
        self.metrics_var.set(
            f"samples {len(samples)} | duration {len(samples) / SAMPLE_RATE_HZ:.1f} s | source {ecg_label}"
        )
        self.quality_var.set(
            f"{self._quality_text(source, result.heart_rate.valid_rr_count, samples, full_status_ints, metrics=metrics)} | "
            f"QRS {'clear' if result.pqrst.qrs_clear else 'unclear'} | "
            f"P {'tentative' if result.pqrst.p_tentative else 'not reliable'} | "
            f"T {'tentative' if result.pqrst.t_tentative else 'not reliable'}"
        )
        self._apply_signal_quality_cards(
            gui_signal_quality_cards(
                quality_label=metrics.quality_label,
                ecg_source=metrics.ecg_source,
                contact_ok_percent=metrics.contact_ok_percent,
                lead_off_bad_samples=metrics.lead_off_bad_samples,
                r_peaks=metrics.r_peaks,
                hr_median_bpm=metrics.hr_median_bpm,
                baseline_drift_counts=metrics.baseline_drift_counts,
                noise_rms_counts=metrics.noise_rms_counts,
                peak_to_peak_counts=metrics.peak_to_peak_counts,
            )
        )

    def _draw_pqrst(self, ecg: np.ndarray, peaks: tuple[int, ...]) -> None:
        review = pqrst_review(ecg, peaks, SAMPLE_RATE_HZ)
        self.ax_pqrst.clear()
        self._style_signal_axes((self.ax_pqrst,))
        self.ax_pqrst.set_xlabel("Time relative to R peak (ms)")
        self.ax_pqrst.set_ylabel("Filtered counts")
        if review.average_beat:
            pqrst_style = pqrst_plot_style()
            self.ax_pqrst.plot(
                review.time_ms,
                review.average_beat,
                color=PLOT_TRACE_COLORS["ecg"],
                **pqrst_style["average"],
            )
            self.ax_pqrst.axvline(
                0,
                color=PLOT_TRACE_COLORS["peak"],
                **pqrst_style["r_marker"],
            )
            p_search = pqrst_style["p_search"]
            self.ax_pqrst.axvspan(
                p_search["start_ms"],
                p_search["end_ms"],
                color=p_search["color"],
                alpha=p_search["alpha"],
                label=p_search["label"],
            )
            t_search = pqrst_style["t_search"]
            self.ax_pqrst.axvspan(
                t_search["start_ms"],
                t_search["end_ms"],
                color=t_search["color"],
                alpha=t_search["alpha"],
                label=t_search["label"],
            )
            self.ax_pqrst.legend(**pqrst_style["legend"])
        self._set_signal_axis_title(
            self.ax_pqrst,
            f"PQRST review: QRS={review.qrs_clear}, P tentative={review.p_tentative}, "
            f"T tentative={review.t_tentative}, beats={review.beats_used}",
        )
        self.pqrst_canvas.draw_idle()

    def _quality_text(
        self,
        source: str,
        valid_rr: int,
        samples: tuple[StreamSample, ...],
        status_values: tuple[int, ...],
        metrics=None,
    ) -> str:
        protocol = self._protocol()
        should_evaluate_protocol = bool(self.loaded_samples) or protocol_ready_for_live_quality(
            samples,
            protocol,
            SAMPLE_RATE_HZ,
        )
        return build_quality_text(
            samples=samples,
            status_values=status_values,
            source=source,
            selected_source=ADS1292R_ECG_SOURCE,
            valid_rr=valid_rr,
            protocol=protocol if should_evaluate_protocol else None,
            sample_rate_hz=SAMPLE_RATE_HZ,
            gate=self._quality_gate(),
            metrics=metrics,
        )

    def _log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{stamp}] {message}\n")
        self.log_text.see(tk.END)

    def _close(self) -> None:
        self.stop()
        if self.live_quality_future is not None and not self.live_quality_future.done():
            self.live_quality_future.cancel()
        self.live_quality_executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def main() -> None:
    install_macos_stderr_filter()
    App().mainloop()


def _float_from_var(variable: tk.StringVar, fallback: float) -> float:
    try:
        return float(variable.get())
    except ValueError:
        return fallback


def _quality_gate_from_values(values: dict[str, object]) -> QualityGate:
    return QualityGate(
        min_duration_seconds=_float_value(values.get("min_duration_seconds"), 8.0),
        min_contact_ok_percent=_float_value(values.get("min_contact_ok_percent"), 95.0),
        min_r_peaks=_int_value(values.get("min_r_peaks"), 5),
        min_hr_bpm=_float_value(values.get("min_hr_bpm"), 35.0),
        max_hr_bpm=_float_value(values.get("max_hr_bpm"), 180.0),
        require_qrs_clear=bool(values.get("require_qrs_clear", True)),
        max_baseline_drift_counts=_optional_float_value(values.get("max_baseline_drift_counts")),
        max_noise_rms_counts=_optional_float_value(values.get("max_noise_rms_counts")),
        max_peak_to_peak_counts=_optional_float_value(values.get("max_peak_to_peak_counts")),
    ).normalized()


def _quality_gate_to_values(gate: QualityGate) -> dict[str, object]:
    normalized = gate.normalized()
    return {
        "min_duration_seconds": _format_number(normalized.min_duration_seconds),
        "min_contact_ok_percent": _format_number(normalized.min_contact_ok_percent),
        "min_r_peaks": str(normalized.min_r_peaks),
        "min_hr_bpm": _format_number(normalized.min_hr_bpm),
        "max_hr_bpm": _format_number(normalized.max_hr_bpm),
        "require_qrs_clear": normalized.require_qrs_clear,
        "max_baseline_drift_counts": _format_optional_number(normalized.max_baseline_drift_counts),
        "max_noise_rms_counts": _format_optional_number(normalized.max_noise_rms_counts),
        "max_peak_to_peak_counts": _format_optional_number(normalized.max_peak_to_peak_counts),
    }


def _float_value(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _int_value(value: object, fallback: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _optional_float_value(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    return f"{value:g}"


def _format_optional_number(value: float | None) -> str:
    return "" if value is None else _format_number(value)


def _format_protocol_steps(steps: tuple[ProtocolStep, ...]) -> str:
    return "; ".join(
        f"{step.start_seconds:g},{step.duration_seconds:g},{step.label},{step.instruction}" for step in steps
    )


def _parse_protocol_steps(text: str) -> tuple[ProtocolStep, ...]:
    steps: list[ProtocolStep] = []
    for chunk in text.split(";"):
        parts = [part.strip() for part in chunk.split(",", 3)]
        if len(parts) != 4:
            continue
        try:
            start = float(parts[0])
            duration = float(parts[1])
        except ValueError:
            continue
        steps.append(ProtocolStep(start, duration, parts[2], parts[3]).normalized())
    if steps:
        return tuple(steps)
    return protocol_template().steps


if __name__ == "__main__":
    main()
