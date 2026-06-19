from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ads1292_studio.display import display_gain_labels, display_window_labels, sweep_speed_labels
from ads1292_studio.gui_specs import (
    ADS1292R_ECG_SOURCE,
    SIGNAL_CARD_LABELS,
    STATUS_CARD_LABELS,
    header_connection_style,
    header_layout_spec,
    header_text_styles,
    main_tab_labels,
    sidebar_action_button_style,
    sidebar_field_styles,
    sidebar_layout_spec,
    toolbar_button_style,
    toolbar_control_styles,
    toolbar_group_padding,
    toolbar_group_label_spec,
    toolbar_label_spec,
    toolbar_layout_spec,
    workspace_layout_spec,
    workspace_notebook_styles,
)
from ads1292_studio.protocol import protocol_template


def build_header(app: Any) -> None:
    header_spec = header_layout_spec()
    header = ttk.Frame(app, padding=header_spec["padding"], style=str(header_spec["frame"]))
    header.pack(side=tk.TOP, fill=tk.X)
    app.header_frame = header
    header_text = header_text_styles()
    app.header_title_label = ttk.Label(header, text="ADS1292 Studio", style=str(header_text["title"]["style"]))
    app.header_title_label.pack(side=tk.LEFT)
    app.header_subtitle_label = ttk.Label(
        header,
        text="MOTAC ECG validation",
        style=str(header_text["subtitle"]["style"]),
    )
    app.header_subtitle_label.pack(side=tk.LEFT, padx=header_spec["subtitle_padding"])
    app.connection_label = ttk.Label(
        header,
        textvariable=app.connection_var,
        style=header_connection_style("warning"),
    )
    app.connection_label.pack(side=tk.RIGHT)
    app.header_separator = ttk.Frame(
        app,
        height=header_spec["separator_height"],
        style=str(header_spec["separator"]),
    )
    app.header_separator.pack(side=tk.TOP, fill=tk.X)


def build_acquisition_toolbar(app: Any) -> None:
    toolbar_spec = toolbar_layout_spec()
    toolbar = ttk.Frame(app, padding=toolbar_spec["padding"], style=str(toolbar_spec["frame"]))
    toolbar.pack(side=tk.TOP, fill=tk.X)
    app.toolbar_frame = toolbar
    toolbar_styles = toolbar_control_styles()

    _toolbar_group_label(toolbar, "Input")
    ttk.Label(toolbar, text="Port", style=str(toolbar_label_spec()["style"])).pack(side=tk.LEFT)
    app.port_var = tk.StringVar()
    app.port_combo = ttk.Combobox(
        toolbar,
        textvariable=app.port_var,
        width=int(toolbar_spec["port_width"]),
        style=toolbar_styles["port"],
    )
    app.port_combo.pack(side=tk.LEFT, padx=toolbar_spec["port_padding"])
    app.refresh_button = ttk.Button(
        toolbar,
        text="Refresh",
        command=app.refresh_ports,
        style=toolbar_button_style("Refresh"),
    )
    app.refresh_button.pack(side=tk.LEFT, padx=toolbar_spec["refresh_padding"])
    app.connect_button = ttk.Button(
        toolbar,
        text="Connect",
        command=app.connect,
        style=toolbar_button_style("Connect"),
    )
    app.connect_button.pack(side=tk.LEFT, padx=toolbar_spec["primary_action_padding"])
    app.start_button = ttk.Button(
        toolbar,
        text="Start",
        command=app.start,
        style=toolbar_button_style("Start"),
    )
    app.start_button.pack(side=tk.LEFT, padx=toolbar_spec["inline_action_padding"])
    app.stop_button = ttk.Button(
        toolbar,
        text="Stop",
        command=app.stop,
        style=toolbar_button_style("Stop"),
    )
    app.stop_button.pack(side=tk.LEFT)
    app.toolbar_acquisition_separator = ttk.Frame(
        toolbar,
        width=toolbar_spec["separator_width"],
        style="ToolbarSeparator.TFrame",
    )
    app.toolbar_acquisition_separator.pack(
        side=tk.LEFT,
        fill=tk.Y,
        padx=toolbar_group_padding()["separator"],
    )

    _toolbar_group_label(toolbar, "Record")
    app.save_var = tk.BooleanVar(value=True)
    app.save_check = ttk.Checkbutton(
        toolbar,
        text="Save CSV",
        variable=app.save_var,
        style=toolbar_styles["toggle"],
    )
    app.save_check.pack(side=tk.LEFT, padx=toolbar_spec["save_padding"])


