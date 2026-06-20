from __future__ import annotations

from ads1292_studio.plot_theme import (
    APP_VISUAL_TOKENS,
    plot_trace_colors as base_plot_trace_colors,
    plot_trace_styles as base_plot_trace_styles,
    pqrst_plot_style as base_pqrst_plot_style,
    seaborn_plot_theme as base_seaborn_plot_theme,
)


APP_WINDOW_SPEC = {
    "geometry": "1440x900",
    "min_size": (1180, 760),
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
        "padding": (9, 5),
        "font": ("Aptos", 12),
        "foreground": "#172033",
        "background": "#FFFFFF",
        "active_foreground": "#1F4FB2",
        "active_background": "#EEF3FA",
        "pressed_foreground": "#FFFFFF",
        "pressed_background": "#2F6FED",
        "border": "#D9E1EC",
        "active_border": "#2F6FED",
        "pressed_border": "#1F4FB2",
        "focus_border": "#2F6FED",
        "disabled_foreground": "#A9B4C3",
        "disabled_background": "#EEF3FA",
        "borderwidth": 1,
        "relief": "flat",
    },
    "primary": {
        "padding": (10, 5),
        "font": ("Aptos", 12, "bold"),
        "foreground": "#FFFFFF",
        "background": "#2F6FED",
        "active_foreground": "#FFFFFF",
        "active_background": "#1F4FB2",
        "pressed_foreground": "#FFFFFF",
        "pressed_background": "#173F99",
        "border": "#2F6FED",
        "active_border": "#1F4FB2",
        "pressed_border": "#173F99",
        "focus_border": "#173F99",
        "disabled_foreground": "#A9B4C3",
        "disabled_background": "#EEF3FA",
        "borderwidth": 1,
        "relief": "flat",
    },
    "stop": {
        "padding": (10, 5),
        "font": ("Aptos", 12, "bold"),
        "foreground": "#B3261E",
        "background": "#FFFFFF",
        "active_foreground": "#FFFFFF",
        "active_background": "#B3261E",
        "pressed_foreground": "#FFFFFF",
        "pressed_background": "#8C1D18",
        "border": "#F3C8C4",
        "active_border": "#B3261E",
        "pressed_border": "#8C1D18",
        "focus_border": "#B3261E",
        "disabled_foreground": "#A9B4C3",
        "disabled_background": "#EEF3FA",
        "borderwidth": 1,
        "relief": "flat",
    },
    "sidebar": {
        "padding": (10, 5),
        "font": ("Aptos", 11, "bold"),
        "foreground": "#172033",
        "background": "#FFFFFF",
        "active_foreground": "#1F4FB2",
        "active_background": "#EEF3FA",
        "pressed_foreground": "#FFFFFF",
        "pressed_background": "#2F6FED",
        "border": "#D9E1EC",
        "active_border": "#2F6FED",
        "pressed_border": "#1F4FB2",
        "focus_border": "#2F6FED",
        "disabled_foreground": "#A9B4C3",
        "disabled_background": "#EEF3FA",
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
        "padding": (8, 5),
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
        "padding": (7, 4),
        "fieldbackground": "#FFFFFF",
        "background": "#FFFFFF",
        "foreground": "#172033",
        "border": "#D9E1EC",
        "focus_border": "#2F6FED",
        "selectbackground": "#EEF3FA",
        "selectforeground": "#172033",
        "arrowcolor": "#657084",
        "active_arrowcolor": "#1F4FB2",
        "disabled_foreground": "#657084",
        "disabled_background": "#EEF3FA",
        "borderwidth": 1,
        "relief": "flat",
        "arrowsize": 14,
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
        "padding": (5, 3),
        "font": ("Aptos", 10, "bold"),
        "background": "#FFFFFF",
        "foreground": "#293247",
        "selected_background": "#2F6FED",
        "selected_foreground": "#FFFFFF",
        "border": "#D9E1EC",
        "selected_border": "#2F6FED",
        "active_foreground": "#1F4FB2",
        "active_border": "#2F6FED",
        "disabled_foreground": "#657084",
        "disabled_background": "#EEF3FA",
        "active_background": "#EAF1FF",
        "selected_active_background": "#1F4FB2",
        "selected_active_border": "#1F4FB2",
    },
}
TOOLBAR_CONTROL_STYLES = {
    "port": "Port.TCombobox",
    "toggle": "ToolbarToggle.TCheckbutton",
    "toggle_chip": "ToolbarToggleChip.TLabel",
    "hover_toggle_chip": "Hover.ToolbarToggleChip.TLabel",
    "disabled_toggle_chip": "Disabled.ToolbarToggleChip.TLabel",
    "selected_toggle_chip": "Selected.ToolbarToggleChip.TLabel",
    "selected_hover_toggle_chip": "SelectedHover.ToolbarToggleChip.TLabel",
}
TOOLBAR_FRAME_SPEC = {
    "frame": "Toolbar.TFrame",
    "separator": "ToolbarSeparator.TFrame",
    "background": "#F8FAFD",
    "separator_background": "#E5EAF2",
    "borderwidth": 0,
    "relief": "flat",
}
TOOLBAR_LABEL_SPEC = {
    "style": "ToolbarLabel.TLabel",
    "font": ("Aptos", 11, "bold"),
    "background": "#F8FAFD",
    "foreground": "#172033",
}
TOOLBAR_GROUP_LABEL_SPEC = {
    "style": "ToolbarGroupLabel.TLabel",
    "font": ("Aptos", 9, "bold"),
    "background": "#F8FAFD",
    "foreground": "#657084",
    "padding": (2, 2),
}
TOOLBAR_HINT_STYLES = {
    "frame": "ToolbarHint.TFrame",
    "label": "ToolbarHint.TLabel",
    "background": "#EAF1FF",
    "foreground": "#293247",
    "font": ("Aptos", 10, "bold"),
    "border": "#EAF1FF",
    "borderwidth": 0,
    "relief": "flat",
    "width": 58,
    "wraplength": 470,
}
TOOLBAR_GROUP_PADDING = {
    "separator": (8, 6),
    "tight": (3, 3),
}
TOOLBAR_LAYOUT_SPEC = {
    "frame": "Toolbar.TFrame",
    "padding": (14, 7, 14, 7),
    "port_width": 34,
    "button_width": 10,
    "port_padding": (6, 5),
    "refresh_padding": (0, 2),
    "primary_action_padding": (8, 2),
    "inline_action_padding": (3, 2),
    "save_padding": (6, 2),
    "toggle_padding": (3, 2),
    "display_label_padding": (4, 2),
    "display_control_padding": (3, 5),
    "display_width": 8,
    "separator_width": 1,
    "hint_padding": (10, 3),
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
    "width": 320,
    "padding": (8, 10),
    "scroll_width": 292,
}
WORKSPACE_LAYOUT_SPEC = {
    "main": "Main.TFrame",
    "main_padding": (8, 10, 14, 10),
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
    "tab_padding": (14, 6),
    "tab_font": ("Aptos", 12, "bold"),
    "tab_borderwidth": 0,
    "tab_relief": "flat",
}
BASE_CHECKBUTTON_STYLE = {
    "style": "TCheckbutton",
    "background": "#EEF3FA",
    "foreground": "#172033",
}
MAIN_TABS = ("Live ECG", "Review CSV", "PQRST Beat", "Event Log")
STATUS_CARD_LABELS = ("Connection", "Port", "Acquisition", "Data", "Package")
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
    "padding": (10, 4),
    "font": ("Aptos", 11, "bold"),
    "width": 22,
    "wraplength": 190,
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
    "padding": (18, 10, 18, 9),
    "subtitle_padding": (12, 0),
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
        "font": ("Aptos", 18, "bold"),
        "background": "#FFFFFF",
        "foreground": "#172033",
    },
    "subtitle": {
        "style": "AppSubtitle.TLabel",
        "font": ("Aptos", 11),
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
STATUS_AXIS_SPEC = {
    "y_major_tick_bits": 1.0,
    "ylabel": "lead-off bits",
}
EMPTY_PLOT_MESSAGES = {
    "live": (
        "CH2 ECG Lead I appears after Start",
        "CH1 respiration appears after Start",
        "Lead-off/contact status appears after Start",
    ),
    "review": (
        "Load CSV for CH2 ECG review",
        "Load CSV for CH1 respiration",
        "Load CSV for contact status",
    ),
    "pqrst": ("Load or record ECG to review averaged PQRST",),
}
EMPTY_PLOT_STYLE = {
    "axis_face": "#F8FAFD",
    "text_color": "#657084",
    "box_face": "#FFFFFF",
    "box_edge": "#EAF1FF",
    "font_size": 9,
    "font_weight": "bold",
    "alpha": 0.88,
    "box_pad": 0.48,
    "rounding": 0.12,
    "line_width": 0.8,
    "guide_color": "#D9E1EC",
    "guide_linewidth": 1.0,
    "guide_alpha": 0.58,
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
    "max_lines": 1200,
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
SCROLLABLE_FRAME_SPEC = {
    "canvas_background": "#F6F8FB",
    "content_padding": 10,
    "highlightthickness": 0,
    "borderwidth": 0,
    "relief": "flat",
}
PANEL_CHROME_SPEC = {
    "background": "#FFFFFF",
    "border": "#E5EAF2",
    "borderwidth": 1,
    "relief": "flat",
}
PLOT_PANEL_CHROME_SPEC = {
    "background": "#FFFFFF",
    "border": "#FFFFFF",
    "borderwidth": 0,
    "relief": "flat",
}
PLOT_PANEL_SPEC = {
    "shell": "Main.TFrame",
    "panel": "PlotPanel.TFrame",
    "padding": (0, 4),
    "panel_padding": (0, 0),
}
PLOT_AXIS_STYLE = {
    "face": "#FBFCFE",
    "grid": "#E3EAF3",
    "spine": "#D9E1EC",
    "tick": "#657084",
    "label": "#293247",
    "title": "#172033",
    "grid_linewidth": 0.56,
    "grid_alpha": 0.26,
    "axisbelow": True,
    "spine_linewidth": 0.65,
    "tick_label_size": 9,
    "tick_direction": "out",
    "tick_length": 3.0,
    "tick_width": 0.65,
    "label_size": 10,
    "label_pad": 6,
    "title_size": 11,
    "title_weight": "bold",
    "title_pad": 8,
    "zero_line_color": "#A9B4C3",
    "zero_line_alpha": 0.55,
    "zero_line_width": 0.8,
    "zero_line_style": "-",
}
PLOT_FIGURE_LAYOUTS = {
    "three_panel": {
        "left": 0.052,
        "right": 0.996,
        "top": 0.990,
        "bottom": 0.052,
        "hspace": 0.18,
    },
    "single_panel": {
        "left": 0.058,
        "right": 0.996,
        "top": 0.980,
        "bottom": 0.096,
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
    "padding": (2, 4),
    "font": ("Aptos", 11, "bold"),
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
    "padding": (8, 4),
    "font": ("Aptos", 10, "bold"),
    "background": "#EEF3FA",
    "foreground": "#293247",
}
SIDEBAR_TAB_STRIP_STYLES = {
    "frame": "SidebarTabStrip.TFrame",
    "tab": "SidebarTab.TLabel",
    "hover_tab": "Hover.SidebarTab.TLabel",
    "selected_tab": "Selected.SidebarTab.TLabel",
    "selected_hover_tab": "SelectedHover.SidebarTab.TLabel",
    "background": "#F6F8FB",
    "selected_background": "#EAF1FF",
    "hover_background": "#EAF1FF",
    "selected_hover_background": "#DDEBFF",
    "foreground": "#657084",
    "selected_foreground": "#2F6FED",
    "font": ("Aptos", 10, "bold"),
    "padding": (0, 0, 0, 5),
    "tab_padding": (7, 6),
    "tab_width": 10,
    "tab_gap": (0, 2),
}
WORKSPACE_TAB_STRIP_STYLES = {
    "frame": "WorkspaceTabStrip.TFrame",
    "tab": "WorkspaceTab.TLabel",
    "hover_tab": "Hover.WorkspaceTab.TLabel",
    "selected_tab": "Selected.WorkspaceTab.TLabel",
    "selected_hover_tab": "SelectedHover.WorkspaceTab.TLabel",
    "background": "#F6F8FB",
    "selected_background": "#2F6FED",
    "hover_background": "#EAF1FF",
    "selected_hover_background": "#1F4FB2",
    "foreground": "#657084",
    "selected_foreground": "#FFFFFF",
    "font": ("Aptos", 12, "bold"),
    "padding": (4, 0, 4, 6),
    "tab_padding": (12, 7),
    "tab_width": 12,
    "tab_gap": (0, 4),
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
    "label_padding": (10, 6),
    "content_padding": (10, 6),
    "primary_wrap": 220,
    "detail_wrap": 215,
    "value_top_padding": (2, 0),
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
    "value_wrap": 225,
}
CARD_LABEL_SPEC = {
    "style": "CardLabel.TLabel",
    "font": ("Aptos", 11),
    "background": "#FFFFFF",
    "foreground": "#657084",
    "width": 12,
    "content_padding": (10, 6),
    "stripe_width": 5,
    "row_padding": (0, 2),
    "value_padding": (6, 0),
    "value_wrap": 160,
    "signal_value_wrap": 160,
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
        "width": HEADER_CONNECTION_PILL["width"],
        "wraplength": HEADER_CONNECTION_PILL["wraplength"],
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


def status_axis_spec() -> dict[str, object]:
    return dict(STATUS_AXIS_SPEC)


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


def scrollable_frame_spec() -> dict[str, object]:
    return dict(SCROLLABLE_FRAME_SPEC)


def panel_chrome_spec() -> dict[str, object]:
    return dict(PANEL_CHROME_SPEC)


def plot_panel_chrome_spec() -> dict[str, object]:
    return dict(PLOT_PANEL_CHROME_SPEC)


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


def sidebar_tab_strip_styles() -> dict[str, object]:
    return dict(SIDEBAR_TAB_STRIP_STYLES)


def sidebar_layout_spec() -> dict[str, object]:
    return dict(SIDEBAR_LAYOUT_SPEC)


def workspace_tab_strip_styles() -> dict[str, object]:
    return dict(WORKSPACE_TAB_STRIP_STYLES)


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


def toolbar_group_label_spec() -> dict[str, object]:
    return dict(TOOLBAR_GROUP_LABEL_SPEC)


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
