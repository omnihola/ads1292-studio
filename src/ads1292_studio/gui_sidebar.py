from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from ads1292_studio.gui_scroll import ScrollableFrame
from ads1292_studio.gui_state import channel_map_cards
from ads1292_studio.gui_specs import (
    SIGNAL_CARD_LABELS,
    SIDEBAR_TABS,
    STATUS_CARD_LABELS,
    action_section_styles,
    card_label_spec,
    safety_notice_styles,
    sidebar_field_styles,
    sidebar_layout_spec,
    sidebar_notebook_styles,
    sidebar_tab_strip_styles,
    sidebar_text_card_spec,
    status_detail_styles,
    status_tone_color,
    status_tone_style,
    toolbar_hint_styles,
    toolbar_layout_spec,
    workflow_hint_styles,
)


def build_workflow_hint(app: Any, parent: ttk.Frame) -> None:
    styles = workflow_hint_styles()
    spec = sidebar_text_card_spec()
    app.workflow_hint_frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
    app.workflow_hint_frame.pack(anchor=tk.W, fill=tk.X, pady=(0, 4))
    app.workflow_hint_stripe = tk.Frame(
        app.workflow_hint_frame,
        width=spec["stripe_width"],
        bg=styles["stripe"],
        highlightthickness=0,
    )
    app.workflow_hint_stripe.pack(side=tk.LEFT, fill=tk.Y)
    app.workflow_hint_label = ttk.Label(
        app.workflow_hint_frame,
        textvariable=app.workflow_hint_var,
        wraplength=spec["primary_wrap"],
        justify=tk.LEFT,
        style=styles["label"],
        padding=spec["label_padding"],
    )
    app.workflow_hint_label.pack(side=tk.LEFT, fill=tk.X, expand=True)


def build_safety_notice(app: Any, parent: ttk.Frame) -> None:
    styles = safety_notice_styles()
    spec = sidebar_text_card_spec()
    app.safety_notice_frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
    app.safety_notice_frame.pack(anchor=tk.W, fill=tk.X, pady=(0, 4))
    app.safety_notice_stripe = tk.Frame(
        app.safety_notice_frame,
        width=spec["stripe_width"],
        bg=styles["stripe"],
        highlightthickness=0,
    )
    app.safety_notice_stripe.pack(side=tk.LEFT, fill=tk.Y)
    app.safety_notice_label = ttk.Label(
        app.safety_notice_frame,
        text="Research use only. Use battery power during human-subject measurements.",
        wraplength=spec["primary_wrap"],
        justify=tk.LEFT,
        style=styles["label"],
        padding=spec["label_padding"],
    )
    app.safety_notice_label.pack(side=tk.LEFT, fill=tk.X, expand=True)


def build_toolbar_hint_chip(app: Any, parent: ttk.Frame, variable: tk.StringVar) -> None:
    styles = toolbar_hint_styles()
    app.toolbar_hint_chip = ttk.Frame(
        parent,
        padding=toolbar_layout_spec()["hint_padding"],
        style=styles["frame"],
    )
    app.toolbar_hint_chip.pack(side=tk.LEFT)
    app.toolbar_hint_label = ttk.Label(app.toolbar_hint_chip, textvariable=variable, style=styles["label"])
    app.toolbar_hint_label.pack(side=tk.LEFT)


def build_action_section_heading(
    app: Any,
    parent: ttk.Frame,
    text: str,
    *,
    top_padding: int = 14,
) -> None:
    styles = action_section_styles()
    frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
    frame.pack(anchor=tk.W, fill=tk.X, pady=(top_padding, 4))
    label = ttk.Label(frame, text=text, style=styles["label"])
    label.pack(anchor=tk.W)
    app.action_section_labels[text] = label


def build_status_detail_card(app: Any, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
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
    app.status_detail_value_labels[label] = value_label


def build_event_count_card(app: Any, parent: ttk.Frame) -> None:
    from ads1292_studio.gui_specs import event_count_styles

    styles = event_count_styles()
    spec = sidebar_text_card_spec()
    row = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
    row.pack(anchor=tk.W, fill=tk.X, pady=(7, 2))
    stripe = tk.Frame(row, width=spec["stripe_width"], bg=styles["stripe"], highlightthickness=0)
    stripe.pack(side=tk.LEFT, fill=tk.Y)
    content = ttk.Frame(row, padding=spec["content_padding"], style=styles["frame"])
    content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Label(content, text="Event markers", style=styles["label"]).pack(anchor=tk.W)
    app.event_count_label = ttk.Label(
        content,
        textvariable=app.event_count_var,
        wraplength=spec["detail_wrap"],
        justify=tk.LEFT,
        style=styles["value"],
    )
    app.event_count_label.pack(anchor=tk.W, fill=tk.X, pady=spec["value_top_padding"])


def build_protocol_note_card(app: Any, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
    from ads1292_studio.gui_specs import protocol_note_styles

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
    app.protocol_note_labels[label] = value_label


def build_status_cards(app: Any, parent: ttk.Frame) -> None:
    card_label = card_label_spec()
    for label in STATUS_CARD_LABELS:
        stripe, content = _build_status_card_row(parent, tone="neutral", card_label=card_label)
        label_widget = ttk.Label(content, text=label, width=int(card_label["width"]), style=str(card_label["style"]))
        label_widget.pack(side=tk.LEFT)
        value_label = ttk.Label(
            content,
            textvariable=app.status_card_vars[label],
            style=status_tone_style("neutral"),
        )
        value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=card_label["value_padding"])
        app.status_card_label_widgets[label] = label_widget
        app.status_card_tone_stripes[label] = stripe
        app.status_card_value_labels[label] = value_label


def build_channel_map_cards(app: Any, parent: ttk.Frame) -> None:
    card_label = card_label_spec()
    for card in channel_map_cards():
        stripe, content = _build_status_card_row(parent, tone=card.tone, card_label=card_label)
        label_widget = ttk.Label(
            content,
            text=card.label,
            width=int(card_label["width"]),
            style=str(card_label["style"]),
        )
        label_widget.pack(side=tk.LEFT)
        value_label = ttk.Label(
            content,
            text=card.value,
            style=status_tone_style(card.tone),
            wraplength=card_label["signal_value_wrap"],
            justify=tk.LEFT,
        )
        value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=card_label["value_padding"])
        app.channel_map_label_widgets[card.label] = label_widget
        app.channel_map_tone_stripes[card.label] = stripe
        app.channel_map_value_labels[card.label] = value_label


