from ads1292_studio.app import (
    action_section_styles,
    ads1292r_plot_layout_labels,
    app_visual_tokens,
    app_window_spec,
    button_chrome_spec,
    card_label_spec,
    empty_plot_messages,
    empty_plot_style,
    event_count_styles,
    header_connection_styles,
    header_layout_spec,
    input_chrome_spec,
    log_panel_spec,
    main_tab_labels,
    panel_chrome_spec,
    plot_axis_style,
    plot_canvas_widget_style,
    plot_figure_layouts,
    plot_panel_spec,
    plot_trace_colors,
    primary_toolbar_button_labels,
    protocol_note_styles,
    safety_notice_styles,
    scrollbar_chrome_spec,
    secondary_action_button_labels,
    section_heading_styles,
    sidebar_action_button_style,
    sidebar_field_styles,
    sidebar_layout_spec,
    sidebar_notebook_styles,
    sidebar_tab_labels,
    sidebar_text_card_spec,
    status_detail_styles,
    toolbar_button_style,
    toolbar_control_styles,
    toolbar_group_padding,
    toolbar_hint_styles,
    toolbar_label_spec,
    toolbar_layout_spec,
    workflow_hint_styles,
    workspace_layout_spec,
    workspace_notebook_styles,
)


def test_gui_layout_keeps_primary_toolbar_focused_on_acquisition() -> None:
    assert primary_toolbar_button_labels() == ("Refresh", "Connect", "Start", "Stop")
    assert "Load CSV" not in primary_toolbar_button_labels()
    assert "Export Report" not in primary_toolbar_button_labels()
    assert "Session Index" not in primary_toolbar_button_labels()


def test_app_window_spec_prevents_cramped_signal_views() -> None:
    assert app_window_spec() == {
        "geometry": "1320x860",
        "min_size": (1120, 740),
    }


def test_gui_layout_assigns_toolbar_action_hierarchy() -> None:
    assert toolbar_button_style("Refresh") == "TButton"
    assert toolbar_button_style("Connect") == "Primary.TButton"
    assert toolbar_button_style("Start") == "Primary.TButton"
    assert toolbar_button_style("Stop") == "Stop.TButton"
    assert toolbar_button_style("Unknown") == "TButton"


