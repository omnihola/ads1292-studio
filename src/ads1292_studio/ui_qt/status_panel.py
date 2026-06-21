"""Right column: Status (Next step / Overview / Channel map / Signal quality / Session).

Driven by the reused ``gui_state`` view-model so it never drifts from the
control gating.
"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ads1292_studio.gui_state import (
    GuiState,
    channel_map_cards,
    gui_status_cards,
    gui_workflow_hint,
)
from ads1292_studio.ui_qt.tokens import design_tokens
from ads1292_studio.ui_qt.widgets import card, status_row

_T = design_tokens()
# gui_state tones -> widget tones
_TONE_MAP = {"ready": "ok", "running": "running", "warning": "warning", "neutral": "neutral", "bad": "bad"}


def _dot_color(tone: str) -> str:
    from ads1292_studio.ui_qt.widgets import tone_color
    return tone_color(_TONE_MAP.get(tone, "neutral"))


class StatusPanel(QScrollArea):
    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setFixedWidth(272)
        inner = QWidget()
        root = QVBoxLayout(inner)
        root.setContentsMargins(14, 12, 14, 16)
        root.setSpacing(13)

        head = QLabel("Status")
        head.setStyleSheet("font-weight:700; font-size:13px;")
        root.addWidget(head)

        # Next step (highlighted)
        ns_frame, ns_lay = card("Next step")
        ns_frame.setStyleSheet(
            f"#Card {{ background: {_T['accent_soft']}; border: 1px solid {_T['accent']}; }}"
        )
        self.next_step = QLabel("Select a port, press Connect, or load CSV.")
        self.next_step.setWordWrap(True)
        self.next_step.setStyleSheet(f"color: {_T['accent_press']}; font-weight:600;")
        ns_lay.addWidget(self.next_step)
        root.addWidget(ns_frame)

        # Overview rows
        ov_frame, ov_lay = card("Overview")
        self._overview: dict[str, tuple[QLabel, QLabel]] = {}
        for label in ("Connection", "Port", "Acquisition", "Data", "Package"):
            row, value = status_row(label, "—", "neutral")
            dot = row.layout().itemAt(0).widget()
            ov_lay.addWidget(row)
            self._overview[label] = (value, dot)
        root.addWidget(ov_frame)

        # Channel map (static)
        cm_frame, cm_lay = card("Channel map")
        for c in channel_map_cards():
            row, _ = status_row(c.label, c.value, _TONE_MAP.get(c.tone, "neutral"))
            cm_lay.addWidget(row)
        root.addWidget(cm_frame)

        # Signal quality (placeholders for MVP; populated in a later phase)
        sq_frame, sq_lay = card("Signal quality")
        self._quality: dict[str, QLabel] = {}
        for label in ("Signal", "Contact", "Heart rate", "Artifacts"):
            row, value = status_row(label, "—", "neutral")
            sq_lay.addWidget(row)
            self._quality[label] = value
        root.addWidget(sq_frame)

        # Session
        se_frame, se_lay = card("Session")
        self.session_value = QLabel("No session")
        self.session_value.setObjectName("Muted")
        se_lay.addWidget(self.session_value)
        root.addWidget(se_frame)

        root.addStretch(1)
        self.setWidget(inner)

    def update_from_state(self, state: GuiState) -> None:
        """Refresh next-step hint and overview rows from a GuiState snapshot."""
        self.next_step.setText(gui_workflow_hint(state=state))
        cards = gui_status_cards(state=state)
        for c in cards:
            handle = self._overview.get(c.label)
            if handle is None:
                continue
            value, dot = handle
            value.setText(c.value)
            dot.setStyleSheet(f"color: {_dot_color(c.tone)};")

    def set_quality(self, label: str, value: str) -> None:
        if label in self._quality:
            self._quality[label].setText(value)
