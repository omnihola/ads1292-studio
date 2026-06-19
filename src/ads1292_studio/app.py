from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import TypeVar

from ads1292_studio.matplotlib_runtime import configure_matplotlib_cache

configure_matplotlib_cache()

import matplotlib
import numpy as np

matplotlib.use("TkAgg")
from matplotlib.ticker import MultipleLocator

from ads1292_studio.batch import export_batch_summary
from ads1292_studio.calibration import Calibration, read_calibration_json, write_calibration_json
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.device import Ads1x9xDevice, find_ads_port, list_ads_ports
from ads1292_studio.display import (
    EcgDisplaySettings,
    SoftwareFilterSettings,
    display_mode_label,
    ecg_paper_grid_key,
    ecg_paper_grid_spec,
    parse_display_gain,
    parse_display_window,
    parse_sweep_speed,
)
from ads1292_studio.events import EventMarker, read_events_json, write_events_json
from ads1292_studio.gui_quality import build_quality_text, protocol_ready_for_live_quality
from ads1292_studio.gui_session_index import build_session_index_message
from ads1292_studio.gui_plots import (
    build_live_plot_panel,
    build_log_panel,
    build_pqrst_plot_panel,
    build_review_plot_panel,
    set_signal_axis_title,
    style_signal_axes,
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
    plot_panel_spec,
    plot_trace_colors,
    plot_trace_styles,
    pqrst_plot_style,
    primary_toolbar_button_labels,
    protocol_note_styles,
    safety_notice_styles,
    scrollbar_chrome_spec,
    secondary_action_button_labels,
    section_heading_styles,
    seaborn_plot_theme,
    sidebar_action_button_style,
    sidebar_field_styles,
    sidebar_layout_spec,
    sidebar_notebook_styles,
    sidebar_tab_labels,
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
    workspace_notebook_styles,
)
from ads1292_studio.live_render import build_live_render_frame, display_signal_values
from ads1292_studio.macos_stderr import install_macos_stderr_filter
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import PqrstReview, Recording, StreamSample, StreamStartResult
from ads1292_studio.plot_theme import (
    APP_VISUAL_TOKENS,
    PLOT_TRACE_COLORS,
)
from ads1292_studio.plots import robust_ylim, stable_ylim
from ads1292_studio.protocol import ProtocolStep, TestProtocol, protocol_template, read_protocol_json, write_protocol_json
from ads1292_studio.quality import QualityMetrics, compute_quality_metrics
from ads1292_studio.quality_gate import QualityGate, read_quality_gate_json, write_quality_gate_json
from ads1292_studio.report import export_review_report
from ads1292_studio.review_render import ReviewRenderFrame, build_review_render_frame
from ads1292_studio.session_index import export_session_index
from ads1292_studio.session_package import export_session_package, verify_session_package
from ads1292_studio.signal_processing import (
    pqrst_review,
)
from ads1292_studio.workers import LiveWorker


_T = TypeVar("_T")

MAX_POINTS = 10000
LIVE_MAX_RENDER_POINTS = 2500
MAX_SAMPLES_PER_TICK = 1000
MAX_LOG_MESSAGES_PER_TICK = 200
ACTIVE_TICK_INTERVAL_MS = 50
IDLE_TICK_INTERVAL_MS = 150
VISIBLE_SECONDS = 8.0
SAMPLE_RATE_HZ = 500.0
DEFAULT_FILTER_ENABLED = False
DEFAULT_ECG_INVERTED = False
DEFAULT_DISPLAY_SETTINGS = EcgDisplaySettings()
DEFAULT_FILTER_SETTINGS = SoftwareFilterSettings()
DISPLAY_SMOOTHING_WINDOW = 11
DISPLAY_MIN_ECG_SPAN_COUNTS = 8.0
DISPLAY_MIN_RESP_SPAN_COUNTS = 40.0


@dataclass(frozen=True)
class GuiStatusCard:
    label: str
    value: str
    tone: str


@dataclass(frozen=True)
class LiveQualityResult:
    generation: int
    source: str
    valid_rr: int
    samples: tuple[StreamSample, ...]
    status_values: tuple[int, ...]
    metrics: QualityMetrics | None = None
    error: str | None = None


@dataclass(frozen=True)
class ReviewRenderResult:
    generation: int
    samples: tuple[StreamSample, ...]
    frame: ReviewRenderFrame | None = None
    error: str | None = None


@dataclass(frozen=True)
class GuiState:
    connected: bool
    streaming: bool
    has_data: bool
    has_recording_path: bool
    loading_csv: bool = False
    connecting: bool = False
    starting: bool = False

    @property
    def busy(self) -> bool:
        return self.loading_csv or self.connecting or self.starting

    @property
    def package_ready(self) -> bool:
        return self.has_data and self.has_recording_path and not self.busy


@dataclass(frozen=True)
class CsvLoadResult:
    path: Path
    recording: Recording | None = None
    review_frame: ReviewRenderFrame | None = None
    display_settings: EcgDisplaySettings | None = None
    filter_settings: SoftwareFilterSettings | None = None
    error: str | None = None


@dataclass(frozen=True)
class ConnectResult:
    port: str
    detail: str | None = None
    error: str | None = None


def channel_map_cards() -> tuple[GuiStatusCard, ...]:
    return (
        GuiStatusCard("ECG", "CH2 Lead I (LA-RA)", "running"),
        GuiStatusCard("Respiration", "CH1 raw impedance", "neutral"),
        GuiStatusCard("Contact", "lead-off bits", "neutral"),
    )


def _gui_state(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
    loading_csv: bool = False,
    connecting: bool = False,
    starting: bool = False,
) -> GuiState:
    if state is not None:
        return state
    return GuiState(
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
        loading_csv=loading_csv,
        connecting=connecting,
        starting=starting,
    )


def should_apply_control_state(
    previous: GuiState | None,
    current: GuiState,
    *,
    force: bool = False,
) -> bool:
    return force or previous != current


def gui_tick_interval_ms(state: GuiState) -> int:
    return ACTIVE_TICK_INTERVAL_MS if state.streaming or state.busy else IDLE_TICK_INTERVAL_MS


def live_quality_worker_available(future: Future[LiveQualityResult] | None) -> bool:
    return future is None or future.done()


def gui_control_states(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
) -> dict[str, str]:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
    )
    if current.busy:
        return {
            "Refresh": tk.DISABLED,
            "Connect": tk.DISABLED,
            "Start": tk.DISABLED,
            "Stop": tk.NORMAL if current.streaming else tk.DISABLED,
            "Load CSV": tk.DISABLED,
            "Export Report": tk.DISABLED,
            "Export Package": tk.DISABLED,
            "Verify Package": tk.DISABLED,
            "Batch Compare": tk.DISABLED,
            "Session Index": tk.DISABLED,
        }
    return {
        "Refresh": tk.NORMAL,
        "Connect": tk.NORMAL,
        "Start": tk.NORMAL if current.connected and not current.streaming else tk.DISABLED,
        "Stop": tk.NORMAL if current.streaming else tk.DISABLED,
        "Load CSV": tk.NORMAL if not current.streaming else tk.DISABLED,
        "Export Report": tk.NORMAL if current.has_data else tk.DISABLED,
        "Export Package": tk.NORMAL if current.package_ready else tk.DISABLED,
        "Verify Package": tk.NORMAL,
        "Batch Compare": tk.NORMAL,
        "Session Index": tk.NORMAL,
    }


