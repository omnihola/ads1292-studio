"""ADS1292 Studio — PySide6 main window (Phase 44.1 MVP).

Assembles the 3-column layout and runs a QTimer tick that drains the
controller's queues, updates the live plot, and refreshes control gating and
the Status panel from the reused ``gui_state`` view-model.
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
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
from ads1292_studio.events import EventMarker, event_from_interval
from ads1292_studio.lead_off import electrodes_off
from ads1292_studio.gui_state import gui_control_states, gui_signal_quality_cards
from ads1292_studio.quality import compute_quality_metrics, estimate_realtime_snr
from ads1292_studio.ui_qt.analysis_panels import EventLogPanel, PqrstPanel, RecordingInfoPanel, SpectrumPanel
from ads1292_studio.ui_qt.controller import AcquisitionController
from ads1292_studio.ui_qt.event_console import EventConsole
from ads1292_studio.ui_qt.live_panel import LivePanel
from ads1292_studio.ui_qt.sidebar_forms import SidebarForms
from ads1292_studio.ui_qt.status_panel import StatusPanel
from ads1292_studio.ui_qt.tokens import design_tokens
from ads1292_studio.ui_qt.widgets import pill
from ads1292_studio.display import (
    DISPLAY_WINDOW_CHOICES,
    EcgDisplaySettings,
    SoftwareFilterSettings,
    display_gain_labels,
    display_window_labels,
    parse_display_gain,
    parse_display_window,
    parse_sweep_speed,
    sweep_speed_labels,
)
from ads1292_studio.plots import decimate_extrema_for_plot
from ads1292_studio.signal_processing import apply_software_filters
from ads1292_studio.workers import AcquisitionMode

_T = design_tokens()
SAMPLE_RATE_HZ = 500.0
VISIBLE_SECONDS = 8.0
# hold enough samples for the widest selectable window (16 s)
MAX_POINTS = int(SAMPLE_RATE_HZ * max(DISPLAY_WINDOW_CHOICES))
# cap plotted points (peak-preserving) so wide windows stay smooth; the default
# 8 s window (4000 pts) is below this, so the common case is never decimated
MAX_PLOT_POINTS = 4000
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
        self._range_start_s: float | None = None
        # last-seen lead-off electrode set (drives the contact indicator);
        # None = unknown, so the first sample always refreshes the indicator
        self._lead_off_active: tuple[str, ...] | None = None

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

        lay.addWidget(self._caps("Save"))
        self.save_csv = QCheckBox("CSV")
        self.save_csv.setChecked(True)
        self.controls["Save CSV"] = self.save_csv
        self.save_h5 = QCheckBox("HDF5")
        self.save_h5.setChecked(True)
        self.controls["Save HDF5"] = self.save_h5
        self.save_xlsx = QCheckBox("XLSX")
        self.save_xlsx.setChecked(False)
        self.controls["Save XLSX"] = self.save_xlsx
        for i, box in enumerate((self.save_csv, self.save_h5, self.save_xlsx)):
            if i:
                lay.addSpacing(16)
            lay.addWidget(box)
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
        self._auto_btn = QPushButton("Auto scale")
        self._auto_btn.setCheckable(True)
        self._auto_btn.setChecked(True)
        self._auto_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._auto_btn.toggled.connect(self._on_autoscale_toggled)
        lay.addWidget(self._auto_btn)
        self._filter_btns: dict[str, QPushButton] = {}
        for f in ("HP", "Notch", "LP", "QRS"):
            b = QPushButton(f)
            b.setCheckable(True)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.toggled.connect(self._on_filter_changed)
            lay.addWidget(b)
            self._filter_btns[f] = b
        self._invert_btn = QPushButton("⇅ Invert ECG")
        self._invert_btn.setCheckable(True)
        self._invert_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._invert_btn.toggled.connect(self._on_filter_changed)
        lay.addWidget(self._invert_btn)
        lay.addWidget(self._caps("Scale"))
        self._window_combo = self._scale_combo(lay, "Window", display_window_labels(), "8 s")
        self._gain_combo = self._scale_combo(lay, "Gain", display_gain_labels(), "1x")
        self._speed_combo = self._scale_combo(lay, "Speed", sweep_speed_labels(), "25 mm/s")
        lay.addStretch(1)
        self._filter_hint = QLabel("CH2 Lead I · CH1 Resp · raw")
        self._filter_hint.setObjectName("Faint")
        lay.addWidget(self._filter_hint)
        return frame

    def _scale_combo(self, layout, label: str, items, default: str) -> QComboBox:
        layout.addWidget(QLabel(label))
        combo = QComboBox()
        combo.addItems(list(items))
        combo.setCurrentText(default)
        combo.currentTextChanged.connect(self._on_scale_changed)
        layout.addWidget(combo)
        return combo

    def _current_display_settings(self) -> EcgDisplaySettings:
        return EcgDisplaySettings(
            time_window_seconds=parse_display_window(self._window_combo.currentText()),
            gain=parse_display_gain(self._gain_combo.currentText()),
            sweep_speed_mm_s=parse_sweep_speed(self._speed_combo.currentText()),
        ).normalized()

    def _on_scale_changed(self) -> None:
        ds = self._current_display_settings()
        self.live_panel.set_sweep_speed(ds.sweep_speed_mm_s)
        self._redraw_live()

    def _on_autoscale_toggled(self, enabled: bool) -> None:
        self.live_panel.set_autoscale(enabled)
        self._redraw_live()

    def _on_filter_changed(self) -> None:
        self._update_filter_hint()

    def _update_filter_hint(self) -> None:
        active = [k for k, b in self._filter_btns.items() if b.isChecked()]
        parts = ["filters: " + ", ".join(active)] if active else ["raw"]
        if self._invert_btn.isChecked():
            parts.append("inv")
        self._filter_hint.setText("CH2 Lead I · CH1 Resp · " + " · ".join(parts))

    def _current_filter_settings(self) -> SoftwareFilterSettings:
        return SoftwareFilterSettings(
            highpass_enabled=self._filter_btns["HP"].isChecked(),
            notch_enabled=self._filter_btns["Notch"].isChecked(),
            lowpass_enabled=self._filter_btns["LP"].isChecked(),
            bandpass_enabled=self._filter_btns["QRS"].isChecked(),
        )

    # ---------- body ----------
    def _build_body(self) -> QWidget:
        body = QWidget()
        lay = QHBoxLayout(body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.sidebar = SidebarForms()
        for name, btn in self.sidebar.buttons.items():
            self.controls[name] = btn
        self.sidebar.buttons["Load CSV"].clicked.connect(self._on_load_csv)
        self.sidebar.buttons["Export XLSX"].clicked.connect(self._on_export_xlsx)
        self.sidebar.buttons["Export JSON"].clicked.connect(self._on_export_json)
        self.sidebar.buttons["Export Report"].clicked.connect(self._on_export_report)
        self.sidebar.buttons["Export Package"].clicked.connect(self._on_export_package)
        self.sidebar.buttons["Verify Package"].clicked.connect(self._on_verify_package)
        self.sidebar.buttons["Batch Compare"].clicked.connect(self._on_batch_compare)
        self.sidebar.buttons["Session Index"].clicked.connect(self._on_session_index)
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
        # Review tab: full-recording 2-panel view (reuses the live 2-axis canvas)
        review_tab = QWidget()
        review_lay = QVBoxLayout(review_tab)
        review_lay.setContentsMargins(0, 8, 0, 0)
        self.review_panel = LivePanel()
        self.review_panel.show_empty("Load a CSV to review a recording")
        review_lay.addWidget(self.review_panel, 1)
        self.tabs.addTab(review_tab, "Review CSV")
        self.pqrst_panel = PqrstPanel()
        self.tabs.addTab(self._tab_with(self.pqrst_panel), "PQRST Beat")
        self.spectrum_panel = SpectrumPanel()
        self.tabs.addTab(self._tab_with(self.spectrum_panel), "Spectrum")
        self.info_panel = RecordingInfoPanel()
        self.tabs.addTab(self._tab_with(self.info_panel, margins=(8, 8, 8, 8)), "Info")
        self.event_log_panel = EventLogPanel()
        self.tabs.addTab(self._tab_with(self.event_log_panel, margins=(8, 8, 8, 8)), "Event Log")
        # Registry of panels that render a loaded recording (RecordingRenderer protocol:
        # any object with render_recording(samples, sample_rate_hz, ecg_source)). To add a
        # new analysis tab, build the panel, addTab it, and append it here.
        self._recording_renderers = [self.review_panel, self.pqrst_panel, self.spectrum_panel, self.info_panel]
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

    def _tab_with(self, widget: QWidget, margins: tuple[int, int, int, int] = (0, 8, 0, 0)) -> QWidget:
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(*margins)
        lay.addWidget(widget, 1)
        return tab

    def _add_control(self, layout, name: str, slot, *, object_name: str | None = None) -> None:
        btn = QPushButton(name)
        if object_name:
            btn.setObjectName(object_name)
        # NoFocus prevents the macOS native focus ring/glow from sticking after a click
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self._lead_off_active = None
        self.controller.start(
            self.port_combo.currentText().strip(),
            save_csv=self.save_csv.isChecked(),
            save_h5=self.save_h5.isChecked(),
            save_xlsx=self.save_xlsx.isChecked(),
            mode=mode,
            metadata=self.sidebar.metadata(),
            quality_gate=self.sidebar.quality_gate(),
            protocol=self.sidebar.protocol(),
        )
        self._set_timer_active(True)
        self._refresh_state()

    def _on_stop(self) -> None:
        self.controller.stop()
        self._set_timer_active(False)
        self._refresh_state()

    def _on_load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Load ADS1292 recording", str(Path.home() / "Documents" / "ECG"),
            "Recordings (*.h5 *.csv);;HDF5 (*.h5);;CSV files (*.csv);;All files (*)",
        )
        if path:
            self.controller.load_csv(Path(path))
            self._refresh_state()

    # ---- archive actions (reuse existing core exporters) ----
    _ECG_ROOT = Path.home() / "Documents" / "ECG"

    def _export_source(self):
        """Return (samples, csv_path) for export: prefer loaded CSV, else the recording."""
        if self.controller.loaded_samples:
            return self.controller.loaded_samples, self.controller.loaded_csv_path
        if self.controller.recording_path and self.controller.recording_path.exists():
            from ads1292_studio.csv_io import read_recording_csv
            return read_recording_csv(self.controller.recording_path).samples, self.controller.recording_path
        return (), None

    def _pick_h5(self) -> Path | None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select canonical .h5 recording", str(self._ECG_ROOT), "HDF5 (*.h5)"
        )
        return Path(path) if path else None

    def _on_export_xlsx(self) -> None:
        from ads1292_studio.h5_export import export_h5_to_xlsx
        h5 = self._pick_h5()
        if h5 is None:
            return
        try:
            out = export_h5_to_xlsx(h5, h5.with_suffix(".xlsx"))
            self.event_log_panel.append_line(f"XLSX exported: {out}")
            QMessageBox.information(self, "Export XLSX", f"Written:\n{out}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export XLSX", str(exc))

    def _on_export_json(self) -> None:
        from ads1292_studio.h5_export import export_h5_to_json
        h5 = self._pick_h5()
        if h5 is None:
            return
        try:
            out = export_h5_to_json(h5, h5.with_suffix(".json"))
            self.event_log_panel.append_line(f"JSON exported: {out}")
            QMessageBox.information(self, "Export JSON", f"Written:\n{out}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export JSON", str(exc))

    def _on_export_report(self) -> None:
        from ads1292_studio.report import export_review_report
        samples, _ = self._export_source()
        if not samples:
            QMessageBox.warning(self, "Export Report", "Load a CSV or finish a recording first.")
            return
        out = self._ECG_ROOT / "reports"
        try:
            result = export_review_report(samples, out, sample_rate_hz=SAMPLE_RATE_HZ, metadata=self.sidebar.metadata())
            self.event_log_panel.append_line(f"Report exported: {getattr(result, 'html_path', out)}")
            QMessageBox.information(self, "Export Report", f"Report written under:\n{out}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Report", str(exc))

    def _on_export_package(self) -> None:
        from ads1292_studio.session_package import export_session_package
        _, csv_path = self._export_source()
        if csv_path is None:
            QMessageBox.warning(self, "Export Package", "Load a saved CSV or record with Record CSV first.")
            return
        out = self._ECG_ROOT / "packages"
        try:
            result = export_session_package(csv_path, out)
            self.event_log_panel.append_line(f"Package exported: {getattr(result, 'package_dir', out)}")
            QMessageBox.information(self, "Export Package", f"Package written under:\n{out}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Export Package", str(exc))

    def _on_verify_package(self) -> None:
        from ads1292_studio.session_package import verify_session_package
        path, _ = QFileDialog.getOpenFileName(self, "Select package manifest", str(self._ECG_ROOT), "Manifest (manifest.json);;JSON (*.json)")
        if not path:
            return
        try:
            result = verify_session_package(Path(path))
            ok = getattr(result, "ok", None)
            msg = "Package OK" if ok else f"Verification failed:\n" + "\n".join(getattr(result, "failures", []) or ["unknown"])
            QMessageBox.information(self, "Verify Package", msg)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Verify Package", str(exc))

    def _on_batch_compare(self) -> None:
        from ads1292_studio.batch import export_batch_summary
        paths, _ = QFileDialog.getOpenFileNames(self, "Select recording CSVs", str(self._ECG_ROOT), "CSV files (*.csv)")
        if not paths:
            return
        out = self._ECG_ROOT / "batch"
        try:
            export_batch_summary([Path(p) for p in paths], out)
            QMessageBox.information(self, "Batch Compare", f"Batch summary written under:\n{out}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Batch Compare", str(exc))

    def _on_session_index(self) -> None:
        from ads1292_studio.session_index import export_session_index
        from ads1292_studio.gui_session_index import build_session_index_message
        folder = QFileDialog.getExistingDirectory(self, "Select recordings folder", str(self._ECG_ROOT))
        if not folder:
            return
        out = self._ECG_ROOT / "session-index"
        try:
            result = export_session_index(Path(folder), out)
            try:
                msg = build_session_index_message(result)
            except Exception:
                msg = f"Session index written under:\n{out}"
            QMessageBox.information(self, "Session Index", msg)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Session Index", str(exc))

    def _on_calibrate(self) -> None:
        port = self.port_combo.currentText().strip()
        if self.controller.connected_port != port:
            QMessageBox.warning(self, "Calibrate Live", "Press Connect before live calibration.")
            return
        self.controller.calibrate(port)
        self.event_log_panel.append_line("Live calibration started (CH2 internal test signal, 5 runs)…")
        self._refresh_state()

    # ---- lead-off contact tracking + auto annotation ----
    def _process_lead_off(self, status_byte: int) -> None:
        """Update the live contact indicator from the per-sample lead-off status.

        Lead-off is surfaced as a non-intrusive indicator only — it is NOT
        auto-annotated as an event. The ADS1292R on this board reports lead-off
        bits unreliably (often set for the whole capture), which previously
        produced a spurious yellow event span over the entire recording. The
        raw status_byte is still persisted to CSV and summarized in the Info
        tab; real events remain user-driven via the Annotate controls.
        """
        current = electrodes_off(status_byte)
        if current == self._lead_off_active:
            return
        self._lead_off_active = current
        self.event_console.set_contact(current)

    # ---- event annotations (real EventMarkers; persisted at finalize, overlaid on plot) ----
    def _now_seconds(self) -> float:
        return self._sample_count / SAMPLE_RATE_HZ

    def _event_label(self) -> str:
        return self.event_console.label_edit.text().strip() or "event"

    def _event_notes(self) -> str:
        return self.event_console.notes_edit.text().strip()

    def _on_add_point(self) -> None:
        marker = EventMarker(
            timestamp_seconds=self._now_seconds(), label=self._event_label(), notes=self._event_notes()
        ).normalized()
        self.controller.event_markers.append(marker)
        self.event_log_panel.append_line(f"Event {marker.timestamp_seconds:.2f}s: {marker.label}")
        self._refresh_events()

    def _on_start_range(self) -> None:
        self._range_start_s = self._now_seconds()
        self._refresh_events()

    def _on_end_range(self) -> None:
        if self._range_start_s is not None:
            marker = event_from_interval(
                start_seconds=self._range_start_s, end_seconds=self._now_seconds(),
                label=self._event_label(), notes=self._event_notes(),
            )
            self.controller.event_markers.append(marker)
            self.event_log_panel.append_line(
                f"Range {marker.timestamp_seconds:.2f}-{marker.timestamp_seconds + marker.duration_seconds:.2f}s: {marker.label}"
            )
            self._range_start_s = None
        self._refresh_events()

    def _on_add_manual_range(self) -> None:
        try:
            start = float(self.event_console.manual_start_edit.text())
            end = float(self.event_console.manual_end_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Manual range", "Enter numeric start and end seconds.")
            return
        self.controller.event_markers.append(
            event_from_interval(start_seconds=start, end_seconds=end, label=self._event_label(), notes=self._event_notes())
        )
        self._refresh_events()

    def _on_remove_last(self) -> None:
        if self.controller.event_markers:
            self.controller.event_markers.pop()
        self._refresh_events()

    def _on_remove_by_number(self) -> None:
        try:
            idx = int(self.event_console.remove_index_edit.text()) - 1
        except ValueError:
            return
        if 0 <= idx < len(self.controller.event_markers):
            self.controller.event_markers.pop(idx)
        self._refresh_events()

    def _refresh_events(self) -> None:
        markers = self.controller.event_markers
        self.event_console.set_event_status(len(markers), self._range_start_s)
        self.live_panel.set_event_markers(markers, pending_range_start=self._range_start_s)

    # ---------- tick ----------
    def _set_timer_active(self, active: bool) -> None:
        self._timer.start(ACTIVE_TICK_MS if active else IDLE_TICK_MS)

    def _tick(self) -> None:
        outcome = self.controller.drain_results()
        for line in outcome.logs:
            self.event_log_panel.append_line(line)
        samples = self.controller.drain_samples()
        if samples:
            for s in samples:
                self._ch1.append(float(s.ch1))
                self._ch2.append(float(s.ch2))
            self._sample_count += len(samples)
            # A single bad render frame must never kill the live loop or the
            # ongoing recording (the worker thread keeps writing the CSV).
            try:
                self._process_lead_off(samples[-1].status_byte)
                self._redraw_live()
            except Exception as exc:  # noqa: BLE001 - keep streaming alive
                self.event_log_panel.append_line(f"live render skipped a frame: {exc}")
        if outcome.loaded_recording is not None:
            self._show_recording(outcome.loaded_recording)
        if outcome.state_changed or samples:
            self._refresh_state()
        if not self.controller.is_streaming and not samples:
            self._set_timer_active(False)
        for err in outcome.errors:
            QMessageBox.critical(self, "ADS1292 Studio", err)

    def _redraw_live(self) -> None:
        import numpy as np

        total = len(self._ch2)
        if total == 0:
            return
        ds = self._current_display_settings()
        # Window: show only the most recent N seconds of the buffer.
        visible = min(total, int(ds.time_window_seconds * SAMPLE_RATE_HZ))
        start_index = self._sample_count - visible
        xs = [(start_index + i) / SAMPLE_RATE_HZ for i in range(visible)]
        fsettings = self._current_filter_settings()
        ecg_raw = np.asarray(list(self._ch2)[-visible:], dtype=float)
        resp_raw = np.asarray(list(self._ch1)[-visible:], dtype=float)
        ecg_filtered = apply_software_filters(ecg_raw, SAMPLE_RATE_HZ, fsettings)
        if self._invert_btn.isChecked():
            ecg_filtered = -ecg_filtered
        # Gain: amplitude zoom on the ECG trace.
        ecg_y = ecg_filtered * ds.gain
        resp_y = apply_software_filters(resp_raw, SAMPLE_RATE_HZ, fsettings)
        # Peak-preserving decimation keeps wide windows smooth without losing QRS.
        xa = np.asarray(xs, dtype=float)
        ex, ey = decimate_extrema_for_plot(xa, ecg_y, MAX_PLOT_POINTS)
        rx, ry = decimate_extrema_for_plot(xa, resp_y, MAX_PLOT_POINTS)
        self.live_panel.update_traces(ex.tolist(), ey.tolist(), rx.tolist(), ry.tolist())
        self._update_live_snr()

    def _update_live_snr(self) -> None:
        import numpy as np

        if len(self._ch2) < 50:
            return
        est = estimate_realtime_snr(np.asarray(self._ch2, dtype=float), sample_rate_hz=SAMPLE_RATE_HZ)
        if est.valid:
            uv = self.live_panel._uv_per_count
            if uv is not None:
                noise_str = f"{est.noise_rms_counts * uv:.1f} µV"
            else:
                noise_str = f"{est.noise_rms_counts:.0f} ct"
            self.event_console.set_snr(f"ECG {est.snr_db:.1f} dB · noise {noise_str}")
        else:
            self.event_console.set_snr("— · acquiring…")

    def _show_recording(self, recording) -> None:
        samples = recording.samples
        if not samples:
            return
        fs = recording.sample_rate_hz or SAMPLE_RATE_HZ
        try:
            metrics = self._update_quality(samples, fs)
        except Exception as exc:  # noqa: BLE001 - never abort the whole view
            self.event_log_panel.append_line(f"quality metrics failed: {exc}")
            return
        # pass current calibration to info panel before render
        cal = self.controller.live_calibration
        self.info_panel.set_calibration(cal.mean_uv_per_count if cal is not None else None)
        # render every registered recording panel through the uniform interface
        for panel in self._recording_renderers:
            try:
                panel.render_recording(samples, fs, metrics.ecg_source)
            except Exception as exc:  # noqa: BLE001 - per-panel render is best-effort
                self.event_log_panel.append_line(f"{type(panel).__name__} render failed: {exc}")
        self.tabs.setCurrentWidget(self.tabs.widget(1))  # Review CSV

    def _update_quality(self, samples, sample_rate_hz: float):
        metrics = compute_quality_metrics(tuple(samples), sample_rate_hz=sample_rate_hz)
        cards = gui_signal_quality_cards(
            quality_label=metrics.quality_label,
            ecg_source=metrics.ecg_source,
            contact_ok_percent=metrics.contact_ok_percent,
            lead_off_bad_samples=metrics.lead_off_bad_samples,
            r_peaks=metrics.r_peaks,
            hr_median_bpm=metrics.hr_median_bpm,
            baseline_drift_counts=metrics.baseline_drift_counts,
            noise_rms_counts=metrics.noise_rms_counts,
            peak_to_peak_counts=metrics.peak_to_peak_counts,
        )
        self.status_panel.update_quality(cards)
        return metrics

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        # Never leave a recording CSV-only: finalize json+xlsx before exit.
        if self.controller.has_pending_recording or self.controller.is_streaming:
            outcome = self.controller.finalize_now()
            for line in outcome.logs:
                print(line)
            for err in outcome.errors:
                print(f"ERROR: {err}")
            if outcome.errors:
                QMessageBox.critical(
                    self, "ADS1292 Studio",
                    "Recording finalization had errors on close:\n" + "\n".join(outcome.errors),
                )
        super().closeEvent(event)

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
        # sync calibration factor to live panel (no-op when unchanged)
        cal = self.controller.live_calibration
        uv = cal.mean_uv_per_count if cal is not None else None
        if uv != self.live_panel._uv_per_count:
            self.live_panel.set_calibration(uv)

    def _set_pill(self, text: str, tone: str) -> None:
        from ads1292_studio.ui_qt.widgets import tone_color
        color = tone_color(tone)
        self.connection_pill.setText(text)
        self.connection_pill.setStyleSheet(
            f"color: {color}; font-weight: 600; padding: 4px 12px;"
            f" border: 1px solid {color}; border-radius: 11px;"
        )
