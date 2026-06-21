"""ADS1292 Studio — PySide6 main window (Phase 44.1 MVP).

Assembles the 3-column layout and runs a QTimer tick that drains the
controller's queues, updates the live plot, and refreshes control gating and
the Status panel from the reused ``gui_state`` view-model.
"""
from __future__ import annotations

from collections import deque

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ads1292_studio.device import find_ads_port, list_ads_ports
from ads1292_studio.gui_state import gui_control_states
from ads1292_studio.ui_qt.controller import AcquisitionController
from ads1292_studio.ui_qt.event_console import EventConsole
from ads1292_studio.ui_qt.live_panel import LivePanel
from ads1292_studio.ui_qt.sidebar_forms import SidebarForms
from ads1292_studio.ui_qt.status_panel import StatusPanel
from ads1292_studio.ui_qt.tokens import design_tokens
from ads1292_studio.ui_qt.widgets import pill
from ads1292_studio.workers import AcquisitionMode

_T = design_tokens()
SAMPLE_RATE_HZ = 500.0
VISIBLE_SECONDS = 8.0
MAX_POINTS = int(SAMPLE_RATE_HZ * VISIBLE_SECONDS)
ACTIVE_TICK_MS = 50
IDLE_TICK_MS = 200


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ADS1292 Studio")
        self.resize(1400, 880)
        self.controller = AcquisitionController()
        self.controls: dict[str, QWidget] = {}
        self._ch1: deque[float] = deque(maxlen=MAX_POINTS)
        self._ch2: deque[float] = deque(maxlen=MAX_POINTS)
        self._sample_count = 0
        self._events: list[dict] = []
        self._range_start_s: float | None = None

        root = QWidget()
        root.setObjectName("CentralRoot")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())
        outer.addWidget(self._build_control_toolbar())
        outer.addWidget(self._build_display_toolbar())
        outer.addWidget(self._build_body(), 1)
        self.setCentralWidget(root)

        self._refresh_ports()
        self._refresh_state()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(IDLE_TICK_MS)

    # ---------- header ----------
    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Header")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(18, 12, 18, 12)
        title_box = QVBoxLayout()
        title = QLabel("ADS1292 Studio")
        title.setObjectName("Title")
        subtitle = QLabel("MOTAC ECG validation")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        lay.addLayout(title_box)
        lay.addStretch(1)
        self.connection_pill = pill("Not connected", "bad")
        lay.addWidget(self.connection_pill)
        return frame

    # ---------- control toolbar ----------
    def _build_control_toolbar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Toolbar")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(18, 10, 18, 10)
        lay.setSpacing(8)

        lay.addWidget(self._caps("Port"))
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setMinimumWidth(220)
        self.port_combo.currentTextChanged.connect(self._on_port_changed)
        self.controls["Port"] = self.port_combo
        lay.addWidget(self.port_combo)

        self._add_control(lay, "Refresh", self._refresh_ports)
        self._add_control(lay, "Connect", self._on_connect, object_name="Primary")
        self._add_control(lay, "Start", self._on_start, object_name="Go")
        self._add_control(lay, "Stop", self._on_stop)

        lay.addWidget(self._caps("Mode"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Live Monitor", "Raw Record"])
        self.controls["Mode"] = self.mode_combo
        lay.addWidget(self.mode_combo)

        self._add_control(lay, "Calibrate Live", self._on_calibrate)

        self.save_csv = QCheckBox("Record CSV")
        self.save_csv.setChecked(True)
        self.controls["Save CSV"] = self.save_csv
        lay.addWidget(self.save_csv)
        lay.addStretch(1)
        return frame

    # ---------- display toolbar ----------
    def _build_display_toolbar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("DisplayToolbar")
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(18, 8, 18, 8)
        lay.setSpacing(8)
        lay.addWidget(self._caps("Display"))
        auto = QPushButton("Auto scale")
        auto.setObjectName("Primary")
        auto.setCheckable(True)
        auto.setChecked(True)
        lay.addWidget(auto)
        for f in ("HP", "Notch", "LP", "QRS filter"):
            b = QPushButton(f)
            b.setCheckable(True)
            lay.addWidget(b)
        lay.addWidget(self._caps("Scale"))
        for label, items in (("Window", ["8 s"]), ("Gain", ["1x"]), ("Speed", ["25 mm/s"])):
            lay.addWidget(QLabel(label))
            combo = QComboBox()
            combo.addItems(items)
            lay.addWidget(combo)
        lay.addStretch(1)
        hint = QLabel("CH2 Lead I · CH1 Resp · Contact · raw · 1x · 8 s · 25 mm/s")
        hint.setObjectName("Faint")
        lay.addWidget(hint)
        return frame

    # ---------- body ----------
    def _build_body(self) -> QWidget:
        body = QWidget()
        lay = QHBoxLayout(body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.sidebar = SidebarForms()
        for name, btn in self.sidebar.buttons.items():
            self.controls[name] = btn
        lay.addWidget(self.sidebar)

        center = QWidget()
        clay = QVBoxLayout(center)
        clay.setContentsMargins(14, 14, 14, 14)
        clay.setSpacing(11)
        self.tabs = QTabWidget()
        live_tab = QWidget()
        live_lay = QVBoxLayout(live_tab)
        live_lay.setContentsMargins(0, 8, 0, 0)
        live_lay.setSpacing(10)
        self.live_panel = LivePanel()
        live_lay.addWidget(self.live_panel, 1)
        self.event_console = EventConsole(
            on_add_point=self._on_add_point,
            on_start_range=self._on_start_range,
            on_end_range=self._on_end_range,
            on_add_manual_range=self._on_add_manual_range,
            on_remove_last=self._on_remove_last,
            on_remove_by_number=self._on_remove_by_number,
        )
        live_lay.addWidget(self.event_console)
        self.tabs.addTab(live_tab, "Live ECG")
        for name in ("Review CSV", "PQRST Beat", "Spectrum", "Event Log"):
            placeholder = QLabel(f"{name} — Phase 44.2")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setObjectName("Faint")
            self.tabs.addTab(placeholder, name)
        clay.addWidget(self.tabs, 1)
        lay.addWidget(center, 1)

        self.status_panel = StatusPanel()
        lay.addWidget(self.status_panel)
        return body

    # ---------- small helpers ----------
    def _caps(self, text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("CardHead")
        return label

    def _add_control(self, layout, name: str, slot, *, object_name: str | None = None) -> None:
        btn = QPushButton(name)
        if object_name:
            btn.setObjectName(object_name)
        btn.clicked.connect(slot)
        self.controls[name] = btn
        layout.addWidget(btn)

    # ---------- actions ----------
    def _refresh_ports(self) -> None:
        ports = [p.device for p in list_ads_ports()]
        if not ports:
            guess = find_ads_port()
            ports = [guess] if guess else []
        current = self.port_combo.currentText()
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current:
            self.port_combo.setCurrentText(current)
        elif ports:
            self.port_combo.setCurrentText(ports[0])
        self.port_combo.blockSignals(False)
        self.controller.selected_port = self.port_combo.currentText()
        self._refresh_state()

    def _on_port_changed(self, text: str) -> None:
        self.controller.selected_port = text
        self._refresh_state()

    def _on_connect(self) -> None:
        self.controller.connect(self.port_combo.currentText().strip())
        self._refresh_state()

    def _on_start(self) -> None:
        mode = AcquisitionMode.RAW if self.mode_combo.currentText().lower().startswith("raw") else AcquisitionMode.LIVE
        self._ch1.clear()
        self._ch2.clear()
        self._sample_count = 0
        self.controller.start(self.port_combo.currentText().strip(), save_csv=self.save_csv.isChecked(), mode=mode)
        self._set_timer_active(True)
        self._refresh_state()

    def _on_stop(self) -> None:
        self.controller.stop()
        self._set_timer_active(False)
        self._refresh_state()

    def _on_calibrate(self) -> None:
        QMessageBox.information(self, "Calibrate Live", "Live calibration wiring lands in Phase 44.3.")

    # event console (MVP: in-memory; sidecar/overlay wiring is Phase 44.3)
    def _now_seconds(self) -> float:
        return self._sample_count / SAMPLE_RATE_HZ

    def _on_add_point(self) -> None:
        self._events.append({"label": self.event_console.label_edit.text(), "t": self._now_seconds(), "kind": "point"})
        self._refresh_events()

    def _on_start_range(self) -> None:
        self._range_start_s = self._now_seconds()
        self._refresh_events()

    def _on_end_range(self) -> None:
        if self._range_start_s is not None:
            self._events.append({"label": self.event_console.label_edit.text(), "start": self._range_start_s, "end": self._now_seconds(), "kind": "range"})
            self._range_start_s = None
        self._refresh_events()

    def _on_add_manual_range(self) -> None:
        try:
            start = float(self.event_console.manual_start_edit.text())
            end = float(self.event_console.manual_end_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Manual range", "Enter numeric start and end seconds.")
            return
        self._events.append({"label": self.event_console.label_edit.text(), "start": start, "end": end, "kind": "range"})
        self._refresh_events()

    def _on_remove_last(self) -> None:
        if self._events:
            self._events.pop()
        self._refresh_events()

    def _on_remove_by_number(self) -> None:
        try:
            idx = int(self.event_console.remove_index_edit.text()) - 1
        except ValueError:
            return
        if 0 <= idx < len(self._events):
            self._events.pop(idx)
        self._refresh_events()

    def _refresh_events(self) -> None:
        self.event_console.set_event_status(len(self._events), self._range_start_s)

    # ---------- tick ----------
    def _set_timer_active(self, active: bool) -> None:
        self._timer.start(ACTIVE_TICK_MS if active else IDLE_TICK_MS)

    def _tick(self) -> None:
        outcome = self.controller.drain_results()
        samples = self.controller.drain_samples()
        if samples:
            for s in samples:
                self._ch1.append(float(s.ch1))
                self._ch2.append(float(s.ch2))
            self._sample_count += len(samples)
            self._redraw_live()
        if outcome.state_changed or samples:
            self._refresh_state()
        if not self.controller.is_streaming and not samples:
            self._set_timer_active(False)
        for err in outcome.errors:
            QMessageBox.critical(self, "ADS1292 Studio", err)

    def _redraw_live(self) -> None:
        n = len(self._ch2)
        if n == 0:
            return
        start_index = self._sample_count - n
        xs = [(start_index + i) / SAMPLE_RATE_HZ for i in range(n)]
        self.live_panel.update_traces(xs, list(self._ch2), xs, list(self._ch1))

    # ---------- state refresh ----------
    def _refresh_state(self) -> None:
        state = self.controller.snapshot()
        states = gui_control_states(state=state)
        for name, widget in self.controls.items():
            if name in states:
                widget.setEnabled(states[name] != "disabled")
        # connection pill
        if state.streaming:
            self._set_pill("Streaming", "running")
        elif state.connected:
            self._set_pill(f"Connected · {state.selected_port}", "ok")
        elif state.connecting:
            self._set_pill("Connecting…", "warning")
        else:
            self._set_pill("Not connected", "bad")
        self.status_panel.update_from_state(state)

    def _set_pill(self, text: str, tone: str) -> None:
        from ads1292_studio.ui_qt.widgets import tone_color
        color = tone_color(tone)
        self.connection_pill.setText(text)
        self.connection_pill.setStyleSheet(
            f"color: {color}; font-weight: 600; padding: 4px 12px;"
            f" border: 1px solid {color}; border-radius: 11px;"
        )
