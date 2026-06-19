from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
import tempfile
from tkinter import filedialog, messagebox, ttk

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ads1292-studio-matplotlib"))

import matplotlib
import numpy as np

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from ads1292_studio.batch import export_batch_summary
from ads1292_studio.calibration import Calibration, read_calibration_json, write_calibration_json
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.device import Ads1x9xDevice, find_ads_port, list_ads_ports
from ads1292_studio.events import EventMarker, read_events_json, write_events_json
from ads1292_studio.gui_quality import build_quality_text, protocol_ready_for_live_quality
from ads1292_studio.gui_session_index import build_session_index_message
from ads1292_studio.macos_stderr import install_macos_stderr_filter
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import Recording, StreamSample, StreamStartResult
from ads1292_studio.plots import decimate_for_plot, robust_ylim
from ads1292_studio.protocol import ProtocolStep, TestProtocol, protocol_template, read_protocol_json, write_protocol_json
from ads1292_studio.quality import compute_quality_metrics
from ads1292_studio.quality_gate import QualityGate, read_quality_gate_json, write_quality_gate_json
from ads1292_studio.report import export_review_report
from ads1292_studio.session_index import export_session_index
from ads1292_studio.session_package import export_session_package, verify_session_package
from ads1292_studio.signal_processing import (
    bandpass,
    detect_r_peaks,
    heart_rate_summary,
    pqrst_review,
    review_channels,
)
from ads1292_studio.workers import LiveWorker


MAX_POINTS = 5000
VISIBLE_SECONDS = 8.0
SAMPLE_RATE_HZ = 500.0
DEFAULT_FILTER_ENABLED = False
DEFAULT_ECG_INVERTED = False
PRIMARY_TOOLBAR_BUTTONS = ("Refresh", "Connect", "Start", "Stop")
SECONDARY_ACTION_BUTTONS = (
    "Load CSV",
    "Export Report",
    "Export Package",
    "Verify Package",
    "Batch Compare",
    "Session Index",
)
SIDEBAR_TABS = ("Status", "Session", "Validation", "Protocol", "Actions")
STATUS_CARD_LABELS = ("Connection", "Acquisition", "Data", "Package")
SIGNAL_CARD_LABELS = ("Signal", "Contact", "Heart rate", "Artifacts")
ADS1292R_ECG_SOURCE = "CH2"
ADS1292R_CHANNEL_LABELS = {
    "CH2": "CH2 ECG Lead I (LA-RA)",
    "CH1": "CH1 Respiration raw",
}
ADS1292R_PLOT_LAYOUT_LABELS = (
    "CH2 ECG Lead I (LA-RA)",
    "CH1 Respiration raw",
    "Lead-off / contact status",
)
STATUS_TONE_STYLES = {
    "ready": "Ready.Status.TLabel",
    "running": "Running.Status.TLabel",
    "warning": "Warning.Status.TLabel",
    "neutral": "Neutral.Status.TLabel",
}
APP_VISUAL_TOKENS = {
    "surface": "#F6F8FB",
    "panel": "#FFFFFF",
    "panel_alt": "#EEF3FA",
    "ink": "#172033",
    "muted": "#657084",
    "border": "#D9E1EC",
    "accent": "#2F6FED",
    "accent_dark": "#1F4FB2",
    "success": "#1E7A46",
    "warning": "#A76400",
    "danger": "#B3261E",
}
PLOT_TRACE_COLORS = {
    "ecg": "#2F6FED",
    "respiration": "#7A5CDB",
    "contact": "#516070",
    "peak": "#E34A4A",
}
EMPTY_PLOT_MESSAGES = {
    "live": (
        "Connect an ADS1292 board, then press Start",
        "CH1 respiration/contact context appears here",
        "Lead-off status stays at 0 when contacts are good",
    ),
    "review": (
        "Load a CSV to review recorded ECG",
        "CH1 respiration/contact context appears here",
        "Lead-off/contact status appears here",
    ),
    "pqrst": ("Load or record data to build the averaged PQRST beat",),
}


@dataclass(frozen=True)
class GuiStatusCard:
    label: str
    value: str
    tone: str


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
    error: str | None = None


@dataclass(frozen=True)
class ConnectResult:
    port: str
    detail: str | None = None
    error: str | None = None


def status_tone_style(tone: str) -> str:
    return STATUS_TONE_STYLES.get(tone, STATUS_TONE_STYLES["neutral"])


def app_visual_tokens() -> dict[str, str]:
    return dict(APP_VISUAL_TOKENS)


def plot_trace_colors() -> dict[str, str]:
    return dict(PLOT_TRACE_COLORS)


def empty_plot_messages() -> dict[str, tuple[str, ...]]:
    return dict(EMPTY_PLOT_MESSAGES)


def ads1292r_channel_label(channel: str) -> str:
    return ADS1292R_CHANNEL_LABELS.get(channel.upper(), channel)


def ads1292r_secondary_channel_label(ecg_source: str) -> str:
    return "CH1 Respiration raw" if ecg_source.upper() == "CH2" else "CH2 ECG Lead I (LA-RA)"