def build_display_toolbar(
    app: Any,
    *,
    default_display_settings: Any,
    default_filter_settings: Any,
    initial_hint_text: str,
) -> None:
    toolbar_spec = toolbar_layout_spec()
    toolbar_styles = toolbar_control_styles()
    toolbar = ttk.Frame(app, padding=toolbar_spec["padding"], style=str(toolbar_spec["frame"]))
    toolbar.pack(side=tk.TOP, fill=tk.X)
    app.display_toolbar_frame = toolbar

    _toolbar_group_label(toolbar, "Display")
    app.autoscale_var = tk.BooleanVar(value=True)
    app.autoscale_check = ttk.Checkbutton(
        toolbar,
        text="Auto scale",
        variable=app.autoscale_var,
        command=app._refresh_display_plots,
        style=toolbar_styles["toggle"],
    )
    app.autoscale_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
    _toolbar_group_label(toolbar, "Filters")
    app.highpass_filter_var = tk.BooleanVar(value=default_filter_settings.highpass_enabled)
    app.highpass_filter_check = ttk.Checkbutton(
        toolbar,
        text="HP",
        variable=app.highpass_filter_var,
        command=app._refresh_display_plots,
        style=toolbar_styles["toggle"],
    )
    app.highpass_filter_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
    app.notch_filter_var = tk.BooleanVar(value=default_filter_settings.notch_enabled)
    app.notch_filter_check = ttk.Checkbutton(
        toolbar,
        text="Notch",
        variable=app.notch_filter_var,
        command=app._refresh_display_plots,
        style=toolbar_styles["toggle"],
    )
    app.notch_filter_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
    app.lowpass_filter_var = tk.BooleanVar(value=default_filter_settings.lowpass_enabled)
    app.lowpass_filter_check = ttk.Checkbutton(
        toolbar,
        text="LP",
        variable=app.lowpass_filter_var,
        command=app._refresh_display_plots,
        style=toolbar_styles["toggle"],
    )
    app.lowpass_filter_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
    app.filter_var = tk.BooleanVar(value=default_filter_settings.bandpass_enabled)
    app.filter_check = ttk.Checkbutton(
        toolbar,
        text="Bandpass",
        variable=app.filter_var,
        command=app._refresh_display_plots,
        style=toolbar_styles["toggle"],
    )
    app.filter_check.pack(side=tk.LEFT, padx=toolbar_spec["toggle_padding"])
    app.display_filter_separator = ttk.Frame(
        toolbar,
        width=toolbar_spec["separator_width"],
        style="ToolbarSeparator.TFrame",
    )
    app.display_filter_separator.pack(side=tk.LEFT, fill=tk.Y, padx=toolbar_group_padding()["separator"])

    _toolbar_group_label(toolbar, "Scale")
    app.display_window_var = tk.StringVar(value=f"{default_display_settings.time_window_seconds:g} s")
    _build_display_combo(app, toolbar, "Window", app.display_window_var, display_window_labels())
    app.display_gain_var = tk.StringVar(value=f"{default_display_settings.gain:g}x")
    _build_display_combo(app, toolbar, "Gain", app.display_gain_var, display_gain_labels())
    app.sweep_speed_var = tk.StringVar(value=f"{default_display_settings.sweep_speed_mm_s} mm/s")
    _build_display_combo(app, toolbar, "Speed", app.sweep_speed_var, sweep_speed_labels())

    app.toolbar_context_separator = ttk.Frame(
        toolbar,
        width=toolbar_spec["separator_width"],
        style="ToolbarSeparator.TFrame",
    )
    app.toolbar_context_separator.pack(side=tk.LEFT, fill=tk.Y, padx=toolbar_group_padding()["separator"])
    app.source_var = tk.StringVar(value=ADS1292R_ECG_SOURCE)
    app.toolbar_hint_var = tk.StringVar(value=initial_hint_text)
    app._build_toolbar_hint_chip(toolbar, app.toolbar_hint_var)


def _toolbar_group_label(toolbar: ttk.Frame, text: str) -> None:
    spec = toolbar_group_label_spec()
    ttk.Label(toolbar, text=text, style=str(spec["style"])).pack(side=tk.LEFT, padx=(2, 5))


def _build_display_combo(
    app: Any,
    toolbar: ttk.Frame,
    label: str,
    variable: tk.StringVar,
    values: tuple[str, ...],
) -> None:
    toolbar_spec = toolbar_layout_spec()
    toolbar_styles = toolbar_control_styles()
    ttk.Label(toolbar, text=label, style=str(toolbar_label_spec()["style"])).pack(
        side=tk.LEFT,
        padx=toolbar_spec["display_label_padding"],
    )
    combo = ttk.Combobox(
        toolbar,
        textvariable=variable,
        width=int(toolbar_spec["display_width"]),
        values=values,
        state="readonly",
        style=toolbar_styles["port"],
    )
    combo.pack(side=tk.LEFT, padx=toolbar_spec["display_control_padding"])
    combo.bind("<<ComboboxSelected>>", app._refresh_display_plots)
    setattr(app, f"{label.lower().replace(' ', '_')}_combo", combo)