def build_signal_quality_cards(app: Any, parent: ttk.Frame) -> None:
    card_label = card_label_spec()
    for label in SIGNAL_CARD_LABELS:
        stripe, content = _build_status_card_row(parent, tone="neutral", card_label=card_label)
        label_widget = ttk.Label(content, text=label, width=int(card_label["width"]), style=str(card_label["style"]))
        label_widget.pack(side=tk.LEFT)
        value_label = ttk.Label(
            content,
            textvariable=app.signal_card_vars[label],
            style=status_tone_style("neutral"),
            wraplength=card_label["signal_value_wrap"],
            justify=tk.LEFT,
        )
        value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=card_label["value_padding"])
        app.signal_card_label_widgets[label] = label_widget
        app.signal_card_tone_stripes[label] = stripe
        app.signal_card_value_labels[label] = value_label


def _build_status_card_row(
    parent: ttk.Frame,
    *,
    tone: str,
    card_label: dict[str, object],
) -> tuple[tk.Frame, ttk.Frame]:
    row = ttk.Frame(parent, padding=(0, 0), style="Card.TFrame")
    row.pack(anchor=tk.W, fill=tk.X, pady=card_label["row_padding"])
    stripe = tk.Frame(
        row,
        width=int(card_label["stripe_width"]),
        bg=status_tone_color(tone),
        highlightthickness=0,
    )
    stripe.pack(side=tk.LEFT, fill=tk.Y)
    content = ttk.Frame(row, padding=card_label["content_padding"], style="Card.TFrame")
    content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    return stripe, content


def build_sidebar(app: Any, parent: ttk.Frame) -> dict[str, ttk.Frame]:
    spec = sidebar_layout_spec()
    tab_strip_style = sidebar_tab_strip_styles()
    tab_strip = ttk.Frame(
        parent,
        padding=tab_strip_style["padding"],
        style=str(tab_strip_style["frame"]),
    )
    tab_strip.pack(fill=tk.X)
    app.sidebar_tab_strip = tab_strip
    app.sidebar_tab_labels = {}

    app.sidebar_notebook = ttk.Notebook(parent, style=sidebar_notebook_styles()["notebook"])
    app.sidebar_notebook.pack(fill=tk.BOTH, expand=True)
    app.sidebar_scrolls: dict[str, ScrollableFrame] = {}
    sections: dict[str, ttk.Frame] = {}
    for label in SIDEBAR_TABS:
        tab = ttk.Frame(app.sidebar_notebook)
        scroll = ScrollableFrame(tab, width=int(spec["scroll_width"]))
        scroll.frame.pack(fill=tk.BOTH, expand=True)
        app.sidebar_notebook.add(tab, text=label)
        tab_label = ttk.Label(
            tab_strip,
            text=label,
            style=str(tab_strip_style["tab"]),
            cursor="hand2",
        )
        tab_label.pack(side=tk.LEFT, padx=tab_strip_style["tab_gap"])
        tab_label.bind("<Button-1>", lambda _event, target=tab: _select_sidebar_tab(app, target))
        tab_label.bind("<Return>", lambda _event, target=tab: _select_sidebar_tab(app, target))
        tab_label.bind("<space>", lambda _event, target=tab: _select_sidebar_tab(app, target))
        app.sidebar_tab_labels[str(tab)] = tab_label
        app.sidebar_scrolls[label] = scroll
        sections[label] = scroll.content
    app.sidebar_notebook.bind("<<NotebookTabChanged>>", lambda _event: _sync_sidebar_tab_styles(app))
    _sync_sidebar_tab_styles(app)
    return sections


def _select_sidebar_tab(app: Any, target: ttk.Frame) -> str:
    app.sidebar_notebook.select(target)
    _sync_sidebar_tab_styles(app)
    return "break"


def _sync_sidebar_tab_styles(app: Any) -> None:
    tab_strip_style = sidebar_tab_strip_styles()
    selected = app.sidebar_notebook.select()
    for tab_id, label in app.sidebar_tab_labels.items():
        style = tab_strip_style["selected_tab"] if tab_id == selected else tab_strip_style["tab"]
        label.configure(style=str(style))


def metadata_entry(app: Any, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
    styles = sidebar_field_styles()
    ttk.Label(parent, text=label, style=styles["label"]).pack(anchor=tk.W, pady=(8, 2))
    ttk.Entry(parent, textvariable=variable, style=styles["entry"]).pack(anchor=tk.W, fill=tk.X)
