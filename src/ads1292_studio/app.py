from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from collections import deque
from datetime import datetime
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ads1292_studio.matplotlib_runtime import configure_matplotlib_cache

configure_matplotlib_cache()

import matplotlib
import numpy as np

matplotlib.use("TkAgg")

from ads1292_studio.batch import export_batch_summary
from ads1292_studio.calibration import Calibration, read_calibration_json, write_calibration_json
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.device import Ads1x9xDevice, find_ads_port, list_ads_ports
from ads1292_studio.display import (
    EcgDisplaySettings,
    SoftwareFilterSettings,
    parse_display_gain,
    parse_display_window,
    parse_sweep_speed,
)
from ads1292_studio.events import EventMarker, read_events_json, write_events_json
from ads1292_studio.gui_quality import build_quality_text, protocol_ready_for_live_quality
from ads1292_studio.gui_samples import append_live_sample_batch
from ads1292_studio.gui_log import append_log_messages, log_tab_is_visible
from ads1292_studio.gui_forms import (
    _calibration_from_values,
    _format_protocol_steps,
    _metadata_from_values,
    _parse_protocol_steps,
    _protocol_from_values,
    _quality_gate_from_values,
    _quality_gate_to_values,
)
from ads1292_studio.gui_scroll import ScrollableFrame, _mousewheel_units
from ads1292_studio.gui_session_index import build_session_index_message
from ads1292_studio.gui_state import (
    ACTIVE_TICK_INTERVAL_MS,
    IDLE_TICK_INTERVAL_MS,
    MAX_LOG_MESSAGES_PER_TICK,
    MAX_SAMPLES_PER_TICK,
    GuiState,
    GuiStatusCard,
    apply_status_card_if_changed,
    axis_limits_changed,
    channel_map_cards,
    compact_ecg_source_label,
    configure_widget_option_if_changed,
    display_refresh_key,
    display_scale_reference_label,
    drain_queue_items,
    effective_port_text,
    format_log_entries,
    gui_control_cursors,
    gui_control_states,
    gui_signal_quality_cards,
    gui_status_cards,
    gui_status_overview,
    gui_tick_interval_ms,
    gui_workflow_hint,
    header_connection_tone,
    live_metrics_text,
    live_render_refresh_key,
    port_entry_connection_message,
    selected_port_is_connected,
    set_axis_xlim_if_changed,
    set_axis_ylim_if_changed,
    set_string_var_if_changed,
    should_apply_control_state,
    toolbar_display_hint_text,
)
from ads1292_studio.gui_style import (
    configure_base_chrome,
    configure_button_chrome,
    configure_form_chrome,
    configure_header_chrome,
    configure_notebook_chrome,
    configure_panel_chrome,
    configure_scrollbar_chrome,
    configure_sidebar_card_chrome,
    configure_status_chrome,
    configure_toolbar_chrome,
)
from ads1292_studio.gui_workers import (
    ConnectResult,
    CsvLoadResult,
    LiveQualityResult,
    ReviewRenderResult,
    build_live_quality_samples,
    compute_live_quality_result,
    compute_review_render_result,
    drain_latest_generation_result,
    drain_latest_live_quality_result,
    drain_latest_review_render_result,
    live_quality_sample_count_ready,
    live_quality_update_plan,
    live_quality_worker_available,
    review_render_pending_ready,
    review_render_update_plan,
)
from ads1292_studio.gui_plots import (
    apply_live_axis_titles,
    apply_live_render_frame,
    apply_review_render_frame,
    build_live_plot_panel,
    build_log_panel,
    build_pqrst_plot_panel,
    build_review_plot_panel,
)
from ads1292_studio.gui_layout import (
    build_acquisition_toolbar,
    build_body_shell,
    build_display_toolbar,
    build_header,
    build_workspace_tabs,
    initialize_sidebar_state,
    populate_sidebar,
    register_control_buttons,
)
from ads1292_studio.gui_specs import (
    ADS1292R_CHANNEL_LABELS,
    ADS1292R_ECG_SOURCE,
    ADS1292R_PLOT_LAYOUT_LABELS,
    MAIN_TABS,
    SIGNAL_CARD_LABELS,
    SIDEBAR_TABS,
    STATUS_CARD_LABELS,
    action_section_styles,
    ads1292r_channel_label,
    ads1292r_plot_layout_labels,
    ads1292r_secondary_channel_label,
    app_visual_tokens,
    app_window_spec,
    base_checkbutton_style,
    base_chrome_spec,
    base_notebook_styles,
    button_chrome_spec,
    card_label_spec,
    empty_plot_messages,
    empty_plot_style,
    event_count_styles,
    header_connection_style,
    header_connection_styles,
    header_frame_spec,
    header_layout_spec,
    header_text_styles,
    input_chrome_spec,
    live_axis_spec,
    log_panel_spec,
    main_tab_labels,
    muted_label_spec,
    panel_chrome_spec,
    plot_axis_style,
    plot_canvas_widget_style,
    plot_figure_layouts,
    plot_panel_chrome_spec,
    plot_panel_spec,
    plot_trace_colors,
    plot_trace_styles,
    pqrst_plot_style,
    primary_toolbar_button_labels,
    protocol_note_styles,
    safety_notice_styles,
    scrollbar_chrome_spec,
    scrollable_frame_spec,
    secondary_action_button_labels,
    section_heading_styles,
    seaborn_plot_theme,
    sidebar_action_button_style,
    sidebar_field_styles,
    sidebar_layout_spec,
    sidebar_tab_labels,
    sidebar_tab_strip_styles,
    sidebar_text_card_spec,
    status_axis_spec,
    status_detail_styles,
    status_label_spec,
    status_tone_color,
    status_tone_style,
    toolbar_button_style,
    toolbar_control_styles,
    toolbar_frame_spec,
    toolbar_group_padding,
    toolbar_group_label_spec,
    toolbar_hint_styles,
    toolbar_label_spec,
    toolbar_layout_spec,
    workflow_hint_styles,
    workspace_layout_spec,
    workspace_tab_strip_styles,
)
from ads1292_studio.live_render import build_live_render_frame, display_signal_values
from ads1292_studio.macos_stderr import install_macos_stderr_filter
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import Recording, StreamSample, StreamStartResult
from ads1292_studio.plot_theme import APP_VISUAL_TOKENS
from ads1292_studio.protocol import TestProtocol, protocol_template, read_protocol_json, write_protocol_json
from ads1292_studio.quality_gate import QualityGate, read_quality_gate_json, write_quality_gate_json
from ads1292_studio.report import export_review_report
from ads1292_studio.review_render import ReviewRenderFrame, build_review_render_frame
from ads1292_studio.session_index import export_session_index
from ads1292_studio.session_package import export_session_package, verify_session_package
from ads1292_studio.workers import LiveWorker


