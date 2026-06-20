from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from pathlib import Path
import queue
import tkinter as tk
from typing import TypeVar

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings, display_mode_label
from ads1292_studio.gui_specs import status_tone_color, status_tone_style


_T = TypeVar("_T")

MAX_SAMPLES_PER_TICK = 1000
MAX_LOG_MESSAGES_PER_TICK = 200
CATCH_UP_TICK_INTERVAL_MS = 1
ACTIVE_TICK_INTERVAL_MS = 40
IDLE_TICK_INTERVAL_MS = 150


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
    has_port: bool = True
    selected_port: str = ""
    loading_csv: bool = False
    connecting: bool = False
    starting: bool = False

    @property
    def busy(self) -> bool:
        return self.loading_csv or self.connecting or self.starting

    @property
    def package_ready(self) -> bool:
        return self.has_data and self.has_recording_path and not self.busy


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
    has_port: bool = True,
    selected_port: str = "",
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
        has_port=has_port,
        selected_port=selected_port,
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


def gui_tick_interval_ms(state: GuiState, *, sample_backlog: bool = False) -> int:
    if sample_backlog and state.streaming:
        return CATCH_UP_TICK_INTERVAL_MS
    return ACTIVE_TICK_INTERVAL_MS if state.streaming or state.busy else IDLE_TICK_INTERVAL_MS


def gui_control_states(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
    has_port: bool = True,
) -> dict[str, str]:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
        has_port=has_port,
    )
    if current.busy:
        return {
            "Port": tk.DISABLED,
            "Refresh": tk.DISABLED,
            "Connect": tk.DISABLED,
            "Start": tk.DISABLED,
            "Stop": tk.NORMAL if current.streaming else tk.DISABLED,
            "Save CSV": tk.DISABLED,
            "Load CSV": tk.DISABLED,
            "Export Report": tk.DISABLED,
            "Export Package": tk.DISABLED,
            "Verify Package": tk.DISABLED,
            "Batch Compare": tk.DISABLED,
            "Session Index": tk.DISABLED,
        }
    return {
        "Port": tk.DISABLED if current.streaming else tk.NORMAL,
        "Refresh": tk.NORMAL,
        "Connect": tk.NORMAL if current.has_port and not current.connected and not current.streaming else tk.DISABLED,
        "Start": tk.NORMAL if current.connected and not current.streaming else tk.DISABLED,
        "Stop": tk.NORMAL if current.streaming else tk.DISABLED,
        "Save CSV": tk.NORMAL if not current.streaming else tk.DISABLED,
        "Load CSV": tk.NORMAL if not current.streaming else tk.DISABLED,
        "Export Report": tk.NORMAL if current.has_data else tk.DISABLED,
        "Export Package": tk.NORMAL if current.package_ready else tk.DISABLED,
        "Verify Package": tk.NORMAL,
        "Batch Compare": tk.NORMAL,
        "Session Index": tk.NORMAL,
    }


def gui_control_cursors(states: dict[str, str]) -> dict[str, str]:
    return {label: "arrow" if state == tk.DISABLED else "hand2" for label, state in states.items()}


def port_entry_connection_message(
    *,
    port_text: str,
    connected: bool,
    busy: bool,
    streaming: bool,
) -> str | None:
    if connected or busy or streaming:
        return None
    return "Not connected" if port_text.strip() else "No ADS1x9x port"


def selected_port_is_connected(connected_port: str | None, port_text: str) -> bool:
    return connected_port is not None and port_text.strip() == connected_port


def short_port_label(port_text: str) -> str:
    port = port_text.strip()
    if not port:
        return "none"
    name = Path(port).name
    for prefix in ("cu.", "tty."):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def effective_port_text(
    variable_text: str,
    widget_text: str,
    available_values: Iterable[object] = (),
) -> str:
    variable_port = variable_text.strip()
    if variable_port:
        return variable_port
    widget_port = widget_text.strip()
    if widget_port:
        return widget_port
    for value in available_values:
        port = str(value).strip()
        if port:
            return port
    return ""


def stable_port_text(
    *,
    variable_text: str,
    widget_text: str,
    available_values: Iterable[object] = (),
    remembered_text: str = "",
    allow_remembered: bool = True,
) -> str:
    current = effective_port_text(variable_text, widget_text, available_values)
    if current:
        return current
    if not allow_remembered:
        return ""
    return remembered_text.strip()


def gui_workflow_hint(
    *,
    state: GuiState | None = None,
    connected: bool = False,
    streaming: bool = False,
    has_data: bool = False,
    has_recording_path: bool = False,
    has_port: bool = True,
) -> str:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
        has_port=has_port,
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
    if not current.has_port:
        return "No ADS1292 port detected: plug in the board, press Refresh, or load an existing CSV."
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


def apply_live_metrics_text(
    var: object,
    *,
    sample_index: int,
    duration_seconds: float,
    ecg_label: str,
    heart_rate_bpm: float,
    peak_count: int,
) -> bool:
    return set_string_var_if_changed(
        var,
        live_metrics_text(
            sample_index=sample_index,
            duration_seconds=duration_seconds,
            ecg_label=ecg_label,
            heart_rate_bpm=heart_rate_bpm,
            peak_count=peak_count,
        ),
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


def live_render_refresh_key(
    *,
    sample_index: int,
    display_settings: object,
    filter_settings: object,
    autoscale: bool,
    source: str,
    ecg_inverted: bool,
) -> tuple[object, ...]:
    return (
        int(sample_index),
        display_settings,
        filter_settings,
        bool(autoscale),
        source,
        bool(ecg_inverted),
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


def set_axis_xlim_if_changed(ax: object, limits: tuple[float, float]) -> bool:
    target = (float(limits[0]), float(limits[1]))
    current = tuple(float(value) for value in ax.get_xlim())
    if not axis_limits_changed(current, target):
        return False
    ax.set_xlim(*target)
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
    selected_port: str = "",
) -> tuple[GuiStatusCard, ...]:
    current = _gui_state(
        state=state,
        connected=connected,
        streaming=streaming,
        has_data=has_data,
        has_recording_path=has_recording_path,
        selected_port=selected_port,
    )
    connection_value = "connected" if current.connected else ("disconnected" if current.has_port else "no port")
    connection = GuiStatusCard(
        label="Connection",
        value=connection_value,
        tone="ready" if current.connected else "warning",
    )
    port = GuiStatusCard(
        label="Port",
        value=short_port_label(current.selected_port),
        tone="neutral" if current.selected_port.strip() else "warning",
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
        port,
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