def gui_workflow_hint(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
) -> str:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
    )
    if current.connecting:
        return "Connecting: probing the selected port."
    if current.starting:
        return "Starting stream: waiting for the device to confirm."
    if current.loading_csv:
        return "Loading CSV: keep the window open; review plots will update when parsing finishes."
    if current.streaming:
        return "Streaming: monitor signal quality, add events if needed, then press Stop."
    if current.package_ready:
        return "Data ready: export a report or package the recording with its sidecars."
    if current.has_data:
        return "Data loaded: export a report; package export needs a saved CSV path."
    if current.connected:
        return "Next: press Start to begin acquisition, or load a CSV for offline review."
    return "Next: select an ADS1292 port and press Connect, or load an existing CSV."


def gui_status_overview(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
) -> str:
    cards = gui_status_cards(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
    )
    return "\n".join(f"{card.label}: {card.value}" for card in cards)


def live_ecg_axis_title(ecg_label: str, mode: str, *, inverted: bool) -> str:
    polarity = ", inverted" if inverted else ""
    return f"ECG display: {ecg_label} | {mode}{polarity}"


def live_axis_titles(
    *,
    ecg_label: str,
    resp_label: str,
    contact_label: str,
    mode: str,
    inverted: bool,
) -> tuple[str, str, str]:
    return (
        live_ecg_axis_title(ecg_label, mode, inverted=inverted),
        resp_label,
        contact_label,
    )


def live_metrics_text(
    *,
    sample_index: int,
    duration_seconds: float,
    ecg_label: str,
    heart_rate_bpm: float,
    peak_count: int,
) -> str:
    return (
        f"samples {sample_index} | duration {duration_seconds:.1f} s | "
        f"source {ecg_label} | HR {heart_rate_bpm:.0f} bpm | R peaks {peak_count}"
    )


def format_log_entries(messages: tuple[str, ...], stamp: str) -> str:
    return "".join(f"[{stamp}] {message}\n" for message in messages)


def display_refresh_key(
    *,
    mode: str,
    display_settings: EcgDisplaySettings,
    filter_settings: SoftwareFilterSettings,
    autoscale: bool,
    sample_index: int,
    loaded_count: int,
    recording_path: Path | None,
) -> tuple[object, ...]:
    return (
        mode,
        display_settings,
        filter_settings,
        bool(autoscale),
        int(sample_index),
        int(loaded_count),
        str(recording_path) if recording_path else "",
    )


def axis_limits_changed(
    current: tuple[float, float],
    target: tuple[float, float],
    *,
    tolerance: float = 1e-9,
) -> bool:
    return abs(float(current[0]) - float(target[0])) > tolerance or abs(float(current[1]) - float(target[1])) > tolerance


def set_axis_ylim_if_changed(ax: object, limits: tuple[float, float]) -> bool:
    target = (float(limits[0]), float(limits[1]))
    current = tuple(float(value) for value in ax.get_ylim())
    if not axis_limits_changed(current, target):
        return False
    ax.set_ylim(*target)
    return True


def toolbar_display_hint_text(settings: EcgDisplaySettings, filters: SoftwareFilterSettings) -> str:
    return f"CH2 Lead I | CH1 Resp | Contact | {display_mode_label(settings, filters)}"


def display_scale_reference_label(settings: EcgDisplaySettings) -> str:
    return f"Scale ref | {settings.normalized().gain:g}x"


def drain_queue_items(item_queue: queue.Queue[_T], max_items: int) -> tuple[_T, ...]:
    items: list[_T] = []
    for _ in range(max(0, max_items)):
        try:
            items.append(item_queue.get_nowait())
        except queue.Empty:
            break
    return tuple(items)


def header_connection_tone(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
    loading_csv: bool = False,
    connecting: bool = False,
    starting: bool = False,
) -> str:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
        loading_csv=loading_csv,
        connecting=connecting,
        starting=starting,
    )
    if current.connecting or current.starting or current.streaming or current.loading_csv:
        return "running"
    if current.connected:
        return "ready"
    return "warning"


def gui_status_cards(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
) -> tuple[GuiStatusCard, ...]:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
    )
    connection = GuiStatusCard(
        label="Connection",
        value="connected" if current.connected else "disconnected",
        tone="ready" if current.connected else "warning",
    )
    if current.connecting:
        acquisition_value = "connecting"
        acquisition_tone = "running"
    elif current.starting:
        acquisition_value = "starting stream"
        acquisition_tone = "running"
    elif current.loading_csv:
        acquisition_value = "loading CSV"
        acquisition_tone = "running"
    elif current.streaming:
        acquisition_value = "streaming"
        acquisition_tone = "running"
    elif current.connected:
        acquisition_value = "ready to start"
        acquisition_tone = "ready"
    else:
        acquisition_value = "idle"
        acquisition_tone = "neutral"
    data = GuiStatusCard(
        label="Data",
        value="loading CSV" if current.loading_csv else ("live or loaded" if current.has_data else "none loaded"),
        tone="running" if current.loading_csv else ("ready" if current.has_data else "neutral"),
    )
    if current.package_ready:
        package_value = "ready"
        package_tone = "ready"
    elif current.has_data:
        package_value = "needs saved CSV"
        package_tone = "warning"
    else:
        package_value = "unavailable"
        package_tone = "neutral"
    return (
        connection,
        GuiStatusCard("Acquisition", acquisition_value, acquisition_tone),
        data,
        GuiStatusCard("Package", package_value, package_tone),
    )


def compact_ecg_source_label(source: str | None) -> str:
    if source in {"CH1", "CH2"}:
        return source
    return "--"