MAX_POINTS = 10000
LIVE_MAX_RENDER_POINTS = 2500
VISIBLE_SECONDS = 8.0
SAMPLE_RATE_HZ = 500.0
DEFAULT_FILTER_ENABLED = False
DEFAULT_ECG_INVERTED = False
DEFAULT_DISPLAY_SETTINGS = EcgDisplaySettings()
DEFAULT_FILTER_SETTINGS = SoftwareFilterSettings()
DISPLAY_SMOOTHING_WINDOW = 11
DISPLAY_MIN_ECG_SPAN_COUNTS = 8.0
DISPLAY_MIN_RESP_SPAN_COUNTS = 40.0


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ADS1292 Studio")
        window_spec = app_window_spec()
        self.geometry(str(window_spec["geometry"]))
        self.minsize(*window_spec["min_size"])

        self.samples: queue.Queue[StreamSample] = queue.Queue()
        self.logs: queue.Queue[str] = queue.Queue()
        self.csv_load_results: queue.Queue[CsvLoadResult] = queue.Queue()
        self.connect_results: queue.Queue[ConnectResult] = queue.Queue()
        self.live_quality_results: queue.Queue[LiveQualityResult] = queue.Queue()
        self.live_quality_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ads1292-quality")
        self.live_quality_future: Future[LiveQualityResult] | None = None
        self.live_quality_generation = 0
        self.review_render_results: queue.Queue[ReviewRenderResult] = queue.Queue()
        self.review_render_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ads1292-review")
        self.review_render_future: Future[ReviewRenderResult] | None = None
        self.review_render_generation = 0
        self.pending_review_render_samples: tuple[StreamSample, ...] | None = None
        self.is_connecting = False
        self.stream_start_results: queue.Queue[StreamStartResult] = queue.Queue()
        self.worker = LiveWorker(self.samples, self.logs, self.stream_start_results)
        self.connected_port: str | None = None
        self.recording_path: Path | None = None
        self.loaded_samples: tuple[StreamSample, ...] = tuple()
        self.event_markers: list[EventMarker] = []
        self.is_streaming = False
        self.is_loading_csv = False
        self.is_starting = False
        self.is_closing = False
        self.tick_after_id: str | None = None

        self.sample_index = 0
        self.ch1: deque[float] = deque(maxlen=MAX_POINTS)
        self.ch2: deque[float] = deque(maxlen=MAX_POINTS)
        self.status: deque[int] = deque(maxlen=MAX_POINTS)
        self.indices: deque[int] = deque(maxlen=MAX_POINTS)
        self.board_hr: deque[int] = deque(maxlen=MAX_POINTS)
        self.board_rr: deque[int] = deque(maxlen=MAX_POINTS)
        self.empty_plot_artists: list[object] = []
        self.live_calibration_artists: list[object] = []
        self.review_calibration_artists: list[object] = []
        self.ecg_paper_grid_cache: dict[int, tuple[float, float, float, float]] = {}
        self.calibration_pulse_cache: dict[int, str] = {}
        self.last_control_state: GuiState | None = None
        self.last_display_refresh_key: tuple[object, ...] | None = None
        self.last_live_render_key: tuple[object, ...] | None = None
        self.last_live_axis_titles: tuple[str, str, str] | None = None

        self._build_ui()
        self.refresh_ports()
        self._schedule_tick()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self) -> None:
        self._configure_status_styles()
        self.connection_var = tk.StringVar(value="Not connected")
        self.configure(bg=APP_VISUAL_TOKENS["surface"])

        build_header(self)
        build_acquisition_toolbar(self)
        build_display_toolbar(
            self,
            default_display_settings=DEFAULT_DISPLAY_SETTINGS,
            default_filter_settings=DEFAULT_FILTER_SETTINGS,
            initial_hint_text=toolbar_display_hint_text(DEFAULT_DISPLAY_SETTINGS, DEFAULT_FILTER_SETTINGS),
        )
        sidebar, main = build_body_shell(self)
        initialize_sidebar_state(self, protocol_steps_text=_format_protocol_steps(protocol_template().steps))
        populate_sidebar(self, sidebar)
        build_workspace_tabs(self, main)

        build_live_plot_panel(self)
        build_review_plot_panel(self)
        build_pqrst_plot_panel(self)
        build_log_panel(self)
        register_control_buttons(self)
        self._apply_control_states()

    def _configure_status_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        configure_base_chrome(style)
        configure_header_chrome(style)
        configure_toolbar_chrome(style)
        configure_form_chrome(style)
        configure_panel_chrome(style)
        configure_scrollbar_chrome(style)
        configure_sidebar_card_chrome(style)
        configure_button_chrome(style)
        configure_notebook_chrome(style)
        configure_status_chrome(style)

    def _clear_empty_plot_state(self) -> None:
        while self.empty_plot_artists:
            artist = self.empty_plot_artists.pop()
            try:
                artist.remove()
            except ValueError:
                pass

    def refresh_ports(self) -> None:
        ports = list_ads_ports()
        values = [port.device for port in ports]
        if not values:
            guess = find_ads_port()
            values = [guess] if guess else []
        self.port_combo["values"] = values
        visible_port = effective_port_text(self.port_var.get(), self.port_combo.get())
        if values and visible_port not in values:
            self.port_var.set(values[0])
        self._sync_port_entry_connection_message()
        self._apply_control_states(force=True)

    def _on_port_value_changed(self, *_args: object) -> None:
        self._sync_port_entry_connection_message()
        self._apply_control_states(force=True)

    def _selected_port_text(self) -> str:
        return effective_port_text(
            self.port_var.get(),
            self.port_combo.get(),
            self.tk.splitlist(self.port_combo.cget("values")),
        )

    def _sync_port_entry_connection_message(self) -> None:
        port_text = self._selected_port_text()
        message = port_entry_connection_message(
            port_text=port_text,
            connected=selected_port_is_connected(self.connected_port, port_text),
            busy=self.is_connecting or self.is_starting or self.is_loading_csv,
            streaming=self.is_streaming,
        )
        if message is not None:
            set_string_var_if_changed(self.connection_var, message)

    def connect(self) -> None:
        port = self._selected_port_text()
        if not port:
            messagebox.showerror("No port", "Select an ADS1x9x serial port first.")
            return
        if self.is_connecting:
            self._log("Connect already in progress")
            return
        self.is_connecting = True
        self.connection_var.set("Connecting...")
        self._apply_control_states()
        threading.Thread(
            target=self._connect_in_background,
            args=(port,),
            daemon=True,
        ).start()

    def _connect_in_background(self, port: str) -> None:
        try:
            with Ads1x9xDevice(port) as device:
                firmware = device.query_firmware()
                try:
                    device_id = device.read_register(0x00)
                    detail = f"firmware {firmware}, ID 0x{device_id:02X}"
                except Exception:
                    detail = f"firmware {firmware}"
            self.connect_results.put(ConnectResult(port=port, detail=detail))
        except Exception as exc:
            self.connect_results.put(ConnectResult(port=port, error=str(exc)))

    def _drain_connect_results(self) -> None:
        while True:
            try:
                result = self.connect_results.get_nowait()
            except queue.Empty:
                return
            self._finish_connect(result)

    def _finish_connect(self, result: ConnectResult) -> None:
        self.is_connecting = False
        if result.error:
            self.connected_port = None
            self.connection_var.set("Connection failed")
            self._log(f"Connect failed for {result.port}: {result.error}")
            messagebox.showerror("Connection failed", result.error)
        else:
            self.connected_port = result.port
            self.connection_var.set(f"Connected: {result.detail}")
            self._log(f"Connected to {result.port}: {result.detail}")
        self._apply_control_states()

    def start(self) -> None:
        port = self._selected_port_text()
        if not port:
            messagebox.showerror("No port", "Select a port and press Connect first.")
            return
        if self.connected_port != port:
            messagebox.showerror("Not connected", "Press Connect before Start.")
            return
        self._clear_buffers()
        self.recording_path = None
        csv_path = None
        if self.save_var.get():
            stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            csv_path = Path("recordings") / f"{stamp}-ads1292-studio.csv"
            self.recording_path = csv_path
            write_metadata_json(csv_path.with_suffix(".json"), self._metadata())
            write_events_json(self._events_path(csv_path), self.event_markers)
            write_calibration_json(self._calibration_path(csv_path), self._calibration())
            write_protocol_json(self._protocol_path(csv_path), self._protocol())
            write_quality_gate_json(self._quality_gate_path(csv_path), self._quality_gate())
            self.path_var.set(f"CSV: {csv_path}")
        self.is_starting = True
        self.connection_var.set("Starting stream...")
        self.worker.start(port, csv_path)
        self._apply_control_states()

    def stop(self) -> None:
        self.worker.stop()
        self.is_streaming = False
        self.connection_var.set(f"Connected: {self.connected_port}" if self.connected_port else "Stopped")
        self._apply_control_states()

    def _drain_stream_start_results(self) -> None:
        while True:
            try:
                result = self.stream_start_results.get_nowait()
            except queue.Empty:
                return
            self._finish_stream_start(result)

    def _finish_stream_start(self, result: StreamStartResult) -> None:
        self.is_starting = False
        if result.ok:
            self.is_streaming = True
            self.connection_var.set("Streaming")
        else:
            self.is_streaming = False
            self.connection_var.set(f"Connected: {self.connected_port}" if self.connected_port else "Stopped")
            messagebox.showerror("Start failed", result.error or "Unknown error starting stream")
        self._apply_control_states()

    def load_csv(self) -> None:
        if self.is_loading_csv:
            self._log("CSV load already in progress")
            return
        path = filedialog.askopenfilename(
            title="Load ADS1292 CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        csv_path = Path(path)
        self.is_loading_csv = True
        self.path_var.set(f"Loading CSV: {csv_path}")
        self.metrics_var.set("Loading CSV...")
        self.quality_var.set("Quality: waiting for CSV parse")
        self._log(f"Loading CSV in background: {csv_path}")
        self._apply_control_states()
        display_settings = self._display_settings()
        filter_settings = self._software_filter_settings()
        threading.Thread(
            target=self._read_csv_in_background,
            args=(csv_path, display_settings, filter_settings),
            daemon=True,
        ).start()

    def _read_csv_in_background(
        self,
        path: Path,
        display_settings: EcgDisplaySettings,
        filter_settings: SoftwareFilterSettings,
    ) -> None:
        try:
            recording = read_recording_csv(path)
            review_frame = build_review_render_frame(
                recording.samples,
                display_settings=display_settings,
                filter_settings=filter_settings,
                source=ADS1292R_ECG_SOURCE,
                sample_rate_hz=SAMPLE_RATE_HZ,
                smoothing_window=DISPLAY_SMOOTHING_WINDOW,
                max_points=MAX_POINTS,
                ecg_inverted=DEFAULT_ECG_INVERTED,
                min_ecg_span_counts=DISPLAY_MIN_ECG_SPAN_COUNTS,
                min_resp_span_counts=DISPLAY_MIN_RESP_SPAN_COUNTS,
            )
            self.csv_load_results.put(
                CsvLoadResult(
                    path=path,
                    recording=recording,
                    review_frame=review_frame,
                    display_settings=display_settings,
                    filter_settings=filter_settings,
                )
            )
        except Exception as exc:
            self.csv_load_results.put(CsvLoadResult(path=path, error=str(exc)))

    def _drain_csv_load_results(self) -> None:
        while True:
            try:
                result = self.csv_load_results.get_nowait()
            except queue.Empty:
                return
            self._finish_csv_load(result)

    def _finish_csv_load(self, result: CsvLoadResult) -> None:
        self.is_loading_csv = False
        if result.error or result.recording is None:
            self.path_var.set(f"CSV load failed: {result.path}")
            self._log(f"Load failed for {result.path}: {result.error}")
            self._apply_control_states()
            messagebox.showerror("Load failed", result.error or "Unknown CSV load error")
            return
        try:
            self.recording_path = result.path
            self.loaded_samples = result.recording.samples
            self._load_event_sidecar(result.path)
            self._load_calibration_sidecar(result.path)
            self._load_protocol_sidecar(result.path)
            self._load_quality_gate_sidecar(result.path)
            if (
                result.review_frame is not None
                and result.display_settings == self._display_settings()
                and result.filter_settings == self._software_filter_settings()
            ):
                self._show_review_frame(result.recording.samples, result.review_frame)
            else:
                self._show_recording(result.recording.samples)
            self.path_var.set(f"CSV: {result.path}")
            self._log(f"Loaded {result.path}")
        except Exception as exc:
            self.path_var.set(f"CSV load failed: {result.path}")
            self._log(f"Load failed after parsing {result.path}: {exc}")
            messagebox.showerror("Load failed", str(exc))
        finally:
            self._apply_control_states()

    def add_event(self) -> None:
        marker = EventMarker(
            timestamp_seconds=self._current_event_time(),
            label=self.event_label_var.get(),
            notes=self.event_notes_var.get(),
        ).normalized()
        self.event_markers = [*self.event_markers, marker]
        self._set_event_count()
        self._save_event_sidecar()
        self._log(f"Event {marker.timestamp_seconds:.2f}s: {marker.label} {marker.notes}".strip())

    def export_report(self) -> None:
        if self.loaded_samples:
            samples = self.loaded_samples
        elif self.ch1 and self.ch2:
            samples = tuple(
                StreamSample(
                    timestamp=index / SAMPLE_RATE_HZ,
                    ch1=int(ch1),
                    ch2=int(ch2),
                    board_heart_rate=0,
                    board_respiration_rate=0,
                    status_byte=int(status),
                )
                for index, (ch1, ch2, status) in enumerate(zip(self.ch1, self.ch2, self.status))
            )
        else:
            messagebox.showerror("No data", "Load a CSV or record data before exporting a report.")
            return
        out_dir = filedialog.askdirectory(title="Choose report output folder")
        if not out_dir:
            return
        try:
            export = export_review_report(
                samples=samples,
                out_dir=Path(out_dir),
                title="ADS1292 Studio Review",
                sample_rate_hz=SAMPLE_RATE_HZ,
                source=ADS1292R_ECG_SOURCE,
                metadata=self._metadata(),
                events=tuple(self.event_markers),
                calibration=self._calibration(),
                quality_gate=self._quality_gate(),
                protocol=self._protocol(),
            )
            self._log(f"Exported report: {export.html_path}")
            messagebox.showinfo("Report exported", f"Saved report:\n{export.html_path}")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))

    def batch_compare(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Choose ADS1292 CSV files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not paths:
            return
        out_dir = filedialog.askdirectory(title="Choose batch output folder")
        if not out_dir:
            return
        try:
            export = export_batch_summary(
                paths=[Path(path) for path in paths],
                out_dir=Path(out_dir),
                title="ADS1292 Batch Summary",
            )
            self._log(f"Exported batch summary: {export.html_path}")
            messagebox.showinfo("Batch summary exported", f"Saved summary:\n{export.html_path}")
        except Exception as exc:
            messagebox.showerror("Batch export failed", str(exc))

    def session_index(self) -> None:
        root = filedialog.askdirectory(title="Choose recordings folder")
        if not root:
            return
        out_dir = filedialog.askdirectory(title="Choose session index output folder")
        if not out_dir:
            return
        try:
            export = export_session_index(
                root=Path(root),
                out_dir=Path(out_dir),
                title="ADS1292 Session Index",
            )
            self._log(f"Exported session index: {export.html_path}")
            messagebox.showinfo("Session index exported", build_session_index_message(export))
        except Exception as exc:
            messagebox.showerror("Session index failed", str(exc))

    def export_package(self) -> None:
        if self.recording_path is None:
            messagebox.showerror("No CSV", "Load a CSV or record with Save CSV before exporting a package.")
            return
        out_dir = filedialog.askdirectory(title="Choose package output folder")
        if not out_dir:
            return
        try:
            self._write_current_sidecars()
            export = export_session_package(
                csv_path=self.recording_path,
                out_dir=Path(out_dir),
                title="ADS1292 Session Package",
                source=ADS1292R_ECG_SOURCE,
            )
            self._log(f"Exported package: {export.manifest_path}")
            messagebox.showinfo("Package exported", f"Saved package manifest:\n{export.manifest_path}")
        except Exception as exc:
            messagebox.showerror("Package export failed", str(exc))

    def verify_package(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose package manifest",
            filetypes=[("Manifest JSON", "manifest.json"), ("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            result = verify_session_package(Path(path))
            if result.ok:
                self._log(f"Verified package: {result.checked_files} files OK")
                messagebox.showinfo("Package verified", f"{result.checked_files} files verified.")
                return
            failures = "\n".join(result.failures)
            self._log(f"Package verification failed: {failures}")
            messagebox.showerror("Package verification failed", failures)
        except Exception as exc:
            messagebox.showerror("Package verification failed", str(exc))

    def _clear_buffers(self) -> None:
        self.sample_index = 0
        self.loaded_samples = tuple()
        self.event_markers = []
        self._set_event_count()
        self._clear_signal_buffers()
        self._apply_control_states()

    def _clear_signal_buffers(self) -> None:
        for buffer in (self.ch1, self.ch2, self.status, self.indices, self.board_hr, self.board_rr):
            buffer.clear()
        self.last_display_refresh_key = None
        self.last_live_render_key = None
        self.live_quality_generation += 1
        self.review_render_generation += 1
        self.pending_review_render_samples = None
        if self.live_quality_future is not None and not self.live_quality_future.done():
            self.live_quality_future.cancel()
        if self.review_render_future is not None and not self.review_render_future.done():
            self.review_render_future.cancel()
        while True:
            try:
                self.live_quality_results.get_nowait()
            except queue.Empty:
                break
        while True:
            try:
                self.review_render_results.get_nowait()
            except queue.Empty:
                break

    def _current_gui_state(self) -> GuiState:
        port_text = self._selected_port_text()
        return GuiState(
            connected=selected_port_is_connected(self.connected_port, port_text),
            streaming=self.is_streaming,
            has_data=bool(self.loaded_samples or (self.ch1 and self.ch2)),
            has_recording_path=self.recording_path is not None,
            has_port=bool(port_text.strip()),
            loading_csv=self.is_loading_csv,
            connecting=self.is_connecting,
            starting=self.is_starting,
        )

    def _apply_control_states(self, *, force: bool = False) -> None:
        if not hasattr(self, "control_buttons"):
            return
        state = self._current_gui_state()
        if not should_apply_control_state(self.last_control_state, state, force=force):
            return
        self.last_control_state = state
        states = gui_control_states(state=state)
        set_string_var_if_changed(
            self.workflow_hint_var,
            gui_workflow_hint(state=state)
        )
        set_string_var_if_changed(
            self.status_overview_var,
            gui_status_overview(state=state)
        )
        configure_widget_option_if_changed(
            self.connection_label,
            "style",
            header_connection_style(header_connection_tone(state=state)),
        )
        for card in gui_status_cards(state=state):
            apply_status_card_if_changed(
                variable=self.status_card_vars[card.label],
                value_label=self.status_card_value_labels[card.label],
                stripe=self.status_card_tone_stripes[card.label],
                card=card,
            )
        if not state.has_data:
            self._apply_signal_quality_cards(gui_signal_quality_cards())
        cursors = gui_control_cursors(states)
        for label, button in self.control_buttons.items():
            configure_widget_option_if_changed(button, "state", states[label])
            configure_widget_option_if_changed(button, "cursor", cursors[label])

    def _apply_signal_quality_cards(self, cards: tuple[GuiStatusCard, ...]) -> None:
        for card in cards:
            apply_status_card_if_changed(
                variable=self.signal_card_vars[card.label],
                value_label=self.signal_card_value_labels[card.label],
                stripe=self.signal_card_tone_stripes[card.label],
                card=card,
            )

    def _metadata(self) -> SessionMetadata:
        return _metadata_from_values(
            session_id=self.session_id_var.get(),
            subject_id=self.subject_id_var.get(),
            electrode=self.electrode_var.get(),
            montage=self.montage_var.get(),
            operator=self.operator_var.get(),
            notes=self.notes_var.get(),
        ).normalized()

    def _current_event_time(self) -> float:
        if self.sample_index > 0:
            return self.sample_index / SAMPLE_RATE_HZ
        if self.loaded_samples:
            return len(self.loaded_samples) / SAMPLE_RATE_HZ
        return 0.0

    def _events_path(self, csv_path: Path) -> Path:
        return csv_path.with_suffix(".events.json")

    def _calibration_path(self, csv_path: Path) -> Path:
        return csv_path.with_suffix(".calibration.json")

    def _protocol_path(self, csv_path: Path) -> Path:
        return csv_path.with_suffix(".protocol.json")

    def _quality_gate_path(self, csv_path: Path) -> Path:
        return csv_path.with_suffix(".quality-gate.json")

    def _load_event_sidecar(self, csv_path: Path) -> None:
        path = self._events_path(csv_path)
        if not path.exists():
            self.event_markers = []
            self._set_event_count()
            return
        self.event_markers = list(read_events_json(path))
        self._set_event_count()
        self._log(f"Loaded events: {path}")

    def _save_event_sidecar(self) -> None:
        if self.recording_path is None:
            return
        write_events_json(self._events_path(self.recording_path), self.event_markers)

    def _set_event_count(self) -> None:
        self.event_count_var.set(f"{len(self.event_markers)} events")

    def _calibration(self) -> Calibration:
        return _calibration_from_values(
            label=self.calibration_label_var.get(),
            vref_mv=self.vref_mv_var.get(),
            pga_gain=self.pga_gain_var.get(),
        )

    def _protocol(self) -> TestProtocol:
        return _protocol_from_values(
            name=self.protocol_name_var.get(),
            objective=self.protocol_objective_var.get(),
            steps_text=self.protocol_steps_var.get(),
            acceptance_notes=self.protocol_acceptance_var.get(),
        )

    def _quality_gate(self) -> QualityGate:
        return _quality_gate_from_values(
            {
                "min_duration_seconds": self.gate_min_duration_var.get(),
                "min_contact_ok_percent": self.gate_min_contact_var.get(),
                "min_r_peaks": self.gate_min_r_peaks_var.get(),
                "min_hr_bpm": self.gate_min_hr_var.get(),
                "max_hr_bpm": self.gate_max_hr_var.get(),
                "require_qrs_clear": self.gate_require_qrs_var.get(),
                "max_baseline_drift_counts": self.gate_max_drift_var.get(),
                "max_noise_rms_counts": self.gate_max_noise_var.get(),
                "max_peak_to_peak_counts": self.gate_max_ptp_var.get(),
            }
        )

    def _load_calibration_sidecar(self, csv_path: Path) -> None:
        path = self._calibration_path(csv_path)
        if not path.exists():
            return
        calibration = read_calibration_json(path)
        self.calibration_label_var.set(calibration.label)
        self.vref_mv_var.set(f"{calibration.vref_mv:g}")
        self.pga_gain_var.set(f"{calibration.pga_gain:g}")
        self._log(f"Loaded calibration: {path}")

    def _load_protocol_sidecar(self, csv_path: Path) -> None:
        path = self._protocol_path(csv_path)
        if not path.exists():
            return
        protocol = read_protocol_json(path)
        self.protocol_name_var.set(protocol.name)
        self.protocol_objective_var.set(protocol.objective)
        self.protocol_steps_var.set(_format_protocol_steps(protocol.steps))
        self.protocol_acceptance_var.set(protocol.acceptance_notes)
        self._log(f"Loaded protocol: {path}")

    def _load_quality_gate_sidecar(self, csv_path: Path) -> None:
        path = self._quality_gate_path(csv_path)
        if not path.exists():
            return
        values = _quality_gate_to_values(read_quality_gate_json(path))
        self.gate_min_duration_var.set(str(values["min_duration_seconds"]))
        self.gate_min_contact_var.set(str(values["min_contact_ok_percent"]))
        self.gate_min_r_peaks_var.set(str(values["min_r_peaks"]))
        self.gate_min_hr_var.set(str(values["min_hr_bpm"]))
        self.gate_max_hr_var.set(str(values["max_hr_bpm"]))
        self.gate_require_qrs_var.set(bool(values["require_qrs_clear"]))
        self.gate_max_drift_var.set(str(values["max_baseline_drift_counts"]))
        self.gate_max_noise_var.set(str(values["max_noise_rms_counts"]))
        self.gate_max_ptp_var.set(str(values["max_peak_to_peak_counts"]))
        self._log(f"Loaded quality gate: {path}")

    def _write_current_sidecars(self) -> None:
        if self.recording_path is None:
            return
        write_metadata_json(self.recording_path.with_suffix(".json"), self._metadata())
        write_events_json(self._events_path(self.recording_path), self.event_markers)
        write_calibration_json(self._calibration_path(self.recording_path), self._calibration())
        write_protocol_json(self._protocol_path(self.recording_path), self._protocol())
        write_quality_gate_json(self._quality_gate_path(self.recording_path), self._quality_gate())

    def _schedule_tick(self) -> None:
        if self.is_closing or self.tick_after_id is not None:
            return
        self.tick_after_id = self.after(gui_tick_interval_ms(self._current_gui_state()), self._tick)

    def _cancel_tick(self) -> None:
        if self.tick_after_id is None:
            return
        try:
            self.after_cancel(self.tick_after_id)
        except tk.TclError:
            pass
        self.tick_after_id = None

    def _tick(self) -> None:
        self.tick_after_id = None
        if self.is_closing:
            return
        self._drain_csv_load_results()
        self._drain_review_render_results()
        self._drain_connect_results()
        self._drain_stream_start_results()
        self._drain_live_quality_results()
        sample_batch = drain_queue_items(self.samples, MAX_SAMPLES_PER_TICK)
        self.sample_index, latest = append_live_sample_batch(
            sample_batch,
            start_index=self.sample_index,
            indices=self.indices,
            ch1=self.ch1,
            ch2=self.ch2,
            status=self.status,
            board_hr=self.board_hr,
            board_rr=self.board_rr,
        )
        if latest is not None:
            self._redraw_live()
            self._apply_control_states()
        log_messages = drain_queue_items(self.logs, MAX_LOG_MESSAGES_PER_TICK)
        self._append_log_messages(log_messages)
        self._drain_live_quality_results()
        self._drain_review_render_results()
        self._schedule_tick()

    def _schedule_live_quality_update(
        self,
        *,
        source: str,
        valid_rr: int,
    ) -> None:
        plan = live_quality_update_plan(
            future=self.live_quality_future,
            generation=self.live_quality_generation,
            sample_count=len(self.ch2),
            sample_rate_hz=SAMPLE_RATE_HZ,
        )
        if not plan.should_submit:
            return
        ch1_values = tuple(self.ch1)
        ch2_values = tuple(self.ch2)
        status_values = tuple(self.status)
        self.live_quality_generation = plan.generation
        future = self.live_quality_executor.submit(
            compute_live_quality_result,
            generation=plan.generation,
            source=source,
            valid_rr=valid_rr,
            ch1_values=ch1_values,
            ch2_values=ch2_values,
            status_values=status_values,
            sample_rate_hz=SAMPLE_RATE_HZ,
            ecg_source=ADS1292R_ECG_SOURCE,
        )
        future.add_done_callback(self._queue_live_quality_result)
        self.live_quality_future = future

    def _queue_live_quality_result(self, future: Future[LiveQualityResult]) -> None:
        if future.cancelled():
            return
        try:
            result = future.result()
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            result = LiveQualityResult(
                generation=self.live_quality_generation,
                source=ADS1292R_ECG_SOURCE,
                valid_rr=0,
                samples=tuple(),
                status_values=tuple(),
                error=str(exc),
            )
        self.live_quality_results.put(result)

    def _schedule_review_render_update(self, samples: tuple[StreamSample, ...]) -> bool:
        plan = review_render_update_plan(
            future=self.review_render_future,
            generation=self.review_render_generation,
            samples=samples,
        )
        self.review_render_generation = plan.generation
        self.pending_review_render_samples = plan.pending_samples
        if not plan.should_submit:
            return False
        display_settings = self._display_settings()
        filter_settings = self._software_filter_settings()
        future = self.review_render_executor.submit(
            compute_review_render_result,
            generation=plan.generation,
            samples=samples,
            display_settings=display_settings,
            filter_settings=filter_settings,
            source=ADS1292R_ECG_SOURCE,
            sample_rate_hz=SAMPLE_RATE_HZ,
            smoothing_window=DISPLAY_SMOOTHING_WINDOW,
            max_points=MAX_POINTS,
            ecg_inverted=DEFAULT_ECG_INVERTED,
            min_ecg_span_counts=DISPLAY_MIN_ECG_SPAN_COUNTS,
            min_resp_span_counts=DISPLAY_MIN_RESP_SPAN_COUNTS,
        )
        future.add_done_callback(self._queue_review_render_result)
        self.review_render_future = future
        return True

    def _queue_review_render_result(self, future: Future[ReviewRenderResult]) -> None:
        if future.cancelled():
            return
        try:
            result = future.result()
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            result = ReviewRenderResult(generation=self.review_render_generation, samples=tuple(), error=str(exc))
        self.review_render_results.put(result)

    def _drain_review_render_results(self) -> None:
        latest = drain_latest_review_render_result(
            self.review_render_results,
            generation=self.review_render_generation,
        )
        if latest is None:
            self._schedule_pending_review_render()
            return
        if latest.error or latest.frame is None:
            set_string_var_if_changed(
                self.quality_var,
                f"Quality: review redraw failed: {latest.error or 'unknown error'}",
            )
            self._apply_control_states()
            self._schedule_pending_review_render()
            return
        self._show_review_frame(latest.samples, latest.frame)
        self._apply_control_states()
        self._schedule_pending_review_render()

    def _schedule_pending_review_render(self) -> None:
        samples = review_render_pending_ready(
            future=self.review_render_future,
            pending_samples=self.pending_review_render_samples,
        )
        if samples is None:
            return
        self.pending_review_render_samples = None
        self._schedule_review_render_update(samples)

    def _drain_live_quality_results(self) -> None:
        latest = drain_latest_live_quality_result(
            self.live_quality_results,
            generation=self.live_quality_generation,
        )
        if latest is None:
            return
        self._apply_live_quality_result(latest)

    def _apply_live_quality_result(self, result: LiveQualityResult) -> None:
        if result.error or result.metrics is None:
            set_string_var_if_changed(
                self.quality_var,
                f"Quality: background update failed: {result.error or 'unknown error'}",
            )
            self._apply_signal_quality_cards(gui_signal_quality_cards())
            return
        set_string_var_if_changed(
            self.quality_var,
            self._quality_text(
                result.source,
                result.valid_rr,
                result.samples,
                result.status_values,
                metrics=result.metrics,
            ),
        )
        self._apply_signal_quality_cards(
            gui_signal_quality_cards(
                quality_label=result.metrics.quality_label,
                ecg_source=result.metrics.ecg_source,
                contact_ok_percent=result.metrics.contact_ok_percent,
                lead_off_bad_samples=result.metrics.lead_off_bad_samples,
                r_peaks=result.metrics.r_peaks,
                hr_median_bpm=result.metrics.hr_median_bpm,
                baseline_drift_counts=result.metrics.baseline_drift_counts,
                noise_rms_counts=result.metrics.noise_rms_counts,
                peak_to_peak_counts=result.metrics.peak_to_peak_counts,
            )
        )

    def _refresh_display_plots(self, _event: tk.Event | None = None) -> None:
        key = self._display_refresh_key()
        if self.last_display_refresh_key == key:
            return
        self.last_display_refresh_key = key
        self._sync_toolbar_hint()
        if self.is_streaming and self.indices:
            self._redraw_live()
            return
        if self.loaded_samples:
            if self._schedule_review_render_update(self.loaded_samples):
                set_string_var_if_changed(self.metrics_var, "Review redraw queued...")
            else:
                set_string_var_if_changed(self.metrics_var, "Review redraw already running...")
            return
        if self.indices:
            self._redraw_live()

    def _display_refresh_key(self) -> tuple[object, ...]:
        if self.loaded_samples:
            mode = "review"
        elif self.indices:
            mode = "live"
        else:
            mode = "empty"
        return display_refresh_key(
            mode=mode,
            display_settings=self._display_settings(),
            filter_settings=self._software_filter_settings(),
            autoscale=bool(self.autoscale_var.get()),
            sample_index=self.sample_index,
            loaded_count=len(self.loaded_samples),
            recording_path=self.recording_path,
        )

    def _sync_toolbar_hint(self) -> None:
        if not hasattr(self, "toolbar_hint_var"):
            return
        set_string_var_if_changed(
            self.toolbar_hint_var,
            toolbar_display_hint_text(self._display_settings(), self._software_filter_settings()),
        )

    def _display_settings(self) -> EcgDisplaySettings:
        return EcgDisplaySettings(
            time_window_seconds=parse_display_window(self.display_window_var.get()),
            gain=parse_display_gain(self.display_gain_var.get()),
            sweep_speed_mm_s=parse_sweep_speed(self.sweep_speed_var.get()),
        ).normalized()

    def _software_filter_settings(self) -> SoftwareFilterSettings:
        return SoftwareFilterSettings(
            highpass_enabled=bool(self.highpass_filter_var.get()),
            notch_enabled=bool(self.notch_filter_var.get()),
            lowpass_enabled=bool(self.lowpass_filter_var.get()),
            bandpass_enabled=bool(self.filter_var.get()),
        )

    def _ads1292r_display_channels(self) -> tuple[str, np.ndarray, np.ndarray]:
        ch1 = np.asarray(self.ch1, dtype=float)
        ch2 = np.asarray(self.ch2, dtype=float)
        return ADS1292R_ECG_SOURCE, ch2, ch1

    def _display_signal(
        self,
        values: np.ndarray,
        *,
        filter_settings: SoftwareFilterSettings | None = None,
        invert: bool = False,
        gain: float = 1.0,
    ) -> np.ndarray:
        settings = filter_settings or self._software_filter_settings()
        return display_signal_values(
            values,
            filter_enabled=bool(settings.bandpass_enabled),
            filter_settings=settings,
            invert=invert,
            gain=gain,
            sample_rate_hz=SAMPLE_RATE_HZ,
        )

    def _redraw_live(self) -> None:
        if not self.indices:
            return
        display_settings = self._display_settings()
        filter_settings = self._software_filter_settings()
        render_key = live_render_refresh_key(
            sample_index=self.sample_index,
            display_settings=display_settings,
            filter_settings=filter_settings,
            autoscale=bool(self.autoscale_var.get()),
            source=ADS1292R_ECG_SOURCE,
            ecg_inverted=DEFAULT_ECG_INVERTED,
        )
        if self.last_live_render_key == render_key:
            return
        frame = build_live_render_frame(
            indices=self.indices,
            ch1=self.ch1,
            ch2=self.ch2,
            status=self.status,
            display_settings=display_settings,
            filter_settings=filter_settings,
            source=ADS1292R_ECG_SOURCE,
            sample_rate_hz=SAMPLE_RATE_HZ,
            smoothing_window=DISPLAY_SMOOTHING_WINDOW,
            max_render_points=LIVE_MAX_RENDER_POINTS,
            ecg_inverted=DEFAULT_ECG_INVERTED,
        )
        if frame is None:
            return

        self.last_live_render_key = render_key
        self._clear_empty_plot_state()
        apply_live_render_frame(
            self,
            frame,
            display_settings=display_settings,
            autoscale=bool(self.autoscale_var.get()),
            min_ecg_span_counts=DISPLAY_MIN_ECG_SPAN_COUNTS,
            min_resp_span_counts=DISPLAY_MIN_RESP_SPAN_COUNTS,
        )
        ecg_label, resp_label, contact_label = ads1292r_plot_layout_labels()
        apply_live_axis_titles(
            self,
            display_settings,
            filter_settings,
            ecg_label=ecg_label,
            resp_label=resp_label,
            contact_label=contact_label,
            ecg_inverted=DEFAULT_ECG_INVERTED,
        )
        set_string_var_if_changed(
            self.metrics_var,
            live_metrics_text(
                sample_index=self.sample_index,
                duration_seconds=float(frame.visible_x[-1]),
                ecg_label=ecg_label,
                heart_rate_bpm=frame.heart_rate.median_bpm,
                peak_count=len(frame.peaks),
            ),
        )
        self._schedule_live_quality_update(
            source=frame.source,
            valid_rr=frame.heart_rate.valid_rr_count,
        )

    def _show_recording(self, samples: tuple[StreamSample, ...]) -> None:
        frame = build_review_render_frame(
            samples,
            display_settings=self._display_settings(),
            filter_settings=self._software_filter_settings(),
            source=ADS1292R_ECG_SOURCE,
            sample_rate_hz=SAMPLE_RATE_HZ,
            smoothing_window=DISPLAY_SMOOTHING_WINDOW,
            max_points=MAX_POINTS,
            ecg_inverted=DEFAULT_ECG_INVERTED,
            min_ecg_span_counts=DISPLAY_MIN_ECG_SPAN_COUNTS,
            min_resp_span_counts=DISPLAY_MIN_RESP_SPAN_COUNTS,
        )
        self._show_review_frame(samples, frame)

    def _show_review_frame(self, samples: tuple[StreamSample, ...], frame: ReviewRenderFrame) -> None:
        self._clear_empty_plot_state()
        self._clear_signal_buffers()
        self.sample_index = 0
        display_settings = self._display_settings()
        ecg_label, resp_label, contact_label = ads1292r_plot_layout_labels()
        apply_review_render_frame(
            self,
            frame,
            display_settings=display_settings,
            ecg_label=ecg_label,
            resp_label=resp_label,
            contact_label=contact_label,
            ecg_inverted=DEFAULT_ECG_INVERTED,
        )
        set_string_var_if_changed(
            self.metrics_var,
            f"samples {frame.sample_count} | duration {frame.duration_seconds:.1f} s | source {ecg_label}",
        )
        set_string_var_if_changed(
            self.quality_var,
            f"{self._quality_text(frame.source, frame.review.heart_rate.valid_rr_count, samples, frame.status_values, metrics=frame.metrics)} | "
            f"QRS {'clear' if frame.review.pqrst.qrs_clear else 'unclear'} | "
            f"P {'tentative' if frame.review.pqrst.p_tentative else 'not reliable'} | "
            f"T {'tentative' if frame.review.pqrst.t_tentative else 'not reliable'}",
        )
        self._apply_signal_quality_cards(
            gui_signal_quality_cards(
                quality_label=frame.metrics.quality_label,
                ecg_source=frame.metrics.ecg_source,
                contact_ok_percent=frame.metrics.contact_ok_percent,
                lead_off_bad_samples=frame.metrics.lead_off_bad_samples,
                r_peaks=frame.metrics.r_peaks,
                hr_median_bpm=frame.metrics.hr_median_bpm,
                baseline_drift_counts=frame.metrics.baseline_drift_counts,
                noise_rms_counts=frame.metrics.noise_rms_counts,
                peak_to_peak_counts=frame.metrics.peak_to_peak_counts,
            )
        )

    def _quality_text(
        self,
        source: str,
        valid_rr: int,
        samples: tuple[StreamSample, ...],
        status_values: tuple[int, ...],
        metrics=None,
    ) -> str:
        protocol = self._protocol()
        should_evaluate_protocol = bool(self.loaded_samples) or protocol_ready_for_live_quality(
            samples,
            protocol,
            SAMPLE_RATE_HZ,
        )
        return build_quality_text(
            samples=samples,
            status_values=status_values,
            source=source,
            selected_source=ADS1292R_ECG_SOURCE,
            valid_rr=valid_rr,
            protocol=protocol if should_evaluate_protocol else None,
            sample_rate_hz=SAMPLE_RATE_HZ,
            gate=self._quality_gate(),
            metrics=metrics,
        )

    def _log(self, message: str) -> None:
        self._append_log_messages((message,))

    def _append_log_messages(self, messages: tuple[str, ...]) -> None:
        append_log_messages(
            self.log_text,
            messages,
            stamp=datetime.now().strftime("%H:%M:%S"),
            max_lines=int(log_panel_spec()["max_lines"]),
            autoscroll=log_tab_is_visible(
                selected_workspace_tab=self.selected_workspace_tab,
                log_tab=getattr(self, "log_tab", None),
            ),
        )

    def _close(self) -> None:
        self.is_closing = True
        self._cancel_tick()
        self.worker.stop()
        if self.live_quality_future is not None and not self.live_quality_future.done():
            self.live_quality_future.cancel()
        if self.review_render_future is not None and not self.review_render_future.done():
            self.review_render_future.cancel()
        self.live_quality_executor.shutdown(wait=False, cancel_futures=True)
        self.review_render_executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()

    def destroy(self) -> None:
        self.is_closing = True
        self._cancel_tick()
        super().destroy()


def main() -> None:
    install_macos_stderr_filter()
    App().mainloop()


if __name__ == "__main__":
    main()
