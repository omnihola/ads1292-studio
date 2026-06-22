"""Left column: Session / Validation / Protocol tabbed forms + archive actions.

MVP wires the Session tab fields and the Load CSV / archive buttons; Validation
and Protocol tab contents are filled in Phase 44.3.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
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
        self.validation_fields: dict[str, QLineEdit] = {}
        self.protocol_fields: dict[str, QLineEdit] = {}
        self.addTab(self._session_tab(), "Session")
        self.addTab(self._validation_tab(), "Validation")
        self.addTab(self._protocol_tab(), "Protocol")

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
        lay.addWidget(_group_head("Export from .h5"))
        for name in ("Export XLSX", "Export JSON"):
            self._add_button(lay, name)

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

    # ---- Validation tab (QualityGate) ----
    def _validation_tab(self) -> QScrollArea:
        from ads1292_studio.quality_gate import QualityGate

        gate = QualityGate()
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(14, 14, 14, 16)
        lay.setSpacing(4)
        lay.addWidget(_group_head("Quality gate thresholds"))
        rows = [
            ("min_duration_seconds", "Min duration (s)", gate.min_duration_seconds),
            ("min_contact_ok_percent", "Min contact OK (%)", gate.min_contact_ok_percent),
            ("min_r_peaks", "Min R peaks", gate.min_r_peaks),
            ("min_hr_bpm", "Min HR (bpm)", gate.min_hr_bpm),
            ("max_hr_bpm", "Max HR (bpm)", gate.max_hr_bpm),
        ]
        for key, label, default in rows:
            cap = QLabel(label)
            cap.setObjectName("Muted")
            edit = QLineEdit(str(default))
            self.validation_fields[key] = edit
            lay.addWidget(cap)
            lay.addWidget(edit)
        self.validation_qrs_check = QCheckBox("Require clear QRS")
        self.validation_qrs_check.setChecked(gate.require_qrs_clear)
        lay.addSpacing(4)
        lay.addWidget(self.validation_qrs_check)
        lay.addSpacing(6)
        lay.addWidget(_group_head("Optional artifact limits (blank = off)"))
        for key, label in (
            ("max_baseline_drift_counts", "Max baseline drift (ct)"),
            ("max_noise_rms_counts", "Max noise RMS (ct)"),
            ("max_peak_to_peak_counts", "Max peak-to-peak (ct)"),
        ):
            cap = QLabel(label)
            cap.setObjectName("Muted")
            edit = QLineEdit("")
            self.validation_fields[key] = edit
            lay.addWidget(cap)
            lay.addWidget(edit)
        lay.addStretch(1)
        return _scroll(inner)

    def quality_gate(self):
        """Build a QualityGate from the Validation-tab fields."""
        from ads1292_studio.quality_gate import QualityGate

        def num(key: str, default: float) -> float:
            try:
                return float(self.validation_fields[key].text())
            except ValueError:
                return default

        def opt(key: str):
            text = self.validation_fields[key].text().strip()
            try:
                return float(text) if text else None
            except ValueError:
                return None

        return QualityGate(
            min_duration_seconds=num("min_duration_seconds", 8.0),
            min_contact_ok_percent=num("min_contact_ok_percent", 95.0),
            min_r_peaks=int(num("min_r_peaks", 5)),
            min_hr_bpm=num("min_hr_bpm", 35.0),
            max_hr_bpm=num("max_hr_bpm", 180.0),
            require_qrs_clear=self.validation_qrs_check.isChecked(),
            max_baseline_drift_counts=opt("max_baseline_drift_counts"),
            max_noise_rms_counts=opt("max_noise_rms_counts"),
            max_peak_to_peak_counts=opt("max_peak_to_peak_counts"),
        )

    # ---- Protocol tab (TestProtocol) ----
    def _protocol_tab(self) -> QScrollArea:
        from ads1292_studio.protocol import protocol_template

        base = protocol_template()
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(14, 14, 14, 16)
        lay.setSpacing(4)
        lay.addWidget(_group_head("Protocol"))
        for key, label, default in (
            ("name", "Name", base.name),
            ("objective", "Objective", base.objective),
            ("operator_instructions", "Operator instructions", base.operator_instructions),
            ("acceptance_notes", "Acceptance notes", base.acceptance_notes),
        ):
            cap = QLabel(label)
            cap.setObjectName("Muted")
            edit = QLineEdit(default)
            self.protocol_fields[key] = edit
            lay.addWidget(cap)
            lay.addWidget(edit)
        lay.addSpacing(6)
        lay.addWidget(_group_head("Steps (from template)"))
        for step in base.steps:
            row = QLabel(f"• {step.label}: {step.start_seconds:.0f}–{step.start_seconds + step.duration_seconds:.0f}s")
            row.setObjectName("Faint")
            row.setWordWrap(True)
            lay.addWidget(row)
        lay.addStretch(1)
        return _scroll(inner)

    def protocol(self):
        """Build a TestProtocol from the Protocol-tab fields (template steps preserved)."""
        from ads1292_studio.protocol import protocol_template, TestProtocol

        base = protocol_template()
        return TestProtocol(
            name=self.protocol_fields["name"].text() or base.name,
            objective=self.protocol_fields["objective"].text(),
            operator_instructions=self.protocol_fields["operator_instructions"].text() or base.operator_instructions,
            steps=base.steps,
            acceptance_notes=self.protocol_fields["acceptance_notes"].text() or base.acceptance_notes,
        ).normalized()

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