def ads1292r_plot_layout_labels() -> tuple[str, str, str]:
    return ADS1292R_PLOT_LAYOUT_LABELS


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


def primary_toolbar_button_labels() -> tuple[str, ...]:
    return PRIMARY_TOOLBAR_BUTTONS


def secondary_action_button_labels() -> tuple[str, ...]:
    return SECONDARY_ACTION_BUTTONS


def sidebar_tab_labels() -> tuple[str, ...]:
    return SIDEBAR_TABS


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


def display_signal_values(
    values: np.ndarray,
    *,
    filter_enabled: bool,
    invert: bool = False,
    sample_rate_hz: float = SAMPLE_RATE_HZ,
) -> np.ndarray:
    display = values if not filter_enabled else bandpass(values, sample_rate_hz)
    display = np.asarray(display, dtype=float)
    return -display if invert else display


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

    source = ads1292r_channel_label(ecg_source) if ecg_source else "--"
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
        GuiStatusCard("Signal", f"{quality_label} on {source}", signal_tone),
        GuiStatusCard("Contact", f"{contact:.1f}% OK, {bad_samples} bad", contact_tone),
        GuiStatusCard("Heart rate", f"{hr_value} bpm, {peak_count} R", hr_tone),
        GuiStatusCard("Artifacts", f"drift {drift:.0f} ct, noise {noise:.1f} ct, p2p {p2p:.0f} ct", artifact_tone),
    )


def _mousewheel_units(event: tk.Event) -> int:
    if getattr(event, "num", None) == 4:
        return -1
    if getattr(event, "num", None) == 5:
        return 1
    delta = int(getattr(event, "delta", 0))
    if delta == 0:
        return 0
    return -1 if delta > 0 else 1


