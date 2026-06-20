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
    plot_panel_chrome_spec,
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
    sidebar_tab_labels,
    sidebar_tab_strip_styles,
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
    workspace_tab_strip_styles,
)
from ads1292_studio.plot_theme import new_export_figure, style_export_axes


def test_gui_layout_keeps_primary_toolbar_focused_on_acquisition() -> None:
    assert primary_toolbar_button_labels() == ("Refresh", "Connect", "Start", "Stop")
    assert "Load CSV" not in primary_toolbar_button_labels()
    assert "Export Report" not in primary_toolbar_button_labels()
    assert "Session Index" not in primary_toolbar_button_labels()


def test_app_window_spec_prevents_cramped_signal_views() -> None:
    assert app_window_spec() == {
        "geometry": "1440x900",
        "min_size": (1180, 760),
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
        "toggle_chip": "ToolbarToggleChip.TLabel",
        "selected_toggle_chip": "Selected.ToolbarToggleChip.TLabel",
    }


def test_app_delegates_static_chrome_to_style_helpers() -> None:
    from ads1292_studio.app import App

    source = inspect.getsource(App._configure_status_styles)

    assert "configure_base_chrome(style)" in source
    assert "configure_header_chrome(style)" in source
    assert "configure_toolbar_chrome(style)" in source
    assert "configure_form_chrome(style)" in source
    assert "configure_panel_chrome(style)" in source
    assert "configure_scrollbar_chrome(style)" in source
    assert "configure_sidebar_card_chrome(style)" in source
    assert "configure_button_chrome(style)" in source
    assert "configure_notebook_chrome(style)" in source
    assert "configure_status_chrome(style)" in source


def test_plot_panel_chrome_is_configured_separately_from_cards() -> None:
    from ads1292_studio.gui_style import configure_panel_chrome

    source = inspect.getsource(configure_panel_chrome)
    card_loop = source.split("for panel_style in (", maxsplit=1)[1].split("):", maxsplit=1)[0]

    assert "\"PlotPanel.TFrame\"" not in card_loop
    assert "plot_panel_chrome_spec()" in source
    assert "style.configure(\n        \"PlotPanel.TFrame\"" in source


def test_toolbar_frame_spec_groups_acquisition_controls_as_one_surface() -> None:
    assert toolbar_frame_spec() == {
        "frame": "Toolbar.TFrame",
        "separator": "ToolbarSeparator.TFrame",
        "background": "#F8FAFD",
        "separator_background": "#E5EAF2",
        "borderwidth": 0,
        "relief": "flat",
    }


def test_toolbar_label_spec_keeps_toolbar_labels_consistent() -> None:
    assert toolbar_label_spec() == {
        "style": "ToolbarLabel.TLabel",
        "font": ("Aptos", 11, "bold"),
        "background": "#F8FAFD",
        "foreground": "#172033",
    }