def build_body_shell(app: Any) -> tuple[dict[str, ttk.Frame], ttk.Frame]:
    body = ttk.PanedWindow(app, orient=tk.HORIZONTAL)
    body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    app.body_pane = body
    workspace_spec = workspace_layout_spec()
    sidebar_spec = sidebar_layout_spec()
    side_shell = ttk.Frame(
        body,
        width=sidebar_spec["width"],
        padding=sidebar_spec["padding"],
        style=str(sidebar_spec["shell"]),
    )
    app.sidebar_shell = side_shell
    body.add(side_shell, weight=workspace_spec["sidebar_weight"])
    sidebar = app._build_sidebar(side_shell)
    main = ttk.Frame(body, padding=workspace_spec["main_padding"], style=str(workspace_spec["main"]))
    app.main_workspace = main
    body.add(main, weight=workspace_spec["main_weight"])
    return sidebar, main


def initialize_sidebar_state(app: Any, *, protocol_steps_text: str) -> None:
    app.metrics_var = tk.StringVar(value="No session")
    app.quality_var = tk.StringVar(value="Quality: --")
    app.path_var = tk.StringVar(value="CSV: --")
    app.workflow_hint_var = tk.StringVar(value="")
    app.status_overview_var = tk.StringVar(value="")
    app.status_card_vars = {label: tk.StringVar(value="") for label in STATUS_CARD_LABELS}
    app.status_card_label_widgets = {}
    app.status_card_value_labels = {}
    app.status_card_tone_stripes = {}
    app.channel_map_label_widgets = {}
    app.channel_map_value_labels = {}
    app.channel_map_tone_stripes = {}
    app.status_detail_value_labels = {}
    app.signal_card_vars = {label: tk.StringVar(value="") for label in SIGNAL_CARD_LABELS}
    app.signal_card_label_widgets = {}
    app.signal_card_value_labels = {}
    app.signal_card_tone_stripes = {}
    app.session_id_var = tk.StringVar(value="untitled-session")
    app.subject_id_var = tk.StringVar(value="anonymous")
    app.electrode_var = tk.StringVar(value="commercial Ag/AgCl control")
    app.montage_var = tk.StringVar(value="RA/LA/RL torso")
    app.operator_var = tk.StringVar(value="")
    app.notes_var = tk.StringVar(value="")
    app.event_label_var = tk.StringVar(value="motion")
    app.event_notes_var = tk.StringVar(value="")
    app.event_count_var = tk.StringVar(value="0 events")
    app.event_count_label = None
    app.calibration_label_var = tk.StringVar(value="ADS1292 default")
    app.vref_mv_var = tk.StringVar(value="2420")
    app.pga_gain_var = tk.StringVar(value="6")
    app.gate_min_duration_var = tk.StringVar(value="8")
    app.gate_min_contact_var = tk.StringVar(value="95")
    app.gate_min_r_peaks_var = tk.StringVar(value="5")
    app.gate_min_hr_var = tk.StringVar(value="35")
    app.gate_max_hr_var = tk.StringVar(value="180")
    app.gate_require_qrs_var = tk.BooleanVar(value=True)
    app.gate_max_drift_var = tk.StringVar(value="")
    app.gate_max_noise_var = tk.StringVar(value="")
    app.gate_max_ptp_var = tk.StringVar(value="")
    protocol = protocol_template()
    app.protocol_name_var = tk.StringVar(value=protocol.name)
    app.protocol_objective_var = tk.StringVar(value=protocol.objective)
    app.protocol_steps_var = tk.StringVar(value=protocol_steps_text)
    app.protocol_acceptance_var = tk.StringVar(value=protocol.acceptance_notes)
    app.protocol_note_labels = {}