def gui_signal_quality_cards(
    *,
    quality_label: str | None = None,
    ecg_source: str | None = None,
    contact_ok_percent: float | None = None,
    lead_off_bad_samples: int | None = None,
    r_peaks: int | None = None,
    hr_median_bpm: float | None = None,
    baseline_drift_counts: float | None = None,
    noise_rms_counts: float | None = None,
    peak_to_peak_counts: float | None = None,
) -> tuple[GuiStatusCard, ...]:
    if quality_label is None:
        return (
            GuiStatusCard("Signal", "not reviewed", "neutral"),
            GuiStatusCard("Contact", "--", "neutral"),
            GuiStatusCard("Heart rate", "--", "neutral"),
            GuiStatusCard("Artifacts", "--", "neutral"),
        )

    source = compact_ecg_source_label(ecg_source)
    contact = 0.0 if contact_ok_percent is None else contact_ok_percent
    bad_samples = 0 if lead_off_bad_samples is None else lead_off_bad_samples
    peak_count = 0 if r_peaks is None else r_peaks
    hr = 0.0 if hr_median_bpm is None else hr_median_bpm
    drift = 0.0 if baseline_drift_counts is None else baseline_drift_counts
    noise = 0.0 if noise_rms_counts is None else noise_rms_counts
    p2p = 0.0 if peak_to_peak_counts is None else peak_to_peak_counts

    signal_tone = "ready" if quality_label in {"Good ECG/QRS", "Usable ECG/QRS"} else "warning"
    contact_tone = "ready" if contact >= 95.0 else "warning"
    hr_tone = "ready" if peak_count >= 5 and 35.0 <= hr <= 180.0 else "warning"
    artifact_tone = "warning" if drift >= 250.0 or noise >= 150.0 else "neutral"
    hr_value = f"{hr:.1f}" if hr > 0 else "--"
    return (
        GuiStatusCard("Signal", f"{quality_label} | {source}", signal_tone),
        GuiStatusCard("Contact", f"{contact:.1f}% OK | {bad_samples} bad", contact_tone),
        GuiStatusCard("Heart rate", f"{hr_value} bpm | {peak_count} R", hr_tone),
        GuiStatusCard("Artifacts", f"drift {drift:.0f} | noise {noise:.1f} | p2p {p2p:.0f} ct", artifact_tone),
    )