def test_toolbar_group_label_spec_adds_scanable_control_groups() -> None:
    assert toolbar_group_label_spec() == {
        "style": "ToolbarGroupLabel.TLabel",
        "font": ("Aptos", 9, "bold"),
        "background": "#F8FAFD",
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
            "padding": (5, 3),
            "font": ("Aptos", 10, "bold"),
            "background": "#FFFFFF",
            "foreground": "#293247",
            "selected_background": "#2F6FED",
            "selected_foreground": "#FFFFFF",
            "border": "#D9E1EC",
            "selected_border": "#2F6FED",
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
    from ads1292_studio.gui_sidebar import build_toolbar_hint_chip

    source = inspect.getsource(build_toolbar_hint_chip)

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


def test_primary_toolbar_buttons_use_stable_widths() -> None:
    from ads1292_studio.gui_layout import build_acquisition_toolbar

    source = inspect.getsource(build_acquisition_toolbar)

    assert source.count('width=int(toolbar_spec["button_width"])') == 4


def test_display_toolbar_uses_compact_toggle_chips() -> None:
    from ads1292_studio.gui_layout import _build_toolbar_toggle_chip, build_display_toolbar

    source = inspect.getsource(build_display_toolbar)
    helper_source = inspect.getsource(_build_toolbar_toggle_chip)

    assert source.count("_build_toolbar_toggle_chip(") == 5
    assert "ttk.Checkbutton(\n        toolbar" not in source
    assert "variable.trace_add(\"write\", sync_style)" in helper_source
    assert "label.bind(\"<Button-1>\", toggle)" in helper_source
    assert "label.bind(\"<Return>\", toggle)" in helper_source
    assert "label.bind(\"<space>\", toggle)" in helper_source


def test_toolbar_toggle_chip_styles_are_configured() -> None:
    from ads1292_studio.gui_style import configure_toolbar_chrome

    source = inspect.getsource(configure_toolbar_chrome)

    assert "toolbar_control_styles()[\"toggle_chip\"]" in source
    assert "toolbar_control_styles()[\"selected_toggle_chip\"]" in source
    assert "selected_background" in source
    assert "selected_border" in source


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


def test_sidebar_tab_strip_styles_replace_native_tab_chrome() -> None:
    assert sidebar_tab_strip_styles() == {
        "frame": "SidebarTabStrip.TFrame",
        "tab": "SidebarTab.TLabel",
        "selected_tab": "Selected.SidebarTab.TLabel",
        "background": "#F6F8FB",
        "selected_background": "#EAF1FF",
        "hover_background": "#EAF1FF",
        "foreground": "#657084",
        "selected_foreground": "#2F6FED",
        "font": ("Aptos", 10, "bold"),
        "padding": (0, 0, 0, 5),
        "tab_padding": (7, 6),
        "tab_gap": (0, 2),
    }


def test_sidebar_uses_custom_segmented_tab_strip() -> None:
    from ads1292_studio.gui_sidebar import build_sidebar

    source = inspect.getsource(build_sidebar)

    assert "app.sidebar_tab_strip" in source
    assert "app.sidebar_tab_labels" in source
    assert "app.sidebar_stack" in source
    assert "_select_sidebar_tab(app, target)" in source
    assert "ttk.Notebook" not in source
    assert "<<NotebookTabChanged>>" not in source


def test_sidebar_tab_selection_uses_stacked_frames() -> None:
    from ads1292_studio.gui_sidebar import _select_sidebar_tab, _sync_sidebar_tab_styles

    select_source = inspect.getsource(_select_sidebar_tab)
    sync_source = inspect.getsource(_sync_sidebar_tab_styles)

    assert "tab.pack_forget()" in select_source
    assert "target.pack(fill=tk.BOTH, expand=True)" in select_source
    assert "app.selected_sidebar_tab = str(target)" in select_source
    assert "app.sidebar_notebook" not in select_source + sync_source


def test_sidebar_layout_spec_stabilizes_control_column() -> None:
    assert sidebar_layout_spec() == {
        "shell": "SidebarShell.TFrame",
        "width": 320,
        "padding": (8, 10),
        "scroll_width": 292,
    }


def test_gui_layout_names_main_workspaces_clearly() -> None:
    assert main_tab_labels() == ("Live ECG", "Review CSV", "PQRST Beat", "Event Log")


def test_workspace_layout_spec_balances_sidebar_and_signal_area() -> None:
    assert workspace_layout_spec() == {
        "main": "Main.TFrame",
        "main_padding": (8, 10, 14, 10),
    }


def test_body_shell_uses_fixed_sidebar_without_native_paned_sash() -> None:
    from ads1292_studio.gui_layout import build_body_shell

    source = inspect.getsource(build_body_shell)

    assert "ttk.PanedWindow" not in source
    assert "app.body_shell" in source
    assert "side_shell.pack(side=tk.LEFT, fill=tk.Y)" in source
    assert "side_shell.pack_propagate(False)" in source
    assert "main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)" in source


def test_header_connection_styles_make_status_a_pill() -> None:
    assert header_connection_styles() == {
        "styles": {
            "ready": "Ready.Connection.TLabel",
            "running": "Running.Connection.TLabel",
            "warning": "Warning.Connection.TLabel",
            "neutral": "Neutral.Connection.TLabel",
        },
        "padding": (10, 4),
        "font": ("Aptos", 11, "bold"),
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
        "padding": (18, 10, 18, 9),
        "subtitle_padding": (12, 0),
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


def test_workspace_tab_strip_styles_replace_native_tab_chrome() -> None:
    assert workspace_tab_strip_styles() == {
        "frame": "WorkspaceTabStrip.TFrame",
        "tab": "WorkspaceTab.TLabel",
        "selected_tab": "Selected.WorkspaceTab.TLabel",
        "background": "#F6F8FB",
        "selected_background": "#2F6FED",
        "hover_background": "#EAF1FF",
        "foreground": "#657084",
        "selected_foreground": "#FFFFFF",
        "font": ("Aptos", 12, "bold"),
        "padding": (4, 0, 4, 6),
        "tab_padding": (12, 7),
        "tab_gap": (0, 4),
    }


def test_workspace_tabs_use_custom_segmented_strip() -> None:
    from ads1292_studio.gui_layout import build_workspace_tabs

    source = inspect.getsource(build_workspace_tabs)

    assert "app.workspace_tab_strip" in source
    assert "app.workspace_tab_labels" in source
    assert "app.workspace_stack" in source
    assert "_select_workspace_tab(app, target)" in source
    assert "ttk.Notebook" not in source
    assert "<<NotebookTabChanged>>" not in source


def test_workspace_tab_selection_uses_stacked_frames() -> None:
    from ads1292_studio.gui_layout import _select_workspace_tab, _sync_workspace_tab_styles

    select_source = inspect.getsource(_select_workspace_tab)
    sync_source = inspect.getsource(_sync_workspace_tab_styles)

    assert "tab.pack_forget()" in select_source
    assert "target.pack(fill=tk.BOTH, expand=True)" in select_source
    assert "app.selected_workspace_tab = str(target)" in select_source
    assert "app.notebook" not in select_source + sync_source


def test_native_sidebar_and_workspace_notebook_styles_are_not_configured() -> None:
    from ads1292_studio.gui_style import configure_notebook_chrome

    source = inspect.getsource(configure_notebook_chrome)

    assert "Sidebar.TNotebook" not in source
    assert "Workspace.TNotebook" not in source
    assert "_configure_named_notebook" not in source


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
    assert "build_channel_map_cards(app, status_side)" in source
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


def test_empty_plot_state_uses_quiet_axes_until_data_arrives() -> None:
    from ads1292_studio.app import App
    from ads1292_studio.gui_plots import apply_live_render_frame, show_empty_plot_state

    empty_source = inspect.getsource(show_empty_plot_state)
    live_source = inspect.getsource(apply_live_render_frame)
    review_source = inspect.getsource(App._show_review_frame)

    assert "soften_empty_axis_chrome(axes)" in empty_source
    assert "restore_data_axis_chrome((app.ax_live_ecg" in live_source
    assert "restore_data_axis_chrome((self.ax_review_ecg" in review_source


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
        "border": "#E5EAF2",
        "borderwidth": 1,
        "relief": "flat",
    }


def test_plot_panel_chrome_spec_keeps_signal_workspace_unframed() -> None:
    assert plot_panel_chrome_spec() == {
        "background": "#FFFFFF",
        "border": "#FFFFFF",
        "borderwidth": 0,
        "relief": "flat",
    }


def test_plot_panel_spec_keeps_signal_workspace_tight() -> None:
    assert plot_panel_spec() == {
        "shell": "Main.TFrame",
        "panel": "PlotPanel.TFrame",
        "padding": (0, 4),
        "panel_padding": (0, 0),
    }


def test_plot_axis_style_keeps_signal_charts_quiet_and_readable() -> None:
    assert plot_axis_style() == {
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
    from ads1292_studio.gui_plots import (
        apply_ecg_paper_grid,
        build_live_plot_panel,
        build_review_plot_panel,
        configure_initial_ecg_paper_grid,
    )

    source = inspect.getsource(build_live_plot_panel) + inspect.getsource(build_review_plot_panel)
    configure_source = inspect.getsource(configure_initial_ecg_paper_grid)
    apply_source = inspect.getsource(apply_ecg_paper_grid)

    assert "configure_initial_ecg_paper_grid((app.ax_live_ecg,))" in source
    assert "configure_initial_ecg_paper_grid((app.ax_review_ecg,))" in source
    assert "apply_ecg_paper_grid(ax, settings" in configure_source
    assert "ecg_paper_grid_spec(settings)" in apply_source
    assert "which=\"minor\"" in apply_source


def test_live_and_review_runtime_grid_and_calibration_are_plot_helpers() -> None:
    from ads1292_studio.app import App
    from ads1292_studio.gui_plots import apply_live_render_frame

    live_source = inspect.getsource(apply_live_render_frame)
    review_source = inspect.getsource(App._show_review_frame)

    assert "apply_live_render_frame(" in inspect.getsource(App._redraw_live)
    assert "set_axis_xlim_if_changed(self.ax_review_ecg" in review_source
    assert "set_axis_xlim_if_changed(self.ax_review_resp" in review_source
    assert "set_axis_xlim_if_changed(self.ax_review_status" in review_source
    assert ".set_xlim(0, frame.x_right)" not in review_source
    assert "set_axis_ylim_if_changed(self.ax_review_ecg" in review_source
    assert "set_axis_ylim_if_changed(self.ax_review_resp" in review_source
    assert "set_axis_ylim_if_changed(self.ax_review_status" in review_source
    assert ".set_ylim(*frame." not in review_source
    assert "apply_ecg_paper_grid(app.ax_live_ecg" in live_source
    assert "apply_ecg_paper_grid(self.ax_review_ecg" in review_source
    assert "draw_calibration_pulse(" in live_source + review_source
    assert "def _apply_ecg_paper_grid" not in inspect.getsource(App)
    assert "def _draw_calibration_pulse" not in inspect.getsource(App)


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


def test_plot_figure_layouts_returns_nested_copies() -> None:
    layouts = plot_figure_layouts()
    layouts["three_panel"]["hspace"] = 9.0

    assert plot_figure_layouts()["three_panel"]["hspace"] == 0.18


def test_plot_canvas_widget_style_removes_embedded_canvas_chrome() -> None:
    assert plot_canvas_widget_style() == {
        "background": "#FFFFFF",
        "borderwidth": 0,
        "highlightthickness": 0,
    }