def populate_sidebar(app: Any, sidebar: dict[str, ttk.Frame]) -> None:
    status_side = sidebar["Status"]
    session_side = sidebar["Session"]
    validation_side = sidebar["Validation"]
    protocol_side = sidebar["Protocol"]
    actions_side = sidebar["Actions"]

    ttk.Label(status_side, text="Next Step", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 6))
    app._build_workflow_hint(status_side)
    ttk.Label(status_side, text="Overview", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 6))
    app._build_status_cards(status_side)
    ttk.Label(status_side, text="Channel Map", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 6))
    app._build_channel_map_cards(status_side)
    ttk.Label(status_side, text="Signal Quality", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 6))
    app._build_signal_quality_cards(status_side)
    for label, var in (("Session", app.metrics_var), ("Quality", app.quality_var), ("Storage", app.path_var)):
        app._build_status_detail_card(status_side, label, var)

    ttk.Label(session_side, text="Recording Notes", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
    app._metadata_entry(session_side, "Session ID", app.session_id_var)
    app._metadata_entry(session_side, "Subject", app.subject_id_var)
    app._metadata_entry(session_side, "Electrode", app.electrode_var)
    app._metadata_entry(session_side, "Montage", app.montage_var)
    app._metadata_entry(session_side, "Operator", app.operator_var)
    app._metadata_entry(session_side, "Notes", app.notes_var)
    ttk.Label(session_side, text="Events", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
    app._metadata_entry(session_side, "Event label", app.event_label_var)
    app._metadata_entry(session_side, "Event notes", app.event_notes_var)
    app.add_event_button = _sidebar_button(session_side, "Add Event", app.add_event)
    app._build_event_count_card(session_side)

    ttk.Label(validation_side, text="Calibration", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
    app._metadata_entry(validation_side, "Label", app.calibration_label_var)
    app._metadata_entry(validation_side, "Vref mV", app.vref_mv_var)
    app._metadata_entry(validation_side, "PGA gain", app.pga_gain_var)
    ttk.Label(validation_side, text="Quality Gate", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
    app._metadata_entry(validation_side, "Min duration s", app.gate_min_duration_var)
    app._metadata_entry(validation_side, "Min contact %", app.gate_min_contact_var)
    app._metadata_entry(validation_side, "Min R peaks", app.gate_min_r_peaks_var)
    app._metadata_entry(validation_side, "HR min bpm", app.gate_min_hr_var)
    app._metadata_entry(validation_side, "HR max bpm", app.gate_max_hr_var)
    app.gate_require_qrs_check = ttk.Checkbutton(
        validation_side,
        text="Require QRS clear",
        variable=app.gate_require_qrs_var,
        style=sidebar_field_styles()["check"],
    )
    app.gate_require_qrs_check.pack(anchor=tk.W, pady=(5, 2))
    app._metadata_entry(validation_side, "Max drift counts", app.gate_max_drift_var)
    app._metadata_entry(validation_side, "Max noise RMS", app.gate_max_noise_var)
    app._metadata_entry(validation_side, "Max peak-to-peak", app.gate_max_ptp_var)

    ttk.Label(protocol_side, text="Protocol", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
    app._metadata_entry(protocol_side, "Name", app.protocol_name_var)
    app._metadata_entry(protocol_side, "Objective", app.protocol_objective_var)
    app._build_protocol_note_card(protocol_side, "Steps", app.protocol_steps_var)
    app._build_protocol_note_card(protocol_side, "Acceptance", app.protocol_acceptance_var)

    app.action_section_labels = {}
    app._build_action_section_heading(actions_side, "Review", top_padding=8)
    app.load_csv_button = _sidebar_button(actions_side, "Load CSV", app.load_csv)
    app.export_report_button = _sidebar_button(actions_side, "Export Report", app.export_report)
    app._build_action_section_heading(actions_side, "Package")
    app.export_package_button = _sidebar_button(actions_side, "Export Package", app.export_package)
    app.verify_package_button = _sidebar_button(actions_side, "Verify Package", app.verify_package)
    app._build_action_section_heading(actions_side, "Library")
    app.batch_compare_button = _sidebar_button(actions_side, "Batch Compare", app.batch_compare)
    app.session_index_button = _sidebar_button(actions_side, "Session Index", app.session_index)
    app._build_action_section_heading(actions_side, "Safety")
    app._build_safety_notice(actions_side)


def _sidebar_button(parent: ttk.Frame, text: str, command: object) -> ttk.Button:
    button = ttk.Button(parent, text=text, command=command, style=sidebar_action_button_style())
    button.pack(anchor=tk.W, fill=tk.X, pady=2)
    return button


def build_workspace_tabs(app: Any, main: ttk.Frame) -> None:
    app.notebook = ttk.Notebook(main, style=workspace_notebook_styles()["notebook"])
    app.notebook.pack(fill=tk.BOTH, expand=True)
    app.live_tab = ttk.Frame(app.notebook)
    app.review_tab = ttk.Frame(app.notebook)
    app.pqrst_tab = ttk.Frame(app.notebook)
    app.log_tab = ttk.Frame(app.notebook)
    live_label, review_label, pqrst_label, log_label = main_tab_labels()
    app.notebook.add(app.live_tab, text=live_label)
    app.notebook.add(app.review_tab, text=review_label)
    app.notebook.add(app.pqrst_tab, text=pqrst_label)
    app.notebook.add(app.log_tab, text=log_label)


def register_control_buttons(app: Any) -> None:
    app.control_buttons = {
        "Refresh": app.refresh_button,
        "Connect": app.connect_button,
        "Start": app.start_button,
        "Stop": app.stop_button,
        "Load CSV": app.load_csv_button,
        "Export Report": app.export_report_button,
        "Export Package": app.export_package_button,
        "Verify Package": app.verify_package_button,
        "Batch Compare": app.batch_compare_button,
        "Session Index": app.session_index_button,
    }
