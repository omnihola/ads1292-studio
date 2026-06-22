"""SNR readout + event-annotation console (regrouped by intent)."""
from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

Callback = Callable[[], None]


def _group_head(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("GroupHead")
    return label


class EventConsole(QFrame):
    """Realtime SNR strip + Annotate / Manual range / Manage controls.

    Callbacks are injected so this widget stays free of acquisition logic.
    """

    def __init__(
        self,
        *,
        on_add_point: Callback,
        on_start_range: Callback,
        on_end_range: Callback,
        on_add_manual_range: Callback,
        on_remove_last: Callback,
        on_remove_by_number: Callback,
    ) -> None:
        super().__init__()
        self.setObjectName("Card")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- top strip: SNR + status ----
        top = QWidget()
        top_lay = QHBoxLayout(top)
        top_lay.setContentsMargins(14, 9, 14, 9)
        snr_title = _group_head("Realtime SNR")
        self.snr_value = QLabel("— · waiting for ECG window")
        self.snr_value.setObjectName("Muted")
        self.contact_value = QLabel("Contact —")
        self.contact_value.setObjectName("Muted")
        self.event_status = QLabel("Events 0 · Range start —")
        self.event_status.setObjectName("Muted")
        top_lay.addWidget(snr_title)
        top_lay.addWidget(self.snr_value)
        top_lay.addStretch(1)
        top_lay.addWidget(self.contact_value)
        top_lay.addWidget(self.event_status)
        root.addWidget(top)

        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(14, 10, 14, 12)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(7)

        # ---- (1) Annotate ----
        grid.addWidget(_group_head("① Annotate"), 0, 0)
        fields = QHBoxLayout()
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Event label, e.g. motion start")
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Event notes (optional)")
        fields.addWidget(self.label_edit)
        fields.addWidget(self.notes_edit)
        fwrap = QWidget()
        fwrap.setLayout(fields)
        grid.addWidget(fwrap, 1, 0)
        actions = QHBoxLayout()
        self.add_point_btn = QPushButton("＋ Add Point Event")
        self.add_point_btn.setObjectName("Primary")
        self.start_range_btn = QPushButton("▷ Start Range")
        self.end_range_btn = QPushButton("▣ End Range")
        for b in (self.add_point_btn, self.start_range_btn, self.end_range_btn):
            actions.addWidget(b)
        awrap = QWidget()
        awrap.setLayout(actions)
        grid.addWidget(awrap, 2, 0)

        # vertical divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("color:#DCE3EC;")
        grid.addWidget(divider, 0, 1, 3, 1)

        # ---- (2) Manual range + (3) Manage ----
        grid.addWidget(_group_head("② Manual range"), 0, 2)
        mrow = QHBoxLayout()
        self.manual_start_edit = QLineEdit()
        self.manual_start_edit.setPlaceholderText("start s")
        self.manual_start_edit.setFixedWidth(80)
        self.manual_end_edit = QLineEdit()
        self.manual_end_edit.setPlaceholderText("end s")
        self.manual_end_edit.setFixedWidth(80)
        self.add_manual_btn = QPushButton("＋ Add Manual Range")
        mrow.addWidget(QLabel("Range"))
        mrow.addWidget(self.manual_start_edit)
        mrow.addWidget(self.manual_end_edit)
        mrow.addWidget(self.add_manual_btn)
        mrow.addStretch(1)
        mwrap = QWidget()
        mwrap.setLayout(mrow)
        grid.addWidget(mwrap, 1, 2)

        grid.addWidget(_group_head("③ Manage"), 2, 2)
        gerow = QHBoxLayout()
        self.remove_last_btn = QPushButton("↶ Remove Last")
        self.remove_last_btn.setObjectName("Danger")
        self.remove_index_edit = QLineEdit()
        self.remove_index_edit.setPlaceholderText("#")
        self.remove_index_edit.setFixedWidth(56)
        self.remove_number_btn = QPushButton("✕ Remove Event #")
        self.remove_number_btn.setObjectName("Danger")
        gerow.addWidget(self.remove_last_btn)
        gerow.addWidget(QLabel("Remove #"))
        gerow.addWidget(self.remove_index_edit)
        gerow.addWidget(self.remove_number_btn)
        gerow.addStretch(1)
        gewrap = QWidget()
        gewrap.setLayout(gerow)
        grid.addWidget(gewrap, 3, 2)

        root.addWidget(body)

        self.add_point_btn.clicked.connect(on_add_point)
        self.start_range_btn.clicked.connect(on_start_range)
        self.end_range_btn.clicked.connect(on_end_range)
        self.add_manual_btn.clicked.connect(on_add_manual_range)
        self.remove_last_btn.clicked.connect(on_remove_last)
        self.remove_number_btn.clicked.connect(on_remove_by_number)

    def set_snr(self, text: str) -> None:
        self.snr_value.setText(text)

    def set_contact(self, electrodes_off: tuple[str, ...]) -> None:
        """Show which electrodes are off, or a green OK when fully connected."""
        from ads1292_studio.ui_qt.widgets import tone_color

        if electrodes_off:
            tone = "bad"
            text = "Lead-off: " + ", ".join(electrodes_off)
        else:
            tone = "ok"
            text = "Contact OK"
        self.contact_value.setText(text)
        self.contact_value.setStyleSheet(f"color: {tone_color(tone)}; font-weight: 600;")

    def set_event_status(self, count: int, range_start: float | None) -> None:
        start = f"{range_start:.1f} s" if range_start is not None else "—"
        self.event_status.setText(f"Events {count} · Range start {start}")
