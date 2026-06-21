"""Left column: Session / Validation / Protocol tabbed forms + archive actions.

MVP wires the Session tab fields and the Load CSV / archive buttons; Validation
and Protocol tab contents are filled in Phase 44.3.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def _group_head(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("GroupHead")
    return label


def _scroll(inner: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(inner)
    return area


class SidebarForms(QTabWidget):
    """Tabbed left panel. Action buttons are exposed for the window to wire."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedWidth(262)
        self.fields: dict[str, QLineEdit] = {}
        self.buttons: dict[str, QPushButton] = {}
        self.addTab(self._session_tab(), "Session")
        self.addTab(self._placeholder_tab("Validation thresholds — Phase 44.3"), "Validation")
        self.addTab(self._placeholder_tab("Protocol steps — Phase 44.3"), "Protocol")

    def _session_tab(self) -> QScrollArea:
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(14, 14, 14, 16)
        lay.setSpacing(4)

        lay.addWidget(_group_head("Recording notes"))
        defaults = {
            "Session ID": "untitled-session",
            "Subject": "anonymous",
            "Electrode": "commercial Ag/AgCl control",
            "Montage": "RA/LA/RL torso",
            "Operator": "",
            "Notes": "",
        }
        for label, default in defaults.items():
            cap = QLabel(label)
            cap.setObjectName("Muted")
            edit = QLineEdit(default)
            self.fields[label] = edit
            lay.addWidget(cap)
            lay.addWidget(edit)

        lay.addSpacing(6)
        lay.addWidget(_group_head("Open data"))
        self._add_button(lay, "Load CSV", primary=True)

        lay.addSpacing(6)
        lay.addWidget(_group_head("Optional archive"))
        for name in ("Export Report", "Export Package", "Verify Package", "Batch Compare", "Session Index"):
            self._add_button(lay, name)

        lay.addStretch(1)
        return _scroll(inner)

    def _add_button(self, layout: QVBoxLayout, name: str, *, primary: bool = False) -> None:
        btn = QPushButton(name)
        if primary:
            btn.setObjectName("Primary")
        self.buttons[name] = btn
        layout.addWidget(btn)

    def metadata(self):
        """Build a SessionMetadata from the Session-tab fields."""
        from ads1292_studio.metadata import SessionMetadata

        def g(key: str) -> str:
            return self.fields[key].text().strip()

        return SessionMetadata(
            session_id=g("Session ID"),
            subject_id=g("Subject") or "anonymous",
            electrode=g("Electrode"),
            montage=g("Montage") or "RA/LA/RL torso",
            operator=g("Operator"),
            notes=g("Notes"),
        )

    def _placeholder_tab(self, message: str) -> QScrollArea:
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(14, 14, 14, 16)
        note = QLabel(message)
        note.setObjectName("Faint")
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addStretch(1)
        return _scroll(inner)
