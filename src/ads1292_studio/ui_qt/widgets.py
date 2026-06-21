"""Small reusable Qt widgets/atoms used across the front-end."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ads1292_studio.ui_qt.tokens import design_tokens

_TOKENS = design_tokens()
_TONE_COLORS = {
    "ok": _TOKENS["ok"],
    "running": _TOKENS["accent"],
    "warning": _TOKENS["warn"],
    "bad": _TOKENS["bad"],
    "neutral": _TOKENS["ink_faint"],
}


def card(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    """Return an elevated card frame and the layout to add content into."""
    frame = QFrame()
    frame.setObjectName("Card")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(13, 11, 13, 12)
    outer.setSpacing(6)
    if title is not None:
        head = QLabel(title.upper())
        head.setObjectName("CardHead")
        outer.addWidget(head)
    return frame, outer


def status_row(key: str, value: str, tone: str = "neutral") -> tuple[QWidget, QLabel]:
    """A single key/value row with a leading tone dot. Returns (row, value_label)."""
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 3, 0, 3)
    lay.setSpacing(7)
    dot = QLabel("●")
    dot.setStyleSheet(f"color: {_TONE_COLORS.get(tone, _TOKENS['ink_faint'])};")
    k = QLabel(key)
    k.setObjectName("Muted")
    v = QLabel(value)
    v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    v.setStyleSheet("font-weight: 600;")
    lay.addWidget(dot)
    lay.addWidget(k)
    lay.addStretch(1)
    lay.addWidget(v)
    return row, v


def tone_color(tone: str) -> str:
    """Resolve a gui_state tone name to a hex color."""
    return str(_TONE_COLORS.get(tone, _TOKENS["ink_faint"]))


def pill(text: str, tone: str = "neutral") -> QLabel:
    """A rounded status pill (e.g. connection state)."""
    color = tone_color(tone)
    label = QLabel(text)
    label.setStyleSheet(
        f"color: {color}; font-weight: 600; padding: 4px 12px;"
        f" border: 1px solid {color}; border-radius: 11px;"
    )
    return label
