import inspect

from ads1292_studio.app import (
    action_section_styles,
    ads1292r_plot_layout_labels,
    app_visual_tokens,
    app_window_spec,
    base_checkbutton_style,
    base_chrome_spec,
    base_notebook_styles,
    button_chrome_spec,
    card_label_spec,
    channel_map_cards,
    empty_plot_messages,
    empty_plot_style,
    event_count_styles,
    format_log_entries,
    header_connection_styles,
    header_frame_spec,
    header_layout_spec,
    header_text_styles,
    input_chrome_spec,
    live_axis_spec,
    log_panel_spec,
    main_tab_labels,
    muted_label_spec,
    panel_chrome_spec,
    plot_axis_style,
    plot_canvas_widget_style,
    plot_figure_layouts,
    plot_panel_spec,
    plot_trace_colors,
    plot_trace_styles,
    pqrst_plot_style,
    primary_toolbar_button_labels,
    protocol_note_styles,
    safety_notice_styles,
    scrollbar_chrome_spec,
    scrollable_frame_spec,
    secondary_action_button_labels,
    section_heading_styles,
    seaborn_plot_theme,
    sidebar_action_button_style,
    sidebar_field_styles,
    sidebar_layout_spec,
    sidebar_notebook_styles,
    sidebar_tab_labels,
    sidebar_text_card_spec,
    status_axis_spec,
    status_detail_styles,
    toolbar_button_style,
    toolbar_control_styles,
    toolbar_frame_spec,
    toolbar_group_padding,
    toolbar_group_label_spec,
    toolbar_hint_styles,
    toolbar_label_spec,
    toolbar_layout_spec,
    workflow_hint_styles,
    workspace_layout_spec,
    workspace_notebook_styles,
)
from ads1292_studio.plot_theme import new_export_figure, style_export_axes


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
            "padding": (9, 5),
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
            "padding": (10, 5),
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
            "padding": (10, 5),
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
            "padding": (10, 5),
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


def test_toolbar_frame_spec_groups_acquisition_controls_as_one_surface() -> None:
    assert toolbar_frame_spec() == {
        "frame": "Toolbar.TFrame",
        "separator": "ToolbarSeparator.TFrame",
        "background": "#EEF3FA",
        "separator_background": "#D9E1EC",
        "borderwidth": 1,
        "relief": "flat",
    }


def test_toolbar_label_spec_keeps_toolbar_labels_consistent() -> None:
    assert toolbar_label_spec() == {
        "style": "ToolbarLabel.TLabel",
        "font": ("Aptos", 11, "bold"),
        "background": "#EEF3FA",
        "foreground": "#172033",
    }


def test_toolbar_group_label_spec_adds_scanable_control_groups() -> None:
    assert toolbar_group_label_spec() == {
        "style": "ToolbarGroupLabel.TLabel",
        "font": ("Aptos", 9, "bold"),
        "background": "#EEF3FA",
        "foreground": "#657084",
        "padding": (2, 2),
    }


def test_input_chrome_spec_keeps_forms_readable() -> None:
    assert input_chrome_spec() == {
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
            "padding": (4, 3),
            "font": ("Aptos", 10, "bold"),
            "background": "#EEF3FA",
            "foreground": "#293247",
            "active_foreground": "#1F4FB2",
            "disabled_foreground": "#657084",
            "active_background": "#EAF1FF",
        },
    }


def test_gui_layout_frames_toolbar_channel_hint_as_chip() -> None:
    assert toolbar_hint_styles() == {
        "frame": "ToolbarHint.TFrame",
        "label": "ToolbarHint.TLabel",
        "background": "#EAF1FF",
        "foreground": "#293247",
        "font": ("Aptos", 10, "bold"),
        "border": "#EAF1FF",
        "borderwidth": 0,
        "relief": "flat",
    }


def test_toolbar_hint_chip_uses_dynamic_textvariable() -> None:
    from ads1292_studio.app import App

    source = inspect.getsource(App._build_toolbar_hint_chip)

    assert "textvariable=variable" in source
    assert "text=" not in source


