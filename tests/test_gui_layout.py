from ads1292_studio.app import (
    ads1292r_plot_layout_labels,
    app_visual_tokens,
    empty_plot_messages,
    empty_plot_style,
    log_panel_spec,
    main_tab_labels,
    plot_panel_spec,
    plot_trace_colors,
    primary_toolbar_button_labels,
    safety_notice_styles,
    secondary_action_button_labels,
    sidebar_action_button_style,
    sidebar_field_styles,
    sidebar_notebook_styles,
    sidebar_tab_labels,
    toolbar_button_style,
    toolbar_control_styles,
    toolbar_group_padding,
    workflow_hint_styles,
    workspace_notebook_styles,
)


def test_gui_layout_keeps_primary_toolbar_focused_on_acquisition() -> None:
    assert primary_toolbar_button_labels() == ("Refresh", "Connect", "Start", "Stop")
    assert "Load CSV" not in primary_toolbar_button_labels()
    assert "Export Report" not in primary_toolbar_button_labels()
    assert "Session Index" not in primary_toolbar_button_labels()


def test_gui_layout_assigns_toolbar_action_hierarchy() -> None:
    assert toolbar_button_style("Refresh") == "TButton"
    assert toolbar_button_style("Connect") == "Primary.TButton"
    assert toolbar_button_style("Start") == "Primary.TButton"
    assert toolbar_button_style("Stop") == "Stop.TButton"
    assert toolbar_button_style("Unknown") == "TButton"


def test_gui_layout_styles_toolbar_inputs_and_toggles() -> None:
    assert toolbar_control_styles() == {
        "port": "Port.TCombobox",
        "toggle": "ToolbarToggle.TCheckbutton",
    }


def test_gui_layout_spaces_toolbar_groups() -> None:
    assert toolbar_group_padding() == {
        "separator": (12, 8),
        "tight": (4, 4),
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
        "selected_foreground": "#2F6FED",
        "inactive_foreground": "#657084",
    }


def test_gui_layout_names_main_workspaces_clearly() -> None:
    assert main_tab_labels() == ("Live ECG", "Review CSV", "PQRST Beat", "Event Log")


def test_workspace_notebook_styles_make_selected_tabs_visible() -> None:
    assert workspace_notebook_styles() == {
        "notebook": "Workspace.TNotebook",
        "tab": "Workspace.TNotebook.Tab",
        "selected_foreground": "#2F6FED",
        "inactive_foreground": "#657084",
    }


def test_sidebar_field_styles_make_forms_consistent() -> None:
    assert sidebar_field_styles() == {
        "label": "FieldLabel.TLabel",
        "entry": "Field.TEntry",
    }


def test_sidebar_action_button_style_keeps_secondary_actions_consistent() -> None:
    assert sidebar_action_button_style() == "SidebarAction.TButton"


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
        "text_color": "#657084",
        "box_face": "#EEF3FA",
        "box_edge": "#D9E1EC",
        "font_size": 11,
        "alpha": 0.92,
    }


def test_log_panel_spec_keeps_long_sessions_readable() -> None:
    spec = log_panel_spec()

    assert spec["wrap"] == "word"
    assert spec["scrollbar"] == "vertical"
    assert spec["font"] == "Aptos 12"


def test_plot_panel_spec_frames_signal_workspaces() -> None:
    assert plot_panel_spec() == {
        "shell": "Main.TFrame",
        "panel": "Card.TFrame",
        "padding": (12, 12),
    }