def test_button_chrome_spec_makes_actions_visually_distinct() -> None:
    assert button_chrome_spec() == {
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
            "padding": (10, 7),
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


def test_gui_layout_styles_toolbar_inputs_and_toggles() -> None:
    assert toolbar_control_styles() == {
        "port": "Port.TCombobox",
        "toggle": "ToolbarToggle.TCheckbutton",
    }


def test_toolbar_label_spec_keeps_toolbar_labels_consistent() -> None:
    assert toolbar_label_spec() == {
        "style": "ToolbarLabel.TLabel",
        "font": ("Aptos", 12, "bold"),
        "background": "#EEF3FA",
        "foreground": "#172033",
    }


def test_input_chrome_spec_keeps_forms_readable() -> None:
    assert input_chrome_spec() == {
        "label": {
            "font": ("Aptos", 10, "bold"),
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
    }


def test_gui_layout_frames_toolbar_channel_hint_as_chip() -> None:
    assert toolbar_hint_styles() == {
        "frame": "ToolbarHint.TFrame",
        "label": "ToolbarHint.TLabel",
        "background": "#EAF1FF",
        "foreground": "#1F4FB2",
        "font": ("Aptos", 11, "bold"),
        "border": "#D9E1EC",
        "borderwidth": 1,
        "relief": "solid",
    }


def test_gui_layout_spaces_toolbar_groups() -> None:
    assert toolbar_group_padding() == {
        "separator": (12, 8),
        "tight": (4, 4),
    }


def test_toolbar_layout_spec_keeps_acquisition_controls_ordered() -> None:
    assert toolbar_layout_spec() == {
        "frame": "Toolbar.TFrame",
        "padding": (16, 10, 16, 10),
        "port_width": 36,
        "port_padding": (8, 8),
        "refresh_padding": (0, 4),
        "primary_action_padding": (12, 4),
        "inline_action_padding": (4, 4),
        "save_padding": (8, 4),
        "toggle_padding": (4, 4),
        "separator_width": 1,
        "hint_padding": (10, 5),
    }


def test_gui_layout_groups_secondary_actions_in_sidebar() -> None:
    assert secondary_action_button_labels() == (
        "Load CSV",
        "Export Report",
        "Export Package",
        "Verify Package",
        "Batch Compare",
        "Session Index",
    )


def test_gui_layout_uses_task_based_sidebar_tabs() -> None:
    assert sidebar_tab_labels() == ("Status", "Session", "Validation", "Protocol", "Actions")


def test_sidebar_notebook_styles_make_navigation_compact() -> None:
    assert sidebar_notebook_styles() == {
        "notebook": "Sidebar.TNotebook",
        "tab": "Sidebar.TNotebook.Tab",
        "tab_padding": (10, 6),
        "tab_font": ("Aptos", 10, "bold"),
        "tab_background": "#EEF3FA",
        "selected_foreground": "#2F6FED",
        "inactive_foreground": "#657084",
        "active_foreground": "#172033",
        "active_background": "#FFFFFF",
    }


def test_sidebar_layout_spec_stabilizes_control_column() -> None:
    assert sidebar_layout_spec() == {
        "shell": "SidebarShell.TFrame",
        "width": 348,
        "padding": (12, 12),
        "scroll_width": 316,
    }


def test_gui_layout_names_main_workspaces_clearly() -> None:
    assert main_tab_labels() == ("Live ECG", "Review CSV", "PQRST Beat", "Event Log")


def test_workspace_layout_spec_balances_sidebar_and_signal_area() -> None:
    assert workspace_layout_spec() == {
        "main": "Main.TFrame",
        "main_padding": (8, 12, 14, 12),
        "sidebar_weight": 0,
        "main_weight": 1,
    }


def test_header_connection_styles_make_status_a_pill() -> None:
    assert header_connection_styles() == {
        "styles": {
            "ready": "Ready.Connection.TLabel",
            "running": "Running.Connection.TLabel",
            "warning": "Warning.Connection.TLabel",
            "neutral": "Neutral.Connection.TLabel",
        },
        "padding": (10, 5),
        "font": ("Aptos", 12, "bold"),
        "borderwidth": 1,
        "relief": "solid",
        "backgrounds": {
            "ready": "#E9F6EE",
            "running": "#EAF1FF",
            "warning": "#FFF4E3",
            "neutral": "#EEF3FA",
        },
    }


def test_header_layout_spec_gives_top_bar_clear_structure() -> None:
    assert header_layout_spec() == {
        "frame": "Header.TFrame",
        "separator": "HeaderSeparator.TFrame",
        "padding": (20, 14, 20, 12),
        "subtitle_padding": (14, 0),
        "separator_height": 1,
    }


def test_workspace_notebook_styles_make_selected_tabs_visible() -> None:
    assert workspace_notebook_styles() == {
        "notebook": "Workspace.TNotebook",
        "tab": "Workspace.TNotebook.Tab",
        "tab_padding": (16, 8),
        "tab_font": ("Aptos", 12, "bold"),
        "tab_background": "#EEF3FA",
        "selected_foreground": "#2F6FED",
        "inactive_foreground": "#657084",
        "active_foreground": "#172033",
        "active_background": "#FFFFFF",
    }


def test_sidebar_field_styles_make_forms_consistent() -> None:
    assert sidebar_field_styles() == {
        "label": "FieldLabel.TLabel",
        "entry": "Field.TEntry",
        "check": "FieldCheck.TCheckbutton",
    }


def test_section_heading_styles_make_sidebar_groups_scannable() -> None:
    assert section_heading_styles() == {
        "label": "SectionHeading.TLabel",
        "padding": (2, 5),
        "font": ("Aptos", 12, "bold"),
        "background": "#F6F8FB",
        "foreground": "#1F4FB2",
    }


def test_sidebar_action_button_style_keeps_secondary_actions_consistent() -> None:
    assert sidebar_action_button_style() == "SidebarAction.TButton"


def test_action_section_styles_make_sidebar_action_groups_scannable() -> None:
    assert action_section_styles() == {
        "frame": "ActionSection.TFrame",
        "label": "ActionSection.TLabel",
        "padding": (8, 5),
        "font": ("Aptos", 10, "bold"),
        "background": "#EEF3FA",
        "foreground": "#1F4FB2",
    }


def test_workflow_hint_styles_make_next_step_prominent() -> None:
    assert workflow_hint_styles() == {
        "frame": "WorkflowHint.TFrame",
        "label": "WorkflowHint.TLabel",
        "stripe": "#2F6FED",
    }


def test_safety_notice_styles_make_research_use_boundary_visible() -> None:
    assert safety_notice_styles() == {
        "frame": "SafetyNotice.TFrame",
        "label": "SafetyNotice.TLabel",
        "stripe": "#A76400",
    }


def test_sidebar_text_card_spec_keeps_long_notes_readable() -> None:
    assert sidebar_text_card_spec() == {
        "stripe_width": 4,
        "label_padding": (10, 8),
        "content_padding": (10, 8),
        "primary_wrap": 240,
        "detail_wrap": 230,
        "value_top_padding": (3, 0),
    }


def test_status_detail_styles_frame_session_quality_and_storage() -> None:
    assert status_detail_styles() == {
        "frame": "StatusDetail.TFrame",
        "label": "StatusDetailLabel.TLabel",
        "value": "StatusDetailValue.TLabel",
        "stripe": "#D9E1EC",
    }


def test_card_label_spec_keeps_status_cards_scannable() -> None:
    assert card_label_spec() == {
        "width": 12,
        "content_padding": (10, 8),
        "signal_value_wrap": 170,
    }


def test_event_count_styles_make_session_events_visible() -> None:
    assert event_count_styles() == {
        "frame": "EventCount.TFrame",
        "label": "EventCountLabel.TLabel",
        "value": "EventCountValue.TLabel",
        "stripe": "#7A5CDB",
    }


def test_protocol_note_styles_make_long_protocol_text_readable() -> None:
    assert protocol_note_styles() == {
        "frame": "ProtocolNote.TFrame",
        "label": "ProtocolNoteLabel.TLabel",
        "value": "ProtocolNoteValue.TLabel",
        "stripe": "#2F6FED",
    }


def test_gui_layout_uses_ads1292r_synchronized_three_panel_view() -> None:
    assert ads1292r_plot_layout_labels() == (
        "CH2 ECG Lead I (LA-RA)",
        "CH1 Respiration raw",
        "Lead-off / contact status",
    )


def test_gui_visual_tokens_define_a_complete_light_theme() -> None:
    tokens = app_visual_tokens()

    assert tokens["surface"] == "#F6F8FB"
    assert tokens["panel"] == "#FFFFFF"
    assert tokens["ink"] == "#172033"
    assert tokens["accent"] == "#2F6FED"
    assert set(tokens) >= {"surface", "panel", "panel_alt", "ink", "muted", "border", "accent", "success", "warning"}


def test_plot_trace_colors_distinguish_ecg_respiration_and_contact() -> None:
    colors = plot_trace_colors()

    assert colors["ecg"] != colors["respiration"]
    assert colors["contact"] != colors["ecg"]
    assert colors["peak"] == "#E34A4A"


def test_empty_plot_messages_guide_the_first_run_workflow() -> None:
    messages = empty_plot_messages()

    assert messages["live"] == (
        "Connect an ADS1292 board, then press Start",
        "CH1 respiration/contact context appears here",
        "Lead-off status stays at 0 when contacts are good",
    )
    assert messages["review"][0] == "Load a CSV to review recorded ECG"
    assert messages["pqrst"] == ("Load or record data to build the averaged PQRST beat",)


def test_empty_plot_style_uses_muted_callouts() -> None:
    assert empty_plot_style() == {
        "text_color": "#516070",
        "box_face": "#F8FAFD",
        "box_edge": "#D9E1EC",
        "font_size": 11,
        "font_weight": "bold",
        "alpha": 0.96,
        "box_pad": 0.55,
        "rounding": 0.18,
        "line_width": 0.8,
    }


def test_log_panel_spec_keeps_long_sessions_readable() -> None:
    assert log_panel_spec() == {
        "shell": "Main.TFrame",
        "panel": "LogPanel.TFrame",
        "padding": (14, 14),
        "panel_padding": (8, 8),
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


def test_scrollbar_chrome_spec_keeps_scroll_surfaces_subtle() -> None:
    assert scrollbar_chrome_spec() == {
        "vertical": "App.Vertical.TScrollbar",
        "width": 12,
        "background": "#A9B4C3",
        "active_background": "#657084",
        "trough": "#EEF3FA",
        "border": "#EEF3FA",
        "arrow": "#657084",
        "relief": "flat",
        "borderwidth": 0,
    }


def test_panel_chrome_spec_softens_repeated_card_borders() -> None:
    assert panel_chrome_spec() == {
        "background": "#FFFFFF",
        "border": "#D9E1EC",
        "borderwidth": 1,
        "relief": "solid",
    }


def test_plot_panel_spec_frames_signal_workspaces() -> None:
    assert plot_panel_spec() == {
        "shell": "Main.TFrame",
        "panel": "PlotPanel.TFrame",
        "padding": (14, 14),
        "panel_padding": (8, 8),
    }


def test_plot_axis_style_keeps_signal_charts_quiet_and_readable() -> None:
    assert plot_axis_style() == {
        "face": "#FFFFFF",
        "grid": "#D9E1EC",
        "spine": "#D9E1EC",
        "tick": "#657084",
        "label": "#172033",
        "grid_linewidth": 0.7,
        "grid_alpha": 0.45,
        "spine_linewidth": 0.8,
        "tick_label_size": 9,
        "label_size": 10,
        "title_size": 11,
        "title_weight": "bold",
        "title_pad": 8,
    }


def test_plot_figure_layouts_keep_signal_panels_dense() -> None:
    assert plot_figure_layouts() == {
        "three_panel": {
            "left": 0.075,
            "right": 0.985,
            "top": 0.965,
            "bottom": 0.075,
            "hspace": 0.34,
        },
        "single_panel": {
            "left": 0.08,
            "right": 0.985,
            "top": 0.955,
            "bottom": 0.12,
        },
    }


def test_plot_figure_layouts_returns_nested_copies() -> None:
    layouts = plot_figure_layouts()
    layouts["three_panel"]["hspace"] = 9.0

    assert plot_figure_layouts()["three_panel"]["hspace"] == 0.34


def test_plot_canvas_widget_style_removes_embedded_canvas_chrome() -> None:
    assert plot_canvas_widget_style() == {
        "background": "#FFFFFF",
        "borderwidth": 0,
        "highlightthickness": 0,
    }