class ScrollableFrame:
    def __init__(self, parent: tk.Widget, width: int = 280) -> None:
        self.frame = ttk.Frame(parent)
        self.canvas = tk.Canvas(self.frame, width=width, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.content = ttk.Frame(self.canvas, padding=10)
        self._content_window = self.canvas.create_window((0, 0), window=self.content, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._fit_content_width)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _update_scroll_region(self, _event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _fit_content_width(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self._content_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not self._contains_pointer(event):
            return
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
        self.geometry("1320x860")

        self.samples: queue.Queue[StreamSample] = queue.Queue()
        self.logs: queue.Queue[str] = queue.Queue()
        self.csv_load_results: queue.Queue[CsvLoadResult] = queue.Queue()
        self.connect_results: queue.Queue[ConnectResult] = queue.Queue()
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

        self.sample_index = 0
        self.ch1: deque[float] = deque(maxlen=MAX_POINTS)
        self.ch2: deque[float] = deque(maxlen=MAX_POINTS)
        self.status: deque[int] = deque(maxlen=MAX_POINTS)
        self.indices: deque[int] = deque(maxlen=MAX_POINTS)
        self.board_hr: deque[int] = deque(maxlen=MAX_POINTS)
        self.board_rr: deque[int] = deque(maxlen=MAX_POINTS)
        self.empty_plot_artists: list[object] = []

        self._build_ui()
        self.refresh_ports()
        self.after(50, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self) -> None:
        self._configure_status_styles()
        self.connection_var = tk.StringVar(value="Not connected")
        self.configure(bg=APP_VISUAL_TOKENS["surface"])

        header = ttk.Frame(self, padding=(18, 12, 18, 10), style="Header.TFrame")
        header.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(header, text="ADS1292 Studio", style="AppTitle.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="MOTAC ECG validation", style="AppSubtitle.TLabel").pack(side=tk.LEFT, padx=(14, 0))
        ttk.Label(header, textvariable=self.connection_var, style="Connection.TLabel").pack(side=tk.RIGHT)

        toolbar = ttk.Frame(self, padding=(14, 10), style="Toolbar.TFrame")
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(toolbar, text="Port", style="ToolbarLabel.TLabel").pack(side=tk.LEFT)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(toolbar, textvariable=self.port_var, width=34)
        self.port_combo.pack(side=tk.LEFT, padx=6)
        self.refresh_button = ttk.Button(toolbar, text="Refresh", command=self.refresh_ports)
        self.refresh_button.pack(side=tk.LEFT)
        self.connect_button = ttk.Button(toolbar, text="Connect", command=self.connect)
        self.connect_button.pack(side=tk.LEFT, padx=(12, 4))
        self.start_button = ttk.Button(toolbar, text="Start", command=self.start)
        self.start_button.pack(side=tk.LEFT, padx=4)
        self.stop_button = ttk.Button(toolbar, text="Stop", command=self.stop)
        self.stop_button.pack(side=tk.LEFT)

        self.save_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Save CSV", variable=self.save_var).pack(side=tk.LEFT, padx=8)
        self.autoscale_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Auto scale", variable=self.autoscale_var).pack(side=tk.LEFT, padx=4)
        self.filter_var = tk.BooleanVar(value=DEFAULT_FILTER_ENABLED)
        ttk.Checkbutton(toolbar, text="Filter", variable=self.filter_var).pack(side=tk.LEFT, padx=4)
        self.source_var = tk.StringVar(value=ADS1292R_ECG_SOURCE)
        ttk.Label(toolbar, text="CH2 ECG / CH1 Resp / Contact", style="ToolbarHint.TLabel").pack(side=tk.LEFT, padx=(12, 2))

        body = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        side_shell = ttk.Frame(body, width=340, padding=(10, 10), style="SidebarShell.TFrame")
        body.add(side_shell, weight=0)
        sidebar = self._build_sidebar(side_shell)
        status_side = sidebar["Status"]
        session_side = sidebar["Session"]
        validation_side = sidebar["Validation"]
        protocol_side = sidebar["Protocol"]
        actions_side = sidebar["Actions"]
        main = ttk.Frame(body, padding=(8, 10, 12, 10), style="Main.TFrame")
        body.add(main, weight=1)

        self.metrics_var = tk.StringVar(value="No session")
        self.quality_var = tk.StringVar(value="Quality: --")
        self.path_var = tk.StringVar(value="CSV: --")
        self.workflow_hint_var = tk.StringVar(value="")
        self.status_overview_var = tk.StringVar(value="")
        self.status_card_vars = {label: tk.StringVar(value="") for label in STATUS_CARD_LABELS}
        self.status_card_value_labels: dict[str, ttk.Label] = {}
        self.signal_card_vars = {label: tk.StringVar(value="") for label in SIGNAL_CARD_LABELS}
        self.signal_card_value_labels: dict[str, ttk.Label] = {}
        self.session_id_var = tk.StringVar(value="untitled-session")
        self.subject_id_var = tk.StringVar(value="anonymous")
        self.electrode_var = tk.StringVar(value="commercial Ag/AgCl control")
        self.montage_var = tk.StringVar(value="RA/LA/RL torso")
        self.operator_var = tk.StringVar(value="")
        self.notes_var = tk.StringVar(value="")
        self.event_label_var = tk.StringVar(value="motion")
        self.event_notes_var = tk.StringVar(value="")
        self.event_count_var = tk.StringVar(value="0 events")
        self.calibration_label_var = tk.StringVar(value="ADS1292 default")
        self.vref_mv_var = tk.StringVar(value="2420")
        self.pga_gain_var = tk.StringVar(value="6")
        self.gate_min_duration_var = tk.StringVar(value="8")
        self.gate_min_contact_var = tk.StringVar(value="95")
        self.gate_min_r_peaks_var = tk.StringVar(value="5")
        self.gate_min_hr_var = tk.StringVar(value="35")
        self.gate_max_hr_var = tk.StringVar(value="180")
        self.gate_require_qrs_var = tk.BooleanVar(value=True)
        self.gate_max_drift_var = tk.StringVar(value="")
        self.gate_max_noise_var = tk.StringVar(value="")
        self.gate_max_ptp_var = tk.StringVar(value="")
        protocol = protocol_template()
        self.protocol_name_var = tk.StringVar(value=protocol.name)
        self.protocol_objective_var = tk.StringVar(value=protocol.objective)
        self.protocol_steps_var = tk.StringVar(value=_format_protocol_steps(protocol.steps))
        self.protocol_acceptance_var = tk.StringVar(value=protocol.acceptance_notes)
        ttk.Label(status_side, text="Next Step", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
        ttk.Label(status_side, textvariable=self.workflow_hint_var, wraplength=260, justify=tk.LEFT, style="Muted.TLabel").pack(anchor=tk.W)
        ttk.Label(status_side, text="Overview", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 6))
        self._build_status_cards(status_side)
        ttk.Label(status_side, text="Signal Quality", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 6))
        self._build_signal_quality_cards(status_side)
        for label, var in (
            ("Session", self.metrics_var),
            ("Quality", self.quality_var),
            ("Storage", self.path_var),
        ):
            ttk.Label(status_side, text=label, style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(10, 2))
            ttk.Label(status_side, textvariable=var, wraplength=260, justify=tk.LEFT, style="Muted.TLabel").pack(anchor=tk.W)

        ttk.Label(session_side, text="Recording Notes", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
        self._metadata_entry(session_side, "Session ID", self.session_id_var)
        self._metadata_entry(session_side, "Subject", self.subject_id_var)
        self._metadata_entry(session_side, "Electrode", self.electrode_var)
        self._metadata_entry(session_side, "Montage", self.montage_var)
        self._metadata_entry(session_side, "Operator", self.operator_var)
        self._metadata_entry(session_side, "Notes", self.notes_var)
        ttk.Label(session_side, text="Events", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
        self._metadata_entry(session_side, "Event label", self.event_label_var)
        self._metadata_entry(session_side, "Event notes", self.event_notes_var)
        ttk.Button(session_side, text="Add Event", command=self.add_event).pack(anchor=tk.W, fill=tk.X, pady=(6, 2))
        ttk.Label(session_side, textvariable=self.event_count_var, wraplength=260, justify=tk.LEFT).pack(anchor=tk.W)

        ttk.Label(validation_side, text="Calibration", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
        self._metadata_entry(validation_side, "Label", self.calibration_label_var)
        self._metadata_entry(validation_side, "Vref mV", self.vref_mv_var)
        self._metadata_entry(validation_side, "PGA gain", self.pga_gain_var)
        ttk.Label(validation_side, text="Quality Gate", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
        self._metadata_entry(validation_side, "Min duration s", self.gate_min_duration_var)
        self._metadata_entry(validation_side, "Min contact %", self.gate_min_contact_var)
        self._metadata_entry(validation_side, "Min R peaks", self.gate_min_r_peaks_var)
        self._metadata_entry(validation_side, "HR min bpm", self.gate_min_hr_var)
        self._metadata_entry(validation_side, "HR max bpm", self.gate_max_hr_var)
        ttk.Checkbutton(validation_side, text="Require QRS clear", variable=self.gate_require_qrs_var).pack(anchor=tk.W)
        self._metadata_entry(validation_side, "Max drift counts", self.gate_max_drift_var)
        self._metadata_entry(validation_side, "Max noise RMS", self.gate_max_noise_var)
        self._metadata_entry(validation_side, "Max peak-to-peak", self.gate_max_ptp_var)

        ttk.Label(protocol_side, text="Protocol", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
        self._metadata_entry(protocol_side, "Name", self.protocol_name_var)
        self._metadata_entry(protocol_side, "Objective", self.protocol_objective_var)
        self._metadata_entry(protocol_side, "Steps", self.protocol_steps_var)
        self._metadata_entry(protocol_side, "Acceptance", self.protocol_acceptance_var)

        ttk.Label(actions_side, text="Review", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(8, 2))
        self.load_csv_button = ttk.Button(actions_side, text="Load CSV", command=self.load_csv)
        self.load_csv_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self.export_report_button = ttk.Button(actions_side, text="Export Report", command=self.export_report)
        self.export_report_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Label(actions_side, text="Package", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
        self.export_package_button = ttk.Button(actions_side, text="Export Package", command=self.export_package)
        self.export_package_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self.verify_package_button = ttk.Button(actions_side, text="Verify Package", command=self.verify_package)
        self.verify_package_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Label(actions_side, text="Library", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
        self.batch_compare_button = ttk.Button(actions_side, text="Batch Compare", command=self.batch_compare)
        self.batch_compare_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        self.session_index_button = ttk.Button(actions_side, text="Session Index", command=self.session_index)
        self.session_index_button.pack(anchor=tk.W, fill=tk.X, pady=2)
        ttk.Label(actions_side, text="Safety", style="SectionHeading.TLabel").pack(anchor=tk.W, pady=(14, 2))
        ttk.Label(
            actions_side,
            text="Research use only. Use battery power during human-subject measurements.",
            wraplength=260,
            justify=tk.LEFT,
            style="Muted.TLabel",
        ).pack(anchor=tk.W)

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.live_tab = ttk.Frame(self.notebook)
        self.review_tab = ttk.Frame(self.notebook)
        self.pqrst_tab = ttk.Frame(self.notebook)
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.live_tab, text="Live")
        self.notebook.add(self.review_tab, text="Review")
        self.notebook.add(self.pqrst_tab, text="PQRST")
        self.notebook.add(self.log_tab, text="Log")

        self._build_live_plot()
        self._build_review_plot()
        self._build_pqrst_plot()
        self.log_text = tk.Text(
            self.log_tab,
            height=12,
            bg=APP_VISUAL_TOKENS["panel"],
            fg=APP_VISUAL_TOKENS["ink"],
            insertbackground=APP_VISUAL_TOKENS["accent"],
            relief=tk.FLAT,
            padx=12,
            pady=10,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.control_buttons = {
            "Refresh": self.refresh_button,
            "Connect": self.connect_button,
            "Start": self.start_button,
            "Stop": self.stop_button,
            "Load CSV": self.load_csv_button,
            "Export Report": self.export_report_button,
            "Export Package": self.export_package_button,
            "Verify Package": self.verify_package_button,
            "Batch Compare": self.batch_compare_button,
            "Session Index": self.session_index_button,
        }
        self._apply_control_states()

    def _configure_status_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        tokens = APP_VISUAL_TOKENS
        style.configure(".", font=("Aptos", 12), background=tokens["surface"], foreground=tokens["ink"])
        style.configure("TFrame", background=tokens["surface"])
        style.configure("Header.TFrame", background=tokens["panel"], borderwidth=0)
        style.configure("Toolbar.TFrame", background=tokens["panel_alt"], borderwidth=1, relief=tk.FLAT)
        style.configure("SidebarShell.TFrame", background=tokens["surface"])
        style.configure("Main.TFrame", background=tokens["surface"])
        style.configure("TLabel", background=tokens["surface"], foreground=tokens["ink"])
        style.configure("AppTitle.TLabel", background=tokens["panel"], foreground=tokens["ink"], font=("Aptos", 20, "bold"))
        style.configure("AppSubtitle.TLabel", background=tokens["panel"], foreground=tokens["muted"], font=("Aptos", 12))
        style.configure("Connection.TLabel", background=tokens["panel"], foreground=tokens["accent"], font=("Aptos", 12, "bold"))
        style.configure("ToolbarLabel.TLabel", background=tokens["panel_alt"], foreground=tokens["ink"], font=("Aptos", 12, "bold"))
        style.configure("ToolbarHint.TLabel", background=tokens["panel_alt"], foreground=tokens["muted"])
        style.configure("SectionHeading.TLabel", background=tokens["surface"], foreground=tokens["ink"], font=("Aptos", 12, "bold"))
        style.configure("Muted.TLabel", background=tokens["surface"], foreground=tokens["muted"])
        style.configure("Card.TFrame", background=tokens["panel"], borderwidth=1, relief=tk.SOLID)
        style.configure("CardLabel.TLabel", background=tokens["panel"], foreground=tokens["muted"], font=("Aptos", 11))
        style.configure("TButton", padding=(10, 6), font=("Aptos", 12))
        style.configure("TCheckbutton", background=tokens["panel_alt"], foreground=tokens["ink"])
        style.configure("TNotebook", background=tokens["surface"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 7), font=("Aptos", 12, "bold"))
        style.configure("Ready.Status.TLabel", background=tokens["panel"], foreground=tokens["success"], font=("Aptos", 12, "bold"))
        style.configure("Running.Status.TLabel", background=tokens["panel"], foreground=tokens["accent"], font=("Aptos", 12, "bold"))
        style.configure("Warning.Status.TLabel", background=tokens["panel"], foreground=tokens["warning"], font=("Aptos", 12, "bold"))
        style.configure("Neutral.Status.TLabel", background=tokens["panel"], foreground=tokens["muted"], font=("Aptos", 12, "bold"))

    def _build_status_cards(self, parent: ttk.Frame) -> None:
        for label in STATUS_CARD_LABELS:
            row = ttk.Frame(parent, padding=(10, 8), style="Card.TFrame")
            row.pack(anchor=tk.W, fill=tk.X, pady=3)
            ttk.Label(row, text=label, width=12, style="CardLabel.TLabel").pack(side=tk.LEFT)
            value_label = ttk.Label(
                row,
                textvariable=self.status_card_vars[label],
                style=status_tone_style("neutral"),
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.status_card_value_labels[label] = value_label

    def _build_signal_quality_cards(self, parent: ttk.Frame) -> None:
        for label in SIGNAL_CARD_LABELS:
            row = ttk.Frame(parent, padding=(10, 8), style="Card.TFrame")
            row.pack(anchor=tk.W, fill=tk.X, pady=3)
            ttk.Label(row, text=label, width=12, style="CardLabel.TLabel").pack(side=tk.LEFT)
            value_label = ttk.Label(
                row,
                textvariable=self.signal_card_vars[label],
                style=status_tone_style("neutral"),
                wraplength=170,
                justify=tk.LEFT,
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.signal_card_value_labels[label] = value_label

    def _build_sidebar(self, parent: ttk.Frame) -> dict[str, ttk.Frame]:
        self.sidebar_notebook = ttk.Notebook(parent)
        self.sidebar_notebook.pack(fill=tk.BOTH, expand=True)
        self.sidebar_scrolls: dict[str, ScrollableFrame] = {}
        sections: dict[str, ttk.Frame] = {}
        for label in SIDEBAR_TABS:
            tab = ttk.Frame(self.sidebar_notebook)
            scroll = ScrollableFrame(tab, width=310)
            scroll.frame.pack(fill=tk.BOTH, expand=True)
            self.sidebar_notebook.add(tab, text=label)
            self.sidebar_scrolls[label] = scroll
            sections[label] = scroll.content
        return sections

    def _metadata_entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="Muted.TLabel").pack(anchor=tk.W, pady=(6, 0))
        ttk.Entry(parent, textvariable=variable).pack(anchor=tk.W, fill=tk.X)

    def _build_live_plot(self) -> None:
        fig = self._new_plot_figure(figsize=(10, 7))
        fig.subplots_adjust(hspace=0.55)
        self.ax_live_ecg = fig.add_subplot(311)
        self.ax_live_resp = fig.add_subplot(312, sharex=self.ax_live_ecg)
        self.ax_live_status = fig.add_subplot(313, sharex=self.ax_live_ecg)
        for ax in (self.ax_live_ecg, self.ax_live_resp, self.ax_live_status):
            ax.label_outer()
        self._style_signal_axes((self.ax_live_ecg, self.ax_live_resp, self.ax_live_status))
        self.ax_live_ecg.set_ylabel("counts")
        self.ax_live_resp.set_ylabel("counts")
        self.ax_live_status.set_xlabel("Time (s)")
        self.live_ecg_line, = self.ax_live_ecg.plot([], [], lw=1.1, color=PLOT_TRACE_COLORS["ecg"])
        self.live_peak_line, = self.ax_live_ecg.plot([], [], ".", ms=5, color=PLOT_TRACE_COLORS["peak"])
        self.live_resp_line, = self.ax_live_resp.plot([], [], lw=0.9, color=PLOT_TRACE_COLORS["respiration"])
        self.live_status_line, = self.ax_live_status.plot(
            [],
            [],
            lw=0.9,
            drawstyle="steps-post",
            color=PLOT_TRACE_COLORS["contact"],
        )
        self._show_empty_plot_state("live", (self.ax_live_ecg, self.ax_live_resp, self.ax_live_status))
        self.live_canvas = FigureCanvasTkAgg(fig, master=self.live_tab)
        self.live_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_review_plot(self) -> None:
        fig = self._new_plot_figure(figsize=(10, 7))
        fig.subplots_adjust(hspace=0.55)
        self.ax_review_ecg = fig.add_subplot(311)
        self.ax_review_resp = fig.add_subplot(312, sharex=self.ax_review_ecg)
        self.ax_review_status = fig.add_subplot(313, sharex=self.ax_review_ecg)
        for ax in (self.ax_review_ecg, self.ax_review_resp, self.ax_review_status):
            ax.label_outer()
        self._style_signal_axes((self.ax_review_ecg, self.ax_review_resp, self.ax_review_status))
        self.ax_review_status.set_xlabel("Samples")
        self.ax_review_ecg.set_ylabel("counts")
        self.ax_review_resp.set_ylabel("counts")
        self.review_ecg_line, = self.ax_review_ecg.plot([], [], lw=1.0, color=PLOT_TRACE_COLORS["ecg"])
        self.review_peak_line, = self.ax_review_ecg.plot([], [], ".", ms=5, color=PLOT_TRACE_COLORS["peak"])
        self.review_resp_line, = self.ax_review_resp.plot([], [], lw=0.9, color=PLOT_TRACE_COLORS["respiration"])
        self.review_status_line, = self.ax_review_status.plot(
            [],
            [],
            lw=0.9,
            drawstyle="steps-post",
            color=PLOT_TRACE_COLORS["contact"],
        )
        self._show_empty_plot_state("review", (self.ax_review_ecg, self.ax_review_resp, self.ax_review_status))
        self.review_canvas = FigureCanvasTkAgg(fig, master=self.review_tab)
        self.review_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_pqrst_plot(self) -> None:
        fig = self._new_plot_figure(figsize=(10, 6))
        self.ax_pqrst = fig.add_subplot(111)
        self._style_signal_axes((self.ax_pqrst,))
        self.ax_pqrst.set_xlabel("Time relative to R peak (ms)")
        self.ax_pqrst.set_ylabel("Filtered counts")
        self._show_empty_plot_state("pqrst", (self.ax_pqrst,))
        self.pqrst_canvas = FigureCanvasTkAgg(fig, master=self.pqrst_tab)
        self.pqrst_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _new_plot_figure(self, *, figsize: tuple[float, float]) -> Figure:
        fig = Figure(figsize=figsize, dpi=100)
        fig.patch.set_facecolor(APP_VISUAL_TOKENS["surface"])
        return fig

    def _style_signal_axes(self, axes: tuple[object, ...]) -> None:
        for ax in axes:
            ax.set_facecolor(APP_VISUAL_TOKENS["panel"])
            ax.grid(True, color=APP_VISUAL_TOKENS["border"], linewidth=0.8, alpha=0.65)
            ax.tick_params(colors=APP_VISUAL_TOKENS["muted"], labelsize=9)
            ax.xaxis.label.set_color(APP_VISUAL_TOKENS["ink"])
            ax.yaxis.label.set_color(APP_VISUAL_TOKENS["ink"])
            ax.title.set_color(APP_VISUAL_TOKENS["ink"])
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(APP_VISUAL_TOKENS["border"])

    def _show_empty_plot_state(self, key: str, axes: tuple[object, ...]) -> None:
        for ax, message in zip(axes, EMPTY_PLOT_MESSAGES[key]):
            artist = ax.text(
                0.5,
                0.5,
                message,
                transform=ax.transAxes,
                ha="center",
                va="center",
                color=APP_VISUAL_TOKENS["muted"],
                fontsize=11,
                fontweight="bold",
                alpha=0.82,
            )
            self.empty_plot_artists.append(artist)

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
        threading.Thread(
            target=self._read_csv_in_background,
            args=(csv_path,),
            daemon=True,
        ).start()

    def _read_csv_in_background(self, path: Path) -> None:
        try:
            recording = read_recording_csv(path)
            self.csv_load_results.put(CsvLoadResult(path=path, recording=recording))
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

    def _apply_control_states(self) -> None:
        if not hasattr(self, "control_buttons"):
            return
        state = GuiState(
            connected=self.connected_port is not None,
            streaming=self.is_streaming,
            has_data=bool(self.loaded_samples or (self.ch1 and self.ch2)),
            has_recording_path=self.recording_path is not None,
            loading_csv=self.is_loading_csv,
            connecting=self.is_connecting,
            starting=self.is_starting,
        )
        states = gui_control_states(state=state)
        self.workflow_hint_var.set(
            gui_workflow_hint(state=state)
        )
        self.status_overview_var.set(
            gui_status_overview(state=state)
        )
        for card in gui_status_cards(state=state):
            self.status_card_vars[card.label].set(card.value)
            self.status_card_value_labels[card.label].configure(
                style=status_tone_style(card.tone)
            )
        if not state.has_data:
            self._apply_signal_quality_cards(gui_signal_quality_cards())
        for label, button in self.control_buttons.items():
            button.configure(state=states[label])

    def _apply_signal_quality_cards(self, cards: tuple[GuiStatusCard, ...]) -> None:
        for card in cards:
            self.signal_card_vars[card.label].set(card.value)
            self.signal_card_value_labels[card.label].configure(
                style=status_tone_style(card.tone)
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

    def _tick(self) -> None:
        self._drain_csv_load_results()
        self._drain_connect_results()
        self._drain_stream_start_results()
        latest = None
        while True:
            try:
                latest = self.samples.get_nowait()
            except queue.Empty:
                break
            self._append_sample(latest)
        if latest is not None:
            self._redraw_live()
            self._apply_control_states()
        while True:
            try:
                self._log(self.logs.get_nowait())
            except queue.Empty:
                break
        self.after(50, self._tick)

    def _append_sample(self, sample: StreamSample) -> None:
        self.indices.append(self.sample_index)
        self.sample_index += 1
        self.ch1.append(sample.ch1)
        self.ch2.append(sample.ch2)
        self.status.append(sample.lead_off_bits)
        self.board_hr.append(sample.board_heart_rate)
        self.board_rr.append(sample.board_respiration_rate)

    def _ads1292r_display_channels(self) -> tuple[str, np.ndarray, np.ndarray]:
        ch1 = np.asarray(self.ch1, dtype=float)
        ch2 = np.asarray(self.ch2, dtype=float)
        return ADS1292R_ECG_SOURCE, ch2, ch1

    def _display_signal(self, values: np.ndarray, *, invert: bool = False) -> np.ndarray:
        return display_signal_values(
            values,
            filter_enabled=bool(self.filter_var.get()),
            invert=invert,
            sample_rate_hz=SAMPLE_RATE_HZ,
        )

    def _redraw_live(self) -> None:
        if not self.indices:
            return
        self._clear_empty_plot_state()
        source, ecg_raw, resp_raw = self._ads1292r_display_channels()
        ecg = self._display_signal(ecg_raw, invert=DEFAULT_ECG_INVERTED)
        resp = self._display_signal(resp_raw)
        x = np.asarray(self.indices, dtype=float) / SAMPLE_RATE_HZ
        left = max(0.0, x[-1] - VISIBLE_SECONDS)
        right = max(VISIBLE_SECONDS, x[-1])
        visible = (x >= left) & (x <= right)
        peaks = detect_r_peaks(ecg[visible], SAMPLE_RATE_HZ)
        peaks_x = x[visible][list(peaks)] if peaks else []
        peaks_y = ecg[visible][list(peaks)] if peaks else []

        self.live_ecg_line.set_data(x, ecg)
        self.live_peak_line.set_data(peaks_x, peaks_y)
        self.live_resp_line.set_data(x, resp)
        self.live_status_line.set_data(x, list(self.status))
        for ax in (self.ax_live_ecg, self.ax_live_resp, self.ax_live_status):
            ax.set_xlim(left, right)
        if self.autoscale_var.get():
            self.ax_live_ecg.set_ylim(*robust_ylim(ecg[visible]))
            self.ax_live_resp.set_ylim(*robust_ylim(resp[visible]))
            self.ax_live_status.set_ylim(-0.5, max(1.0, max(self.status or [0]) + 0.5))
        hr = heart_rate_summary(peaks, SAMPLE_RATE_HZ)
        ecg_label, resp_label, contact_label = ads1292r_plot_layout_labels()
        mode = "filtered" if self.filter_var.get() else "raw"
        polarity = ", inverted" if DEFAULT_ECG_INVERTED else ""
        self.ax_live_ecg.set_title(f"ECG display: {ecg_label} | {mode}{polarity} | R peaks {len(peaks)}")
        self.ax_live_resp.set_title(resp_label)
        self.ax_live_status.set_title(contact_label)
        self.metrics_var.set(
            f"samples {self.sample_index} | duration {x[-1]:.1f} s | source {ecg_label} | HR {hr.median_bpm:.0f} bpm"
        )
        samples = tuple(self._current_samples())
        metrics = compute_quality_metrics(samples, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
        self.quality_var.set(self._quality_text(source, hr.valid_rr_count, samples, tuple(self.status), metrics=metrics))
        self._apply_signal_quality_cards(
            gui_signal_quality_cards(
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
        )
        self.live_canvas.draw_idle()

    def _show_recording(self, samples: tuple[StreamSample, ...]) -> None:
        self._clear_empty_plot_state()
        self._clear_signal_buffers()
        self.sample_index = 0
        full_ch1 = np.asarray([sample.ch1 for sample in samples], dtype=float)
        full_ch2 = np.asarray([sample.ch2 for sample in samples], dtype=float)
        full_status_ints = tuple(sample.lead_off_bits for sample in samples)
        source = ADS1292R_ECG_SOURCE
        ecg = self._display_signal(full_ch2, invert=DEFAULT_ECG_INVERTED)
        resp = self._display_signal(full_ch1)
        result = review_channels(full_ch1, full_ch2, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
        metrics = compute_quality_metrics(samples, SAMPLE_RATE_HZ, ADS1292R_ECG_SOURCE)
        x = np.arange(ecg.size)
        status_arr = np.asarray(full_status_ints, dtype=float)
        plot_x, plot_ecg = decimate_for_plot(x, ecg, MAX_POINTS)
        _, plot_resp = decimate_for_plot(x, resp, MAX_POINTS)
        _, plot_status = decimate_for_plot(x, status_arr, MAX_POINTS)
        ecg_label, resp_label, contact_label = ads1292r_plot_layout_labels()
        self.review_ecg_line.set_data(plot_x, plot_ecg)
        self.review_resp_line.set_data(plot_x, plot_resp)
        self.review_status_line.set_data(plot_x, plot_status)
        self.review_peak_line.set_data(list(result.peaks), ecg[list(result.peaks)] if result.peaks else [])
        polarity = ", inverted" if DEFAULT_ECG_INVERTED else ""
        self.ax_review_ecg.set_title(
            f"Offline ECG: {ecg_label} | {'filtered' if self.filter_var.get() else 'raw'}{polarity} | "
            f"HR {result.heart_rate.median_bpm:.1f} bpm | peaks {len(result.peaks)}"
        )
        self.ax_review_resp.set_title(resp_label)
        self.ax_review_status.set_title(contact_label)
        for ax, values in ((self.ax_review_ecg, ecg), (self.ax_review_resp, resp)):
            ax.set_xlim(0, max(1, x[-1] if x.size else 1))
            ax.set_ylim(*robust_ylim(values))
        self.ax_review_status.set_xlim(0, max(1, x[-1] if x.size else 1))
        self.ax_review_status.set_ylim(-0.5, max(1.0, float(status_arr.max()) + 0.5 if status_arr.size else 1.0))
        self.review_canvas.draw_idle()
        self._draw_pqrst(ecg, result.peaks)
        self.metrics_var.set(
            f"samples {len(samples)} | duration {len(samples) / SAMPLE_RATE_HZ:.1f} s | source {ecg_label}"
        )
        self.quality_var.set(
            f"{self._quality_text(source, result.heart_rate.valid_rr_count, samples, full_status_ints, metrics=metrics)} | "
            f"QRS {'clear' if result.pqrst.qrs_clear else 'unclear'} | "
            f"P {'tentative' if result.pqrst.p_tentative else 'not reliable'} | "
            f"T {'tentative' if result.pqrst.t_tentative else 'not reliable'}"
        )
        self._apply_signal_quality_cards(
            gui_signal_quality_cards(
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
        )

    def _draw_pqrst(self, ecg: np.ndarray, peaks: tuple[int, ...]) -> None:
        review = pqrst_review(ecg, peaks, SAMPLE_RATE_HZ)
        self.ax_pqrst.clear()
        self._style_signal_axes((self.ax_pqrst,))
        self.ax_pqrst.set_xlabel("Time relative to R peak (ms)")
        self.ax_pqrst.set_ylabel("Filtered counts")
        if review.average_beat:
            self.ax_pqrst.plot(
                review.time_ms,
                review.average_beat,
                lw=2.0,
                color=PLOT_TRACE_COLORS["ecg"],
                label="average beat",
            )
            self.ax_pqrst.axvline(0, color=PLOT_TRACE_COLORS["peak"], linestyle="--", lw=1, label="R")
            self.ax_pqrst.axvspan(-220, -80, color=APP_VISUAL_TOKENS["success"], alpha=0.08, label="P search")
            self.ax_pqrst.axvspan(120, 380, color=APP_VISUAL_TOKENS["warning"], alpha=0.08, label="T search")
            self.ax_pqrst.legend(loc="upper right")
        self.ax_pqrst.set_title(
            f"PQRST review: QRS={review.qrs_clear}, P tentative={review.p_tentative}, "
            f"T tentative={review.t_tentative}, beats={review.beats_used}"
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

    def _current_samples(self) -> tuple[StreamSample, ...]:
        return tuple(
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

    def _log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{stamp}] {message}\n")
        self.log_text.see(tk.END)

    def _close(self) -> None:
        self.stop()
        self.destroy()


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