def compute_live_quality_result(
    *,
    generation: int,
    source: str,
    valid_rr: int,
    ch1_values: tuple[float, ...],
    ch2_values: tuple[float, ...],
    status_values: tuple[int, ...],
) -> LiveQualityResult:
    try:
        samples = build_live_quality_samples(ch1_values, ch2_values, status_values)
        metrics = compute_quality_metrics(samples, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
    except Exception as exc:  # pragma: no cover - defensive worker boundary
        return LiveQualityResult(generation, source, valid_rr, tuple(), status_values, error=str(exc))
    return LiveQualityResult(generation, source, valid_rr, samples, status_values, metrics=metrics)


def compute_review_render_result(
    *,
    generation: int,
    samples: tuple[StreamSample, ...],
    display_settings: EcgDisplaySettings,
    filter_settings: SoftwareFilterSettings,
) -> ReviewRenderResult:
    try:
        frame = build_review_render_frame(
            samples,
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
    except Exception as exc:  # pragma: no cover - defensive worker boundary
        return ReviewRenderResult(generation=generation, samples=samples, error=str(exc))
    return ReviewRenderResult(generation=generation, samples=samples, frame=frame)


def build_live_quality_samples(
    ch1_values: tuple[float, ...],
    ch2_values: tuple[float, ...],
    status_values: tuple[int, ...],
) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(
            timestamp=index / SAMPLE_RATE_HZ,
            ch1=int(ch1),
            ch2=int(ch2),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=int(status),
        )
        for index, (ch1, ch2, status) in enumerate(zip(ch1_values, ch2_values, status_values))
    )


def set_string_var_if_changed(variable: tk.StringVar, value: str) -> bool:
    if variable.get() == value:
        return False
    variable.set(value)
    return True


def configure_widget_option_if_changed(widget: object, option: str, value: object) -> bool:
    if widget.cget(option) == value:
        return False
    widget.configure(**{option: value})
    return True


def apply_status_card_if_changed(
    *,
    variable: tk.StringVar,
    value_label: object,
    stripe: object,
    card: GuiStatusCard,
) -> bool:
    changed = set_string_var_if_changed(variable, card.value)
    style = status_tone_style(card.tone)
    if value_label.cget("style") != style:
        value_label.configure(style=style)
        changed = True
    color = status_tone_color(card.tone)
    if stripe.cget("bg") != color:
        stripe.configure(bg=color)
        changed = True
    return changed


def _mousewheel_units(event: tk.Event) -> int:
    if getattr(event, "num", None) == 4:
        return -1
    if getattr(event, "num", None) == 5:
        return 1
    delta = int(getattr(event, "delta", 0))
    if delta == 0:
        return 0
    return -1 if delta > 0 else 1


def _widget_exists(widget: tk.Widget) -> bool:
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        return False


def _unbind_mousewheel_events(widget: tk.Widget) -> None:
    for sequence in ScrollableFrame._mousewheel_events:
        try:
            widget.unbind_all(sequence)
        except tk.TclError:
            pass


class ScrollableFrame:
    _mousewheel_events = ("<MouseWheel>", "<Button-4>", "<Button-5>")
    _instances: list["ScrollableFrame"] = []
    _active_frame: "ScrollableFrame | None" = None
    _global_mousewheel_bound = False
    _global_mousewheel_widget: tk.Widget | None = None

    def __init__(self, parent: tk.Widget, width: int = 280) -> None:
        scrollbar_spec = scrollbar_chrome_spec()
        self.frame = ttk.Frame(parent)
        self.canvas = tk.Canvas(self.frame, width=width, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self.frame,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
            style=str(scrollbar_spec["vertical"]),
        )
        self.content = ttk.Frame(self.canvas, padding=10)
        self._content_window = self.canvas.create_window((0, 0), window=self.content, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._fit_content_width)
        self.canvas.bind("<Enter>", self._activate_mousewheel)
        self.content.bind("<Enter>", self._activate_mousewheel)
        self.canvas.bind("<Leave>", self._deactivate_mousewheel)
        self.frame.bind("<Destroy>", self._forget_instance, add="+")
        ScrollableFrame._instances.append(self)
        self._bind_global_mousewheel()

    def _bind_global_mousewheel(self) -> None:
        widget = ScrollableFrame._global_mousewheel_widget
        if ScrollableFrame._global_mousewheel_bound and widget is not None and _widget_exists(widget):
            return
        for sequence in ScrollableFrame._mousewheel_events:
            self.canvas.bind_all(sequence, self._dispatch_mousewheel)
        ScrollableFrame._global_mousewheel_bound = True
        ScrollableFrame._global_mousewheel_widget = self.canvas

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_content_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._content_window, width=event.width)

    def _activate_mousewheel(self, _event: tk.Event) -> None:
        ScrollableFrame._active_frame = self

    def _deactivate_mousewheel(self, event: tk.Event) -> None:
        if ScrollableFrame._active_frame is self and not self._contains_pointer(event):
            ScrollableFrame._active_frame = None

    def _forget_instance(self, event: tk.Event) -> None:
        if event.widget is not self.frame:
            return
        ScrollableFrame._instances = [instance for instance in ScrollableFrame._instances if instance is not self]
        if ScrollableFrame._active_frame is self:
            ScrollableFrame._active_frame = None
        if ScrollableFrame._global_mousewheel_widget is self.canvas:
            self._rebind_global_mousewheel()

    def _rebind_global_mousewheel(self) -> None:
        _unbind_mousewheel_events(self.canvas)
        ScrollableFrame._global_mousewheel_bound = False
        ScrollableFrame._global_mousewheel_widget = None
        if ScrollableFrame._instances:
            ScrollableFrame._instances[0]._bind_global_mousewheel()

    def _dispatch_mousewheel(self, event: tk.Event) -> None:
        target = self._mousewheel_target(event)
        if target is None:
            return
        target._scroll_mousewheel(event)

    def _mousewheel_target(self, event: tk.Event) -> "ScrollableFrame | None":
        active = ScrollableFrame._active_frame
        if active is not None and active._contains_pointer(event):
            return active
        return next((instance for instance in ScrollableFrame._instances if instance._contains_pointer(event)), None)

    def _scroll_mousewheel(self, event: tk.Event) -> None:
        units = _mousewheel_units(event)
        if units:
            self.canvas.yview_scroll(units, "units")

    def _contains_pointer(self, event: tk.Event) -> bool:
        x = int(getattr(event, "x_root", self.canvas.winfo_pointerx()))
        y = int(getattr(event, "y_root", self.canvas.winfo_pointery()))
        left = self.canvas.winfo_rootx()
        top = self.canvas.winfo_rooty()
        right = left + self.canvas.winfo_width()
        bottom = top + self.canvas.winfo_height()
        return left <= x <= right and top <= y <= bottom


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
        tokens = APP_VISUAL_TOKENS
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
        toolbar_frame = toolbar_frame_spec()
        style.configure(
            str(toolbar_frame["frame"]),
            background=toolbar_frame["background"],
            borderwidth=toolbar_frame["borderwidth"],
            relief=toolbar_frame["relief"],
        )
        style.configure(str(toolbar_frame["separator"]), background=toolbar_frame["separator_background"])
        style.configure(str(base_chrome["sidebar"]), background=base_chrome["background"])
        style.configure(str(base_chrome["main"]), background=base_chrome["background"])
        style.configure(
            str(base_chrome["label"]),
            background=base_chrome["background"],
            foreground=base_chrome["foreground"],
            borderwidth=base_chrome["borderwidth"],
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
        style.configure(
            "Connection.TLabel",
            background=connection_backgrounds["running"],
            foreground=connection_foregrounds["running"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        style.configure(
            "Ready.Connection.TLabel",
            background=connection_backgrounds["ready"],
            foreground=connection_foregrounds["ready"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        style.configure(
            "Running.Connection.TLabel",
            background=connection_backgrounds["running"],
            foreground=connection_foregrounds["running"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        style.configure(
            "Warning.Connection.TLabel",
            background=connection_backgrounds["warning"],
            foreground=connection_foregrounds["warning"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
        style.configure(
            "Neutral.Connection.TLabel",
            background=connection_backgrounds["neutral"],
            foreground=connection_foregrounds["neutral"],
            font=connection_pill["font"],
            padding=connection_pill["padding"],
            borderwidth=connection_pill["borderwidth"],
            relief=connection_pill["relief"],
        )
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
        panel_chrome = panel_chrome_spec()
        for panel_style in (
            "Card.TFrame",
            "PlotPanel.TFrame",
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
        workflow_hint = workflow_hint_styles()
        safety_notice = safety_notice_styles()
        for notice_style in (workflow_hint, safety_notice):
            style.configure(
                notice_style["frame"],
                background=notice_style["background"],
                borderwidth=panel_chrome["borderwidth"],
                relief=panel_chrome["relief"],
                bordercolor=panel_chrome["border"],
                lightcolor=panel_chrome["border"],
                darkcolor=panel_chrome["border"],
            )
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
        card_label = card_label_spec()
        style.configure(
            str(card_label["style"]),
            background=card_label["background"],
            foreground=card_label["foreground"],
            font=card_label["font"],
        )
        style.configure(
            workflow_hint["label"],
            background=workflow_hint["background"],
            foreground=workflow_hint["foreground"],
            font=workflow_hint["font"],
        )
        style.configure(
            safety_notice["label"],
            background=safety_notice["background"],
            foreground=safety_notice["foreground"],
            font=safety_notice["font"],
        )
        status_detail = status_detail_styles()
        style.configure(
            status_detail["label"],
            background=status_detail["background"],
            foreground=status_detail["label_foreground"],
            font=status_detail["label_font"],
        )
        style.configure(
            status_detail["value"],
            background=status_detail["background"],
            foreground=status_detail["value_foreground"],
            font=status_detail["value_font"],
        )
        event_count = event_count_styles()
        style.configure(
            event_count["label"],
            background=event_count["background"],
            foreground=event_count["label_foreground"],
            font=event_count["label_font"],
        )
        style.configure(
            event_count["value"],
            background=event_count["background"],
            foreground=event_count["value_foreground"],
            font=event_count["value_font"],
        )
        protocol_note = protocol_note_styles()
        style.configure(
            protocol_note["label"],
            background=protocol_note["background"],
            foreground=protocol_note["label_foreground"],
            font=protocol_note["label_font"],
        )
        style.configure(
            protocol_note["value"],
            background=protocol_note["background"],
            foreground=protocol_note["value_foreground"],
            font=protocol_note["value_font"],
        )
        button_chrome = button_chrome_spec()
        default_button = button_chrome["default"]
        style.configure(
            "TButton",
            padding=default_button["padding"],
            font=default_button["font"],
            foreground=default_button["foreground"],
            background=default_button["background"],
            borderwidth=default_button["borderwidth"],
            relief=default_button["relief"],
        )
        style.map(
            "TButton",
            foreground=[
                ("disabled", default_button["disabled_foreground"]),
                ("active", default_button["active_foreground"]),
            ],
            background=[
                ("disabled", default_button["disabled_background"]),
                ("active", default_button["active_background"]),
            ],
        )
        sidebar_button = button_chrome["sidebar"]
        style.configure(
            "SidebarAction.TButton",
            padding=sidebar_button["padding"],
            font=sidebar_button["font"],
            foreground=sidebar_button["foreground"],
            background=sidebar_button["background"],
            borderwidth=sidebar_button["borderwidth"],
            relief=sidebar_button["relief"],
        )
        style.map(
            "SidebarAction.TButton",
            foreground=[
                ("disabled", sidebar_button["disabled_foreground"]),
                ("active", sidebar_button["active_foreground"]),
            ],
            background=[
                ("disabled", sidebar_button["disabled_background"]),
                ("active", sidebar_button["active_background"]),
            ],
        )
        primary_button = button_chrome["primary"]
        style.configure(
            "Primary.TButton",
            padding=primary_button["padding"],
            font=primary_button["font"],
            foreground=primary_button["foreground"],
            background=primary_button["background"],
            borderwidth=primary_button["borderwidth"],
            relief=primary_button["relief"],
        )
        style.map(
            "Primary.TButton",
            foreground=[
                ("disabled", primary_button["disabled_foreground"]),
                ("active", primary_button["active_foreground"]),
            ],
            background=[
                ("disabled", primary_button["disabled_background"]),
                ("active", primary_button["active_background"]),
            ],
        )
        stop_button = button_chrome["stop"]
        style.configure(
            "Stop.TButton",
            padding=stop_button["padding"],
            font=stop_button["font"],
            foreground=stop_button["foreground"],
            background=stop_button["background"],
            borderwidth=stop_button["borderwidth"],
            relief=stop_button["relief"],
        )
        style.map(
            "Stop.TButton",
            foreground=[
                ("disabled", stop_button["disabled_foreground"]),
                ("active", stop_button["active_foreground"]),
            ],
            background=[
                ("disabled", stop_button["disabled_background"]),
                ("active", stop_button["active_background"]),
            ],
        )
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
        sidebar_tabs = sidebar_notebook_styles()
        style.configure(
            "Sidebar.TNotebook",
            background=sidebar_tabs["background"],
            borderwidth=sidebar_tabs["borderwidth"],
        )
        style.configure(
            "Sidebar.TNotebook.Tab",
            padding=sidebar_tabs["tab_padding"],
            font=sidebar_tabs["tab_font"],
            foreground=sidebar_tabs["inactive_foreground"],
            background=sidebar_tabs["tab_background"],
            borderwidth=sidebar_tabs["tab_borderwidth"],
            relief=sidebar_tabs["tab_relief"],
        )
        style.map(
            "Sidebar.TNotebook.Tab",
            foreground=[
                ("selected", sidebar_tabs["selected_foreground"]),
                ("active", sidebar_tabs["active_foreground"]),
            ],
            background=[
                ("selected", sidebar_tabs["active_background"]),
                ("active", sidebar_tabs["active_background"]),
            ],
        )
        workspace_tabs = workspace_notebook_styles()
        style.configure(
            "Workspace.TNotebook",
            background=workspace_tabs["background"],
            borderwidth=workspace_tabs["borderwidth"],
        )
        style.configure(
            "Workspace.TNotebook.Tab",
            padding=workspace_tabs["tab_padding"],
            font=workspace_tabs["tab_font"],
            foreground=workspace_tabs["inactive_foreground"],
            background=workspace_tabs["tab_background"],
            borderwidth=workspace_tabs["tab_borderwidth"],
            relief=workspace_tabs["tab_relief"],
        )
        style.map(
            "Workspace.TNotebook.Tab",
            foreground=[
                ("selected", workspace_tabs["selected_foreground"]),
                ("active", workspace_tabs["active_foreground"]),
            ],
            background=[
                ("selected", workspace_tabs["active_background"]),
                ("active", workspace_tabs["active_background"]),
            ],
        )
        status_label = status_label_spec()
        status_backgrounds = status_label["backgrounds"]
        status_foregrounds = status_label["foregrounds"]
        style.configure(
            "Ready.Status.TLabel",
            background=status_backgrounds["ready"],
            foreground=status_foregrounds["ready"],
            font=status_label["font"],
            padding=status_label["padding"],
        )
        style.configure(
            "Running.Status.TLabel",
            background=status_backgrounds["running"],
            foreground=status_foregrounds["running"],
            font=status_label["font"],
            padding=status_label["padding"],
        )
        style.configure(
            "Warning.Status.TLabel",
            background=status_backgrounds["warning"],
            foreground=status_foregrounds["warning"],
            font=status_label["font"],
            padding=status_label["padding"],
        )
        style.configure(
            "Neutral.Status.TLabel",
            background=status_backgrounds["neutral"],
            foreground=status_foregrounds["neutral"],
            font=status_label["font"],
            padding=status_label["padding"],
        )

    def _build_workflow_hint(self, parent: ttk.Frame) -> None:
        styles = workflow_hint_styles()
        spec = sidebar_text_card_spec()
        self.workflow_hint_frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        self.workflow_hint_frame.pack(anchor=tk.W, fill=tk.X, pady=(0, 4))
        self.workflow_hint_stripe = tk.Frame(
            self.workflow_hint_frame,
            width=spec["stripe_width"],
            bg=styles["stripe"],
            highlightthickness=0,
        )
        self.workflow_hint_stripe.pack(side=tk.LEFT, fill=tk.Y)
        self.workflow_hint_label = ttk.Label(
            self.workflow_hint_frame,
            textvariable=self.workflow_hint_var,
            wraplength=spec["primary_wrap"],
            justify=tk.LEFT,
            style=styles["label"],
            padding=spec["label_padding"],
        )
        self.workflow_hint_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_safety_notice(self, parent: ttk.Frame) -> None:
        styles = safety_notice_styles()
        spec = sidebar_text_card_spec()
        self.safety_notice_frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        self.safety_notice_frame.pack(anchor=tk.W, fill=tk.X, pady=(0, 4))
        self.safety_notice_stripe = tk.Frame(
            self.safety_notice_frame,
            width=spec["stripe_width"],
            bg=styles["stripe"],
            highlightthickness=0,
        )
        self.safety_notice_stripe.pack(side=tk.LEFT, fill=tk.Y)
        self.safety_notice_label = ttk.Label(
            self.safety_notice_frame,
            text="Research use only. Use battery power during human-subject measurements.",
            wraplength=spec["primary_wrap"],
            justify=tk.LEFT,
            style=styles["label"],
            padding=spec["label_padding"],
        )
        self.safety_notice_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _build_toolbar_hint_chip(self, parent: ttk.Frame, variable: tk.StringVar) -> None:
        styles = toolbar_hint_styles()
        self.toolbar_hint_chip = ttk.Frame(
            parent,
            padding=toolbar_layout_spec()["hint_padding"],
            style=styles["frame"],
        )
        self.toolbar_hint_chip.pack(side=tk.LEFT)
        self.toolbar_hint_label = ttk.Label(self.toolbar_hint_chip, textvariable=variable, style=styles["label"])
        self.toolbar_hint_label.pack(side=tk.LEFT)

    def _build_action_section_heading(self, parent: ttk.Frame, text: str, *, top_padding: int = 14) -> None:
        styles = action_section_styles()
        frame = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        frame.pack(anchor=tk.W, fill=tk.X, pady=(top_padding, 4))
        label = ttk.Label(frame, text=text, style=styles["label"])
        label.pack(anchor=tk.W)
        self.action_section_labels[text] = label

    def _build_status_detail_card(self, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
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
        self.status_detail_value_labels[label] = value_label

    def _build_event_count_card(self, parent: ttk.Frame) -> None:
        styles = event_count_styles()
        spec = sidebar_text_card_spec()
        row = ttk.Frame(parent, padding=(0, 0), style=styles["frame"])
        row.pack(anchor=tk.W, fill=tk.X, pady=(7, 2))
        stripe = tk.Frame(row, width=spec["stripe_width"], bg=styles["stripe"], highlightthickness=0)
        stripe.pack(side=tk.LEFT, fill=tk.Y)
        content = ttk.Frame(row, padding=spec["content_padding"], style=styles["frame"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Label(content, text="Event markers", style=styles["label"]).pack(anchor=tk.W)
        self.event_count_label = ttk.Label(
            content,
            textvariable=self.event_count_var,
            wraplength=spec["detail_wrap"],
            justify=tk.LEFT,
            style=styles["value"],
        )
        self.event_count_label.pack(anchor=tk.W, fill=tk.X, pady=spec["value_top_padding"])

    def _build_protocol_note_card(self, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
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
        self.protocol_note_labels[label] = value_label

    def _build_status_cards(self, parent: ttk.Frame) -> None:
        card_label = card_label_spec()
        for label in STATUS_CARD_LABELS:
            row = ttk.Frame(parent, padding=(0, 0), style="Card.TFrame")
            row.pack(anchor=tk.W, fill=tk.X, pady=card_label["row_padding"])
            stripe = tk.Frame(
                row,
                width=int(card_label["stripe_width"]),
                bg=status_tone_color("neutral"),
                highlightthickness=0,
            )
            stripe.pack(side=tk.LEFT, fill=tk.Y)
            content = ttk.Frame(row, padding=card_label["content_padding"], style="Card.TFrame")
            content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            label_widget = ttk.Label(content, text=label, width=int(card_label["width"]), style=str(card_label["style"]))
            label_widget.pack(side=tk.LEFT)
            value_label = ttk.Label(
                content,
                textvariable=self.status_card_vars[label],
                style=status_tone_style("neutral"),
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=card_label["value_padding"])
            self.status_card_label_widgets[label] = label_widget
            self.status_card_tone_stripes[label] = stripe
            self.status_card_value_labels[label] = value_label

    def _build_channel_map_cards(self, parent: ttk.Frame) -> None:
        card_label = card_label_spec()
        for card in channel_map_cards():
            row = ttk.Frame(parent, padding=(0, 0), style="Card.TFrame")
            row.pack(anchor=tk.W, fill=tk.X, pady=card_label["row_padding"])
            stripe = tk.Frame(
                row,
                width=int(card_label["stripe_width"]),
                bg=status_tone_color(card.tone),
                highlightthickness=0,
            )
            stripe.pack(side=tk.LEFT, fill=tk.Y)
            content = ttk.Frame(row, padding=card_label["content_padding"], style="Card.TFrame")
            content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
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
            self.channel_map_label_widgets[card.label] = label_widget
            self.channel_map_tone_stripes[card.label] = stripe
            self.channel_map_value_labels[card.label] = value_label

    def _build_signal_quality_cards(self, parent: ttk.Frame) -> None:
        card_label = card_label_spec()
        for label in SIGNAL_CARD_LABELS:
            row = ttk.Frame(parent, padding=(0, 0), style="Card.TFrame")
            row.pack(anchor=tk.W, fill=tk.X, pady=card_label["row_padding"])
            stripe = tk.Frame(
                row,
                width=int(card_label["stripe_width"]),
                bg=status_tone_color("neutral"),
                highlightthickness=0,
            )
            stripe.pack(side=tk.LEFT, fill=tk.Y)
            content = ttk.Frame(row, padding=card_label["content_padding"], style="Card.TFrame")
            content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            label_widget = ttk.Label(content, text=label, width=int(card_label["width"]), style=str(card_label["style"]))
            label_widget.pack(side=tk.LEFT)
            value_label = ttk.Label(
                content,
                textvariable=self.signal_card_vars[label],
                style=status_tone_style("neutral"),
                wraplength=card_label["signal_value_wrap"],
                justify=tk.LEFT,
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=card_label["value_padding"])
            self.signal_card_label_widgets[label] = label_widget
            self.signal_card_tone_stripes[label] = stripe
            self.signal_card_value_labels[label] = value_label

    def _build_sidebar(self, parent: ttk.Frame) -> dict[str, ttk.Frame]:
        spec = sidebar_layout_spec()
        self.sidebar_notebook = ttk.Notebook(parent, style=sidebar_notebook_styles()["notebook"])
        self.sidebar_notebook.pack(fill=tk.BOTH, expand=True)
        self.sidebar_scrolls: dict[str, ScrollableFrame] = {}
        sections: dict[str, ttk.Frame] = {}
        for label in SIDEBAR_TABS:
            tab = ttk.Frame(self.sidebar_notebook)
            scroll = ScrollableFrame(tab, width=int(spec["scroll_width"]))
            scroll.frame.pack(fill=tk.BOTH, expand=True)
            self.sidebar_notebook.add(tab, text=label)
            self.sidebar_scrolls[label] = scroll
            sections[label] = scroll.content
        return sections

    def _metadata_entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
        styles = sidebar_field_styles()
        ttk.Label(parent, text=label, style=styles["label"]).pack(anchor=tk.W, pady=(8, 2))
        ttk.Entry(parent, textvariable=variable, style=styles["entry"]).pack(anchor=tk.W, fill=tk.X)

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
        if values and not self.port_var.get():
            self.port_var.set(values[0])
        if not values:
            self.connection_var.set("No ADS1x9x port")

    def connect(self) -> None:
        port = self.port_var.get().strip()
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
        port = self.port_var.get().strip()
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
        return GuiState(
            connected=self.connected_port is not None,
            streaming=self.is_streaming,
            has_data=bool(self.loaded_samples or (self.ch1 and self.ch2)),
            has_recording_path=self.recording_path is not None,
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
        for label, button in self.control_buttons.items():
            configure_widget_option_if_changed(button, "state", states[label])

    def _apply_signal_quality_cards(self, cards: tuple[GuiStatusCard, ...]) -> None:
        for card in cards:
            apply_status_card_if_changed(
                variable=self.signal_card_vars[card.label],
                value_label=self.signal_card_value_labels[card.label],
                stripe=self.signal_card_tone_stripes[card.label],
                card=card,
            )

    def _metadata(self) -> SessionMetadata:
        return SessionMetadata(
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
        return Calibration(
            vref_mv=_float_from_var(self.vref_mv_var, 2420.0),
            pga_gain=_float_from_var(self.pga_gain_var, 6.0),
            adc_bits=24,
            label=self.calibration_label_var.get(),
        ).normalized()

    def _protocol(self) -> TestProtocol:
        return TestProtocol(
            name=self.protocol_name_var.get(),
            objective=self.protocol_objective_var.get(),
            operator_instructions="Follow the listed protocol steps.",
            steps=_parse_protocol_steps(self.protocol_steps_var.get()),
            acceptance_notes=self.protocol_acceptance_var.get(),
        ).normalized()

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
        latest = sample_batch[-1] if sample_batch else None
        for sample in sample_batch:
            self._append_sample(sample)
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
        if not live_quality_worker_available(self.live_quality_future):
            return
        ch1_values = tuple(self.ch1)
        ch2_values = tuple(self.ch2)
        status_values = tuple(self.status)
        self.live_quality_generation += 1
        generation = self.live_quality_generation
        future = self.live_quality_executor.submit(
            compute_live_quality_result,
            generation=generation,
            source=source,
            valid_rr=valid_rr,
            ch1_values=ch1_values,
            ch2_values=ch2_values,
            status_values=status_values,
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
        if self.review_render_future is not None and not self.review_render_future.done():
            self.review_render_generation += 1
            self.pending_review_render_samples = samples
            return False
        self.review_render_generation += 1
        generation = self.review_render_generation
        self.pending_review_render_samples = None
        display_settings = self._display_settings()
        filter_settings = self._software_filter_settings()
        future = self.review_render_executor.submit(
            compute_review_render_result,
            generation=generation,
            samples=samples,
            display_settings=display_settings,
            filter_settings=filter_settings,
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
        latest: ReviewRenderResult | None = None
        while True:
            try:
                result = self.review_render_results.get_nowait()
            except queue.Empty:
                break
            if result.generation == self.review_render_generation:
                latest = result
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
        if self.pending_review_render_samples is None:
            return
        if self.review_render_future is not None and not self.review_render_future.done():
            return
        samples = self.pending_review_render_samples
        self.pending_review_render_samples = None
        self._schedule_review_render_update(samples)

    def _drain_live_quality_results(self) -> None:
        latest: LiveQualityResult | None = None
        while True:
            try:
                result = self.live_quality_results.get_nowait()
            except queue.Empty:
                break
            if result.generation == self.live_quality_generation:
                latest = result
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

    def _append_sample(self, sample: StreamSample) -> None:
        self.indices.append(self.sample_index)
        self.sample_index += 1
        self.ch1.append(sample.ch1)
        self.ch2.append(sample.ch2)
        self.status.append(sample.lead_off_bits)
        self.board_hr.append(sample.board_heart_rate)
        self.board_rr.append(sample.board_respiration_rate)

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

    def _apply_ecg_paper_grid(self, ax: object, settings: EcgDisplaySettings) -> None:
        spec = ecg_paper_grid_spec(settings)
        cache_key = ecg_paper_grid_key(settings, ax.get_ylim())
        axis_id = id(ax)
        if self.ecg_paper_grid_cache.get(axis_id) == cache_key:
            return
        self.ecg_paper_grid_cache[axis_id] = cache_key
        ax.xaxis.set_major_locator(MultipleLocator(float(spec["major_x_seconds"])))
        ax.xaxis.set_minor_locator(MultipleLocator(float(spec["minor_x_seconds"])))
        _, _, major_y, minor_y = cache_key
        ax.yaxis.set_major_locator(MultipleLocator(major_y))
        ax.yaxis.set_minor_locator(MultipleLocator(minor_y))
        ax.grid(
            True,
            which="major",
            color=spec["major_color"],
            linewidth=spec["major_linewidth"],
            alpha=spec["major_alpha"],
        )
        ax.grid(
            True,
            which="minor",
            color=spec["minor_color"],
            linewidth=spec["minor_linewidth"],
            alpha=spec["minor_alpha"],
        )

    def _draw_calibration_pulse(
        self,
        ax: object,
        artists: list[object],
        settings: EcgDisplaySettings,
    ) -> None:
        axis_id = id(ax)
        label_text = display_scale_reference_label(settings)
        if artists and self.calibration_pulse_cache.get(axis_id) == label_text:
            return
        if len(artists) >= 2 and hasattr(artists[1], "set_text"):
            artists[1].set_text(label_text)
            self.calibration_pulse_cache[axis_id] = label_text
            return
        for artist in artists:
            artist.remove()
        artists.clear()
        line, = ax.plot(
            [0.025, 0.025, 0.07, 0.07, 0.105],
            [0.12, 0.30, 0.30, 0.12, 0.12],
            transform=ax.transAxes,
            color=PLOT_TRACE_COLORS["peak"],
            linewidth=1.25,
            solid_capstyle="butt",
            clip_on=False,
        )
        label = ax.text(
            0.115,
            0.30,
            label_text,
            transform=ax.transAxes,
            color=APP_VISUAL_TOKENS["muted"],
            fontsize=8,
            va="center",
            ha="left",
            clip_on=False,
        )
        artists.extend((line, label))
        self.calibration_pulse_cache[axis_id] = label_text

    def _apply_live_axis_titles(
        self,
        display_settings: EcgDisplaySettings,
        filter_settings: SoftwareFilterSettings,
    ) -> None:
        ecg_label, resp_label, contact_label = ads1292r_plot_layout_labels()
        mode = f"{display_mode_label(display_settings, filter_settings)}, display-smoothed"
        titles = live_axis_titles(
            ecg_label=ecg_label,
            resp_label=resp_label,
            contact_label=contact_label,
            mode=mode,
            inverted=DEFAULT_ECG_INVERTED,
        )
        if self.last_live_axis_titles == titles:
            return
        self.last_live_axis_titles = titles
        ecg_title, resp_title, contact_title = titles
        set_signal_axis_title(self.ax_live_ecg, ecg_title)
        set_signal_axis_title(self.ax_live_resp, resp_title)
        set_signal_axis_title(self.ax_live_status, contact_title)

    def _redraw_live(self) -> None:
        if not self.indices:
            return
        self._clear_empty_plot_state()
        display_settings = self._display_settings()
        filter_settings = self._software_filter_settings()
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

        self.live_ecg_line.set_data(frame.plot_ecg_x, frame.plot_ecg)
        self.live_peak_line.set_data(frame.peaks_x, frame.peaks_y)
        self.live_resp_line.set_data(frame.plot_resp_x, frame.plot_resp)
        self.live_status_line.set_data(frame.plot_status_x, frame.plot_status)
        for ax in (self.ax_live_ecg, self.ax_live_resp, self.ax_live_status):
            ax.set_xlim(frame.left, frame.right)
        if self.autoscale_var.get():
            ecg_ylim = robust_ylim(frame.visible_ecg_plot, min_span=DISPLAY_MIN_ECG_SPAN_COUNTS * display_settings.gain)
            resp_ylim = robust_ylim(frame.visible_resp_plot, min_span=DISPLAY_MIN_RESP_SPAN_COUNTS)
            set_axis_ylim_if_changed(self.ax_live_ecg, stable_ylim(self.ax_live_ecg.get_ylim(), ecg_ylim))
            set_axis_ylim_if_changed(self.ax_live_resp, stable_ylim(self.ax_live_resp.get_ylim(), resp_ylim))
            status_top = float(frame.visible_status.max()) + 0.5 if frame.visible_status.size else 1.0
            set_axis_ylim_if_changed(self.ax_live_status, (-0.5, max(1.0, status_top)))
        self._apply_ecg_paper_grid(self.ax_live_ecg, display_settings)
        self._draw_calibration_pulse(self.ax_live_ecg, self.live_calibration_artists, display_settings)
        ecg_label = ads1292r_plot_layout_labels()[0]
        self._apply_live_axis_titles(display_settings, filter_settings)
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
        self.live_canvas.draw_idle()

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
        self.review_ecg_line.set_data(frame.plot_ecg_x, frame.plot_ecg)
        self.review_resp_line.set_data(frame.plot_resp_x, frame.plot_resp)
        self.review_status_line.set_data(frame.plot_status_x, frame.plot_status)
        self.review_peak_line.set_data(frame.peak_x, frame.peak_y)
        polarity = ", inverted" if DEFAULT_ECG_INVERTED else ""
        set_signal_axis_title(
            self.ax_review_ecg,
            f"Offline ECG: {ecg_label} | {frame.mode}{polarity} | "
            f"HR {frame.review.heart_rate.median_bpm:.1f} bpm | peaks {len(frame.review.peaks)}",
        )
        set_signal_axis_title(self.ax_review_resp, resp_label)
        set_signal_axis_title(self.ax_review_status, contact_label)
        self.ax_review_ecg.set_xlim(0, frame.x_right)
        self.ax_review_ecg.set_ylim(*frame.ecg_ylim)
        self.ax_review_resp.set_xlim(0, frame.x_right)
        self.ax_review_resp.set_ylim(*frame.resp_ylim)
        self.ax_review_status.set_xlim(0, frame.x_right)
        self.ax_review_status.set_ylim(*frame.status_ylim)
        self.ax_review_status.set_xlabel("Time (s)")
        self._apply_ecg_paper_grid(self.ax_review_ecg, display_settings)
        self._draw_calibration_pulse(self.ax_review_ecg, self.review_calibration_artists, display_settings)
        self.review_canvas.draw_idle()
        self._draw_pqrst_review(frame.pqrst)
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

    def _draw_pqrst(self, ecg: np.ndarray, peaks: tuple[int, ...]) -> None:
        self._draw_pqrst_review(pqrst_review(ecg, peaks, SAMPLE_RATE_HZ))

    def _draw_pqrst_review(self, review: PqrstReview) -> None:
        self.ax_pqrst.clear()
        style_signal_axes((self.ax_pqrst,))
        self.ax_pqrst.set_xlabel("Time relative to R peak (ms)")
        self.ax_pqrst.set_ylabel("Filtered counts")
        if review.average_beat:
            pqrst_style = pqrst_plot_style()
            self.ax_pqrst.plot(
                review.time_ms,
                review.average_beat,
                color=PLOT_TRACE_COLORS["ecg"],
                **pqrst_style["average"],
            )
            self.ax_pqrst.axvline(
                0,
                color=PLOT_TRACE_COLORS["peak"],
                **pqrst_style["r_marker"],
            )
            p_search = pqrst_style["p_search"]
            self.ax_pqrst.axvspan(
                p_search["start_ms"],
                p_search["end_ms"],
                color=p_search["color"],
                alpha=p_search["alpha"],
                label=p_search["label"],
            )
            t_search = pqrst_style["t_search"]
            self.ax_pqrst.axvspan(
                t_search["start_ms"],
                t_search["end_ms"],
                color=t_search["color"],
                alpha=t_search["alpha"],
                label=t_search["label"],
            )
            self.ax_pqrst.legend(**pqrst_style["legend"])
        set_signal_axis_title(
            self.ax_pqrst,
            f"PQRST review: QRS={review.qrs_clear}, P tentative={review.p_tentative}, "
            f"T tentative={review.t_tentative}, beats={review.beats_used}",
        )
        self.pqrst_canvas.draw_idle()

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
        if not messages:
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, format_log_entries(messages, stamp))
        self._trim_log_text()
        self.log_text.see(tk.END)

    def _trim_log_text(self) -> None:
        max_lines = int(log_panel_spec()["max_lines"])
        line_count = int(self.log_text.index("end-1c").split(".", maxsplit=1)[0])
        if line_count <= max_lines:
            return
        self.log_text.delete("1.0", f"{line_count - max_lines + 1}.0")

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


def _float_from_var(variable: tk.StringVar, fallback: float) -> float:
    try:
        return float(variable.get())
    except ValueError:
        return fallback


def _quality_gate_from_values(values: dict[str, object]) -> QualityGate:
    return QualityGate(
        min_duration_seconds=_float_value(values.get("min_duration_seconds"), 8.0),
        min_contact_ok_percent=_float_value(values.get("min_contact_ok_percent"), 95.0),
        min_r_peaks=_int_value(values.get("min_r_peaks"), 5),
        min_hr_bpm=_float_value(values.get("min_hr_bpm"), 35.0),
        max_hr_bpm=_float_value(values.get("max_hr_bpm"), 180.0),
        require_qrs_clear=bool(values.get("require_qrs_clear", True)),
        max_baseline_drift_counts=_optional_float_value(values.get("max_baseline_drift_counts")),
        max_noise_rms_counts=_optional_float_value(values.get("max_noise_rms_counts")),
        max_peak_to_peak_counts=_optional_float_value(values.get("max_peak_to_peak_counts")),
    ).normalized()


def _quality_gate_to_values(gate: QualityGate) -> dict[str, object]:
    normalized = gate.normalized()
    return {
        "min_duration_seconds": _format_number(normalized.min_duration_seconds),
        "min_contact_ok_percent": _format_number(normalized.min_contact_ok_percent),
        "min_r_peaks": str(normalized.min_r_peaks),
        "min_hr_bpm": _format_number(normalized.min_hr_bpm),
        "max_hr_bpm": _format_number(normalized.max_hr_bpm),
        "require_qrs_clear": normalized.require_qrs_clear,
        "max_baseline_drift_counts": _format_optional_number(normalized.max_baseline_drift_counts),
        "max_noise_rms_counts": _format_optional_number(normalized.max_noise_rms_counts),
        "max_peak_to_peak_counts": _format_optional_number(normalized.max_peak_to_peak_counts),
    }


def _float_value(value: object, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _int_value(value: object, fallback: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _optional_float_value(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    return f"{value:g}"


def _format_optional_number(value: float | None) -> str:
    return "" if value is None else _format_number(value)


def _format_protocol_steps(steps: tuple[ProtocolStep, ...]) -> str:
    return "; ".join(
        f"{step.start_seconds:g},{step.duration_seconds:g},{step.label},{step.instruction}" for step in steps
    )


def _parse_protocol_steps(text: str) -> tuple[ProtocolStep, ...]:
    steps: list[ProtocolStep] = []
    for chunk in text.split(";"):
        parts = [part.strip() for part in chunk.split(",", 3)]
        if len(parts) != 4:
            continue
        try:
            start = float(parts[0])
            duration = float(parts[1])
        except ValueError:
            continue
        steps.append(ProtocolStep(start, duration, parts[2], parts[3]).normalized())
    if steps:
        return tuple(steps)
    return protocol_template().steps


if __name__ == "__main__":
    main()