def test_gui_layout_spaces_toolbar_groups() -> None:
    assert toolbar_group_padding() == {
        "separator": (8, 6),
        "tight": (3, 3),
    }


def test_toolbar_layout_spec_keeps_acquisition_controls_ordered() -> None:
    assert toolbar_layout_spec() == {
        "frame": "Toolbar.TFrame",
        "padding": (12, 6, 12, 6),
        "port_width": 36,
        "port_padding": (6, 6),
        "refresh_padding": (0, 3),
        "primary_action_padding": (8, 3),
        "inline_action_padding": (3, 3),
        "save_padding": (6, 3),
        "toggle_padding": (3, 3),
        "display_label_padding": (4, 3),
        "display_control_padding": (3, 6),
        "display_width": 9,
        "separator_width": 1,
        "hint_padding": (10, 4),
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


def test_base_notebook_styles_keep_tab_defaults_consistent() -> None:
    assert base_notebook_styles() == {
        "notebook": "TNotebook",
        "tab": "TNotebook.Tab",
        "background": "#F6F8FB",
        "borderwidth": 0,
        "tab_padding": (14, 6),
        "tab_font": ("Aptos", 12, "bold"),
        "tab_borderwidth": 0,
        "tab_relief": "flat",
    }


def test_base_checkbutton_style_keeps_default_toggles_consistent() -> None:
    assert base_checkbutton_style() == {
        "style": "TCheckbutton",
        "background": "#EEF3FA",
        "foreground": "#172033",
    }


def test_sidebar_notebook_styles_make_navigation_compact() -> None:
    assert sidebar_notebook_styles() == {
        "notebook": "Sidebar.TNotebook",
        "tab": "Sidebar.TNotebook.Tab",
        "background": "#F6F8FB",
        "borderwidth": 0,
        "tab_padding": (11, 6),
        "tab_font": ("Aptos", 10, "bold"),
        "tab_background": "#EEF3FA",
        "selected_foreground": "#2F6FED",
        "inactive_foreground": "#657084",
        "active_foreground": "#172033",
        "active_background": "#FFFFFF",
        "tab_borderwidth": 0,
        "tab_relief": "flat",
    }


def test_sidebar_layout_spec_stabilizes_control_column() -> None:
    assert sidebar_layout_spec() == {
        "shell": "SidebarShell.TFrame",
        "width": 328,
        "padding": (10, 10),
        "scroll_width": 296,
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


def test_header_layout_spec_gives_top_bar_clear_structure() -> None:
    assert header_layout_spec() == {
        "frame": "Header.TFrame",
        "separator": "HeaderSeparator.TFrame",
        "padding": (20, 14, 20, 12),
        "subtitle_padding": (14, 0),
        "separator_height": 1,
    }


def test_header_frame_spec_keeps_app_title_bar_clean() -> None:
    assert header_frame_spec() == {
        "frame": "Header.TFrame",
        "separator": "HeaderSeparator.TFrame",
        "background": "#FFFFFF",
        "separator_background": "#D9E1EC",
        "borderwidth": 0,
    }


def test_header_text_styles_keep_title_and_context_readable() -> None:
    assert header_text_styles() == {
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


def test_workspace_notebook_styles_make_selected_tabs_visible() -> None:
    assert workspace_notebook_styles() == {
        "notebook": "Workspace.TNotebook",
        "tab": "Workspace.TNotebook.Tab",
        "background": "#F6F8FB",
        "borderwidth": 0,
        "tab_padding": (16, 8),
        "tab_font": ("Aptos", 12, "bold"),
        "tab_background": "#EEF3FA",
        "selected_foreground": "#2F6FED",
        "inactive_foreground": "#657084",
        "active_foreground": "#172033",
        "active_background": "#FFFFFF",
        "tab_borderwidth": 0,
        "tab_relief": "flat",
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
        "padding": (2, 4),
        "font": ("Aptos", 11, "bold"),
        "background": "#F6F8FB",
        "foreground": "#293247",
    }


def test_muted_label_spec_keeps_secondary_copy_subtle() -> None:
    assert muted_label_spec() == {
        "style": "Muted.TLabel",
        "font": ("Aptos", 11),
        "background": "#F6F8FB",
        "foreground": "#657084",
    }


def test_sidebar_action_button_style_keeps_secondary_actions_consistent() -> None:
    assert sidebar_action_button_style() == "SidebarAction.TButton"


def test_action_section_styles_make_sidebar_action_groups_scannable() -> None:
    assert action_section_styles() == {
        "frame": "ActionSection.TFrame",
        "label": "ActionSection.TLabel",
        "padding": (8, 4),
        "font": ("Aptos", 10, "bold"),
        "background": "#EEF3FA",
        "foreground": "#293247",
    }


def test_workflow_hint_styles_make_next_step_prominent() -> None:
    assert workflow_hint_styles() == {
        "frame": "WorkflowHint.TFrame",
        "label": "WorkflowHint.TLabel",
        "stripe": "#2F6FED",
        "background": "#EAF1FF",
        "foreground": "#1F4FB2",
        "font": ("Aptos", 11, "bold"),
    }


def test_safety_notice_styles_make_research_use_boundary_visible() -> None:
    assert safety_notice_styles() == {
        "frame": "SafetyNotice.TFrame",
        "label": "SafetyNotice.TLabel",
        "stripe": "#A76400",
        "background": "#FFF4E3",
        "foreground": "#6B4700",
        "font": ("Aptos", 11, "bold"),
    }


def test_sidebar_text_card_spec_keeps_long_notes_readable() -> None:
    assert sidebar_text_card_spec() == {
        "stripe_width": 4,
        "label_padding": (10, 6),
        "content_padding": (10, 6),
        "primary_wrap": 220,
        "detail_wrap": 215,
        "value_top_padding": (2, 0),
    }


def test_status_detail_styles_frame_session_quality_and_storage() -> None:
    assert status_detail_styles() == {
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


def test_card_label_spec_keeps_status_cards_scannable() -> None:
    assert card_label_spec() == {
        "style": "CardLabel.TLabel",
        "font": ("Aptos", 11),
        "background": "#FFFFFF",
        "foreground": "#657084",
        "width": 12,
        "content_padding": (10, 6),
        "stripe_width": 5,
        "row_padding": (0, 2),
        "value_padding": (6, 0),
        "signal_value_wrap": 160,
    }


def test_event_count_styles_make_session_events_visible() -> None:
    assert event_count_styles() == {
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


def test_protocol_note_styles_make_long_protocol_text_readable() -> None:
    assert protocol_note_styles() == {
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


def test_gui_layout_uses_ads1292r_synchronized_three_panel_view() -> None:
    assert ads1292r_plot_layout_labels() == (
        "CH2 ECG Lead I (LA-RA)",
        "CH1 Respiration raw",
        "Lead-off / contact status",
    )


def test_channel_map_cards_explain_live_dual_channel_mapping() -> None:
    cards = channel_map_cards()

    assert [(card.label, card.value, card.tone) for card in cards] == [
        ("ECG", "CH2 Lead I (LA-RA)", "running"),
        ("Respiration", "CH1 raw impedance", "neutral"),
        ("Contact", "lead-off bits", "neutral"),
    ]


def test_status_sidebar_includes_channel_map_before_signal_quality() -> None:
    from ads1292_studio.gui_layout import populate_sidebar

    source = inspect.getsource(populate_sidebar)

    assert "Channel Map" in source
    assert "app._build_channel_map_cards(status_side)" in source
    assert source.index("Channel Map") < source.index("Signal Quality")


def test_gui_visual_tokens_define_a_complete_light_theme() -> None:
    tokens = app_visual_tokens()

    assert tokens["surface"] == "#F6F8FB"
    assert tokens["panel"] == "#FFFFFF"
    assert tokens["ink"] == "#172033"
    assert tokens["accent"] == "#2F6FED"
    assert set(tokens) >= {"surface", "panel", "panel_alt", "ink", "muted", "border", "accent", "success", "warning"}


def test_base_chrome_spec_keeps_global_window_surfaces_consistent() -> None:
    assert base_chrome_spec() == {
        "font": ("Aptos", 12),
        "background": "#F6F8FB",
        "foreground": "#172033",
        "frame": "TFrame",
        "label": "TLabel",
        "sidebar": "SidebarShell.TFrame",
        "main": "Main.TFrame",
        "borderwidth": 0,
    }


def test_plot_trace_colors_distinguish_ecg_respiration_and_contact() -> None:
    colors = plot_trace_colors()

    assert colors["ecg"] != colors["respiration"]
    assert colors["contact"] != colors["ecg"]
    assert colors["ecg"] == "#0B6FA4"
    assert colors["respiration"] == "#7A5CDB"
    assert colors["peak"] == "#E4572E"


def test_seaborn_plot_theme_uses_clean_signal_grid() -> None:
    theme = seaborn_plot_theme()

    assert theme["style"] == "whitegrid"
    assert theme["context"] == "notebook"
    assert theme["palette"] == "colorblind"
    assert theme["rc"]["axes.facecolor"] == "#FFFFFF"
    assert theme["rc"]["figure.facecolor"] == "#F6F8FB"
    assert theme["rc"]["lines.antialiased"] is True
    assert theme["rc"]["path.simplify"] is True
    assert theme["rc"]["path.simplify_threshold"] == 0.18
    assert theme["rc"]["grid.linewidth"] == 0.62
    assert theme["rc"]["agg.path.chunksize"] == 10000


def test_export_plot_theme_uses_shared_seaborn_surface() -> None:
    fig = new_export_figure(figsize=(4, 2), dpi=100)
    ax = fig.add_subplot(111)

    style_export_axes((ax,))

    assert fig.get_facecolor()[:3] == (246 / 255, 248 / 255, 251 / 255)
    assert ax.get_facecolor()[:3] == (1.0, 1.0, 1.0)
    assert any(line.get_visible() for line in ax.get_xgridlines())


def test_plot_trace_styles_keep_live_and_review_signals_readable() -> None:
    assert plot_trace_styles() == {
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


def test_live_axis_spec_keeps_time_grid_stable() -> None:
    assert live_axis_spec() == {
        "x_major_tick_seconds": 1.0,
    }


def test_plot_trace_styles_returns_nested_copies() -> None:
    styles = plot_trace_styles()
    styles["ecg"]["linewidth"] = 99

    assert plot_trace_styles()["ecg"]["linewidth"] == 1.45


def test_pqrst_plot_style_keeps_morphology_review_readable() -> None:
    assert pqrst_plot_style() == {
        "average": {"linewidth": 2.25, "label": "average beat"},
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


def test_pqrst_plot_style_returns_nested_copies() -> None:
    style = pqrst_plot_style()
    style["average"]["linewidth"] = 99

    assert pqrst_plot_style()["average"]["linewidth"] == 2.25


def test_empty_plot_messages_guide_the_first_run_workflow() -> None:
    messages = empty_plot_messages()

    assert messages["live"] == (
        "Waiting for CH2 ECG Lead I",
        "Waiting for CH1 respiration",
        "Waiting for contact status",
    )
    assert messages["review"] == (
        "Load CSV for CH2 ECG review",
        "Load CSV for CH1 respiration",
        "Load CSV for contact status",
    )
    assert messages["pqrst"] == ("Load or record ECG to review averaged PQRST",)


def test_empty_plot_style_uses_muted_callouts() -> None:
    assert empty_plot_style() == {
        "text_color": "#657084",
        "box_face": "#FFFFFF",
        "box_edge": "#EAF1FF",
        "font_size": 9,
        "font_weight": "bold",
        "alpha": 0.88,
        "box_pad": 0.48,
        "rounding": 0.12,
        "line_width": 0.8,
    }


def test_log_panel_spec_keeps_long_sessions_readable() -> None:
    assert log_panel_spec() == {
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


def test_format_log_entries_batches_messages_with_one_timestamp() -> None:
    assert format_log_entries(("connected", "streaming"), "12:34:56") == (
        "[12:34:56] connected\n"
        "[12:34:56] streaming\n"
    )


def test_scrollbar_chrome_spec_keeps_scroll_surfaces_subtle() -> None:
    assert scrollbar_chrome_spec() == {
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


def test_scrollable_frame_spec_prevents_default_tk_canvas_chrome() -> None:
    assert scrollable_frame_spec() == {
        "canvas_background": "#F6F8FB",
        "content_padding": 10,
        "highlightthickness": 0,
        "borderwidth": 0,
        "relief": "flat",
    }


def test_panel_chrome_spec_softens_repeated_card_borders() -> None:
    assert panel_chrome_spec() == {
        "background": "#FFFFFF",
        "border": "#D9E1EC",
        "borderwidth": 1,
        "relief": "flat",
    }


def test_plot_panel_spec_frames_signal_workspaces() -> None:
    assert plot_panel_spec() == {
        "shell": "Main.TFrame",
        "panel": "PlotPanel.TFrame",
        "padding": (10, 10),
        "panel_padding": (10, 10),
    }


def test_plot_axis_style_keeps_signal_charts_quiet_and_readable() -> None:
    assert plot_axis_style() == {
        "face": "#FFFFFF",
        "grid": "#D9E1EC",
        "spine": "#D9E1EC",
        "tick": "#657084",
        "label": "#293247",
        "title": "#172033",
        "grid_linewidth": 0.62,
        "grid_alpha": 0.32,
        "axisbelow": True,
        "spine_linewidth": 0.65,
        "tick_label_size": 9,
        "tick_direction": "out",
        "tick_length": 3.0,
        "tick_width": 0.65,
        "label_size": 10,
        "label_pad": 7,
        "title_size": 11,
        "title_weight": "bold",
        "title_pad": 10,
        "zero_line_color": "#A9B4C3",
        "zero_line_alpha": 0.55,
        "zero_line_width": 0.8,
        "zero_line_style": "-",
    }


def test_signal_reference_lines_are_limited_to_ecg_and_respiration_axes() -> None:
    from ads1292_studio.gui_plots import build_live_plot_panel, build_review_plot_panel

    source = inspect.getsource(build_live_plot_panel) + inspect.getsource(build_review_plot_panel)

    assert "add_signal_reference_lines((app.ax_live_ecg, app.ax_live_resp))" in source
    assert "add_signal_reference_lines((app.ax_review_ecg, app.ax_review_resp))" in source
    assert "app.ax_live_status" not in source.split("add_signal_reference_lines")[1].split(")")[0]
    assert "app.ax_review_status" not in source.split("add_signal_reference_lines")[2].split(")")[0]


def test_status_axis_uses_integer_lead_off_bit_scale() -> None:
    assert status_axis_spec() == {
        "y_major_tick_bits": 1.0,
        "ylabel": "lead-off bits",
    }


def test_live_and_review_status_axes_are_configured_as_status_tracks() -> None:
    from ads1292_studio.gui_plots import build_live_plot_panel, build_review_plot_panel, configure_status_axes

    source = inspect.getsource(build_live_plot_panel) + inspect.getsource(build_review_plot_panel)
    configure_source = inspect.getsource(configure_status_axes)

    assert "configure_status_axes((app.ax_live_status,))" in source
    assert "configure_status_axes((app.ax_review_status,))" in source
    assert "set_ylabel(str(spec[\"ylabel\"]))" in configure_source
    assert "MultipleLocator(float(spec[\"y_major_tick_bits\"]))" in configure_source


def test_live_and_review_ecg_axes_start_with_ecg_paper_grid() -> None:
    from ads1292_studio.gui_plots import build_live_plot_panel, build_review_plot_panel, configure_initial_ecg_paper_grid

    source = inspect.getsource(build_live_plot_panel) + inspect.getsource(build_review_plot_panel)
    configure_source = inspect.getsource(configure_initial_ecg_paper_grid)

    assert "configure_initial_ecg_paper_grid((app.ax_live_ecg,))" in source
    assert "configure_initial_ecg_paper_grid((app.ax_review_ecg,))" in source
    assert "ecg_paper_grid_spec(settings)" in configure_source
    assert "which=\"minor\"" in configure_source


def test_live_and_review_display_reuse_filter_settings_snapshot() -> None:
    from ads1292_studio.app import App

    source = inspect.getsource(App._redraw_live) + inspect.getsource(App._show_recording)

    assert "filter_settings = self._software_filter_settings()" in source
    assert "build_live_render_frame(" in source
    assert "build_review_render_frame(" in source
    assert "filter_settings=filter_settings" in source
    assert "filter_settings=self._software_filter_settings()" in source


def test_csv_loader_precomputes_review_render_frame_off_the_tk_thread() -> None:
    from ads1292_studio.app import App

    source = inspect.getsource(App._read_csv_in_background) + inspect.getsource(App._finish_csv_load)

    assert "review_frame = build_review_render_frame(" in source
    assert "review_frame=review_frame" in source
    assert "self._show_review_frame(result.recording.samples, result.review_frame)" in source


def test_loaded_csv_display_refresh_schedules_single_flight_review_render() -> None:
    from ads1292_studio.app import App

    source = inspect.getsource(App._refresh_display_plots) + inspect.getsource(App._schedule_review_render_update)

    assert "if self.loaded_samples:" in source
    assert "self._schedule_review_render_update(self.loaded_samples)" in source
    assert "self.review_render_future is not None and not self.review_render_future.done()" in source
    assert "self.pending_review_render_samples = samples" in source
    assert "self.review_render_generation += 1" in source
    assert "self.review_render_executor.submit(" in source
    assert "_show_recording(self.loaded_samples)" not in inspect.getsource(App._refresh_display_plots)


def test_review_render_results_reschedule_pending_latest_settings() -> None:
    from ads1292_studio.app import App

    source = inspect.getsource(App._drain_review_render_results) + inspect.getsource(App._schedule_pending_review_render)

    assert "if latest is None:" in source
    assert "self._schedule_pending_review_render()" in source
    assert "samples = self.pending_review_render_samples" in source
    assert "self._schedule_review_render_update(samples)" in source


def test_control_state_updates_skip_redundant_tk_writes() -> None:
    from ads1292_studio.app import App

    source = inspect.getsource(App._apply_control_states)

    assert "set_string_var_if_changed(" in source
    assert "configure_widget_option_if_changed(" in source
    assert "button.configure(state=" not in source
    assert "workflow_hint_var.set(" not in source
    assert "status_overview_var.set(" not in source


def test_tick_scheduler_uses_current_gui_state_for_adaptive_interval() -> None:
    from ads1292_studio.app import App

    source = inspect.getsource(App._schedule_tick)

    assert "gui_tick_interval_ms(self._current_gui_state())" in source
    assert "self._gui_state()" not in source


def test_plot_figure_layouts_keep_signal_panels_dense() -> None:
    assert plot_figure_layouts() == {
        "three_panel": {
            "left": 0.068,
            "right": 0.99,
            "top": 0.975,
            "bottom": 0.068,
            "hspace": 0.28,
        },
        "single_panel": {
            "left": 0.072,
            "right": 0.99,
            "top": 0.965,
            "bottom": 0.118,
        },
    }


def test_plot_figure_layouts_returns_nested_copies() -> None:
    layouts = plot_figure_layouts()
    layouts["three_panel"]["hspace"] = 9.0

    assert plot_figure_layouts()["three_panel"]["hspace"] == 0.28


def test_plot_canvas_widget_style_removes_embedded_canvas_chrome() -> None:
    assert plot_canvas_widget_style() == {
        "background": "#FFFFFF",
        "borderwidth": 0,
        "highlightthickness": 0,
    }
