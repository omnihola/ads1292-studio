from __future__ import annotations

from tkinter import ttk

from ads1292_studio.gui_specs import (
    action_section_styles,
    base_checkbutton_style,
    base_chrome_spec,
    base_notebook_styles,
    button_chrome_spec,
    card_label_spec,
    event_count_styles,
    header_connection_styles,
    header_frame_spec,
    header_text_styles,
    input_chrome_spec,
    muted_label_spec,
    panel_chrome_spec,
    plot_panel_chrome_spec,
    protocol_note_styles,
    safety_notice_styles,
    scrollbar_chrome_spec,
    section_heading_styles,
    sidebar_notebook_styles,
    sidebar_tab_strip_styles,
    status_detail_styles,
    status_label_spec,
    toolbar_control_styles,
    toolbar_frame_spec,
    toolbar_group_label_spec,
    toolbar_hint_styles,
    toolbar_label_spec,
    workflow_hint_styles,
    workspace_notebook_styles,
    workspace_tab_strip_styles,
)


def configure_base_chrome(style: ttk.Style) -> None:
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
    style.configure(str(base_chrome["sidebar"]), background=base_chrome["background"])
    style.configure(str(base_chrome["main"]), background=base_chrome["background"])
    style.configure(
        str(base_chrome["label"]),
        background=base_chrome["background"],
        foreground=base_chrome["foreground"],
        borderwidth=base_chrome["borderwidth"],
    )


def configure_header_chrome(style: ttk.Style) -> None:
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
    for tone, style_name in (
        ("running", "Connection.TLabel"),
        ("ready", "Ready.Connection.TLabel"),
        ("running", "Running.Connection.TLabel"),
        ("warning", "Warning.Connection.TLabel"),
        ("neutral", "Neutral.Connection.TLabel"),
    ):
        style.configure(
            style_name,
            background=connection_backgrounds[tone],
            foreground=connection_foregrounds[tone],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )


def configure_toolbar_chrome(style: ttk.Style) -> None:
    toolbar_frame = toolbar_frame_spec()
    style.configure(
        str(toolbar_frame["frame"]),
        background=toolbar_frame["background"],
        borderwidth=toolbar_frame["borderwidth"],
        relief=toolbar_frame["relief"],
    )
    style.configure(str(toolbar_frame["separator"]), background=toolbar_frame["separator_background"])

    toolbar_label = toolbar_label_spec()
    style.configure(
        str(toolbar_label["style"]),
        background=toolbar_label["background"],
        foreground=toolbar_label["foreground"],
        font=toolbar_label["font"],
    )

    toolbar_group_label = toolbar_group_label_spec()
    style.configure(
        str(toolbar_group_label["style"]),
        background=toolbar_group_label["background"],
        foreground=toolbar_group_label["foreground"],
        font=toolbar_group_label["font"],
        padding=toolbar_group_label["padding"],
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
        bordercolor=combobox_chrome["border"],
        lightcolor=combobox_chrome["border"],
        darkcolor=combobox_chrome["border"],
        selectbackground=combobox_chrome["selectbackground"],
        selectforeground=combobox_chrome["selectforeground"],
        arrowcolor=combobox_chrome["arrowcolor"],
        padding=combobox_chrome["padding"],
        borderwidth=combobox_chrome["borderwidth"],
        relief=combobox_chrome["relief"],
        arrowsize=combobox_chrome["arrowsize"],
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
        bordercolor=[("focus", combobox_chrome["focus_border"]), ("active", combobox_chrome["focus_border"])],
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
    style.configure(
        toolbar_control_styles()["toggle_chip"],
        background=toolbar_toggle["background"],
        foreground=toolbar_toggle["foreground"],
        font=toolbar_toggle["font"],
        padding=toolbar_toggle["padding"],
        borderwidth=1,
        relief="flat",
        bordercolor=toolbar_toggle["border"],
        lightcolor=toolbar_toggle["border"],
        darkcolor=toolbar_toggle["border"],
    )
    style.configure(
        toolbar_control_styles()["selected_toggle_chip"],
        background=toolbar_toggle["selected_background"],
        foreground=toolbar_toggle["selected_foreground"],
        font=toolbar_toggle["font"],
        padding=toolbar_toggle["padding"],
        borderwidth=1,
        relief="flat",
        bordercolor=toolbar_toggle["selected_border"],
        lightcolor=toolbar_toggle["selected_border"],
        darkcolor=toolbar_toggle["selected_border"],
    )
    style.map(
        toolbar_control_styles()["toggle_chip"],
        background=[("active", toolbar_toggle["active_background"])],
        foreground=[("active", toolbar_toggle["active_foreground"])],
    )


def configure_form_chrome(style: ttk.Style) -> None:
    input_chrome = input_chrome_spec()
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


def configure_panel_chrome(style: ttk.Style) -> None:
    panel_chrome = panel_chrome_spec()
    for panel_style in (
        "Card.TFrame",
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
    plot_panel_chrome = plot_panel_chrome_spec()
    style.configure(
        "PlotPanel.TFrame",
        background=plot_panel_chrome["background"],
        borderwidth=plot_panel_chrome["borderwidth"],
        relief=plot_panel_chrome["relief"],
        bordercolor=plot_panel_chrome["border"],
        lightcolor=plot_panel_chrome["border"],
        darkcolor=plot_panel_chrome["border"],
    )
    for notice_style in (workflow_hint_styles(), safety_notice_styles()):
        style.configure(
            notice_style["frame"],
            background=notice_style["background"],
            borderwidth=panel_chrome["borderwidth"],
            relief=panel_chrome["relief"],
            bordercolor=panel_chrome["border"],
            lightcolor=panel_chrome["border"],
            darkcolor=panel_chrome["border"],
        )


def configure_scrollbar_chrome(style: ttk.Style) -> None:
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


def configure_sidebar_card_chrome(style: ttk.Style) -> None:
    card_label = card_label_spec()
    style.configure(
        str(card_label["style"]),
        background=card_label["background"],
        foreground=card_label["foreground"],
        font=card_label["font"],
    )

    workflow_hint = workflow_hint_styles()
    style.configure(
        workflow_hint["label"],
        background=workflow_hint["background"],
        foreground=workflow_hint["foreground"],
        font=workflow_hint["font"],
    )

    safety_notice = safety_notice_styles()
    style.configure(
        safety_notice["label"],
        background=safety_notice["background"],
        foreground=safety_notice["foreground"],
        font=safety_notice["font"],
    )

    _configure_label_value_pair(style, status_detail_styles())
    _configure_label_value_pair(style, event_count_styles())
    _configure_label_value_pair(style, protocol_note_styles())


def _configure_label_value_pair(style: ttk.Style, chrome: dict[str, object]) -> None:
    style.configure(
        chrome["label"],
        background=chrome["background"],
        foreground=chrome["label_foreground"],
        font=chrome["label_font"],
    )
    style.configure(
        chrome["value"],
        background=chrome["background"],
        foreground=chrome["value_foreground"],
        font=chrome["value_font"],
    )


def configure_button_chrome(style: ttk.Style) -> None:
    button_chrome = button_chrome_spec()
    _configure_button_style(style, "TButton", button_chrome["default"])
    _configure_button_style(style, "SidebarAction.TButton", button_chrome["sidebar"])
    _configure_button_style(style, "Primary.TButton", button_chrome["primary"])
    _configure_button_style(style, "Stop.TButton", button_chrome["stop"])


def _configure_button_style(style: ttk.Style, style_name: str, chrome: dict[str, object]) -> None:
    style.configure(
        style_name,
        padding=chrome["padding"],
        font=chrome["font"],
        foreground=chrome["foreground"],
        background=chrome["background"],
        borderwidth=chrome["borderwidth"],
        relief=chrome["relief"],
    )
    style.map(
        style_name,
        foreground=[
            ("disabled", chrome["disabled_foreground"]),
            ("active", chrome["active_foreground"]),
        ],
        background=[
            ("disabled", chrome["disabled_background"]),
            ("active", chrome["active_background"]),
        ],
    )


def configure_status_chrome(style: ttk.Style) -> None:
    status_label = status_label_spec()
    status_backgrounds = status_label["backgrounds"]
    status_foregrounds = status_label["foregrounds"]
    for tone, style_name in (
        ("ready", "Ready.Status.TLabel"),
        ("running", "Running.Status.TLabel"),
        ("warning", "Warning.Status.TLabel"),
        ("neutral", "Neutral.Status.TLabel"),
    ):
        style.configure(
            style_name,
            background=status_backgrounds[tone],
            foreground=status_foregrounds[tone],
            font=status_label["font"],
            padding=status_label["padding"],
        )


def configure_notebook_chrome(style: ttk.Style) -> None:
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
        borderwidth=base_notebook["tab_borderwidth"],
        relief=base_notebook["tab_relief"],
    )

    _configure_named_notebook(style, "Sidebar.TNotebook", "Sidebar.TNotebook.Tab", sidebar_notebook_styles())
    _configure_named_notebook(style, "Workspace.TNotebook", "Workspace.TNotebook.Tab", workspace_notebook_styles())
    _configure_tab_strip(style, sidebar_tab_strip_styles())
    _configure_tab_strip(style, workspace_tab_strip_styles())
    style.layout("Sidebar.TNotebook.Tab", [])
    style.layout("Workspace.TNotebook.Tab", [])


def _configure_named_notebook(
    style: ttk.Style,
    notebook_style: str,
    tab_style: str,
    chrome: dict[str, object],
) -> None:
    style.configure(
        notebook_style,
        background=chrome["background"],
        borderwidth=chrome["borderwidth"],
    )
    style.configure(
        tab_style,
        padding=chrome["tab_padding"],
        font=chrome["tab_font"],
        foreground=chrome["inactive_foreground"],
        background=chrome["tab_background"],
        borderwidth=chrome["tab_borderwidth"],
        relief=chrome["tab_relief"],
    )
    style.map(
        tab_style,
        foreground=[
            ("selected", chrome["selected_foreground"]),
            ("active", chrome["active_foreground"]),
        ],
        background=[
            ("selected", chrome["active_background"]),
            ("active", chrome["active_background"]),
        ],
    )


def _configure_tab_strip(style: ttk.Style, chrome: dict[str, object]) -> None:
    style.configure(
        chrome["frame"],
        background=chrome["background"],
        borderwidth=0,
    )
    style.configure(
        chrome["tab"],
        background=chrome["background"],
        foreground=chrome["foreground"],
        font=chrome["font"],
        padding=chrome["tab_padding"],
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        chrome["selected_tab"],
        background=chrome["selected_background"],
        foreground=chrome["selected_foreground"],
        font=chrome["font"],
        padding=chrome["tab_padding"],
        borderwidth=0,
        relief="flat",
    )
    style.map(
        chrome["tab"],
        background=[("active", chrome["hover_background"])],
        foreground=[("active", chrome["selected_foreground"])],
    )
