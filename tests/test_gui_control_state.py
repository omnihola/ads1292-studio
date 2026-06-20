import queue

import numpy as np

from ads1292_studio.app import (
    DEFAULT_ECG_INVERTED,
    DEFAULT_FILTER_ENABLED,
    ACTIVE_TICK_INTERVAL_MS,
    GuiState,
    GuiStatusCard,
    IDLE_TICK_INTERVAL_MS,
    MAX_LOG_MESSAGES_PER_TICK,
    MAX_SAMPLES_PER_TICK,
    ads1292r_channel_label,
    apply_status_card_if_changed,
    axis_limits_changed,
    ads1292r_secondary_channel_label,
    build_live_quality_samples,
    compact_ecg_source_label,
    configure_widget_option_if_changed,
    compute_live_quality_result,
    compute_review_render_result,
    display_scale_reference_label,
    display_signal_values,
    display_refresh_key,
    drain_queue_items,
    gui_control_cursors,
    gui_control_states,
    gui_signal_quality_cards,
    gui_status_cards,
    gui_status_overview,
    gui_tick_interval_ms,
    gui_workflow_hint,
    header_connection_style,
    header_connection_tone,
    live_axis_titles,
    live_ecg_axis_title,
    live_quality_sample_count_ready,
    live_quality_worker_available,
    live_metrics_text,
    live_render_refresh_key,
    port_entry_connection_message,
    set_axis_xlim_if_changed,
    set_axis_ylim_if_changed,
    set_string_var_if_changed,
    should_apply_control_state,
    status_label_spec,
    status_tone_color,
    status_tone_style,
    toolbar_display_hint_text,
)

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings
from ads1292_studio.models import StreamSample


class _FakeStringVar:
    def __init__(self, value: str) -> None:
        self.value = value
        self.set_calls = 0

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value
        self.set_calls += 1


class _FakeWidget:
    def __init__(self, **values: str) -> None:
        self.values = dict(values)
        self.configure_calls = 0

    def cget(self, key: str) -> str:
        return self.values[key]

    def configure(self, **values: str) -> None:
        self.values = {**self.values, **values}
        self.configure_calls += 1


class _FakeAxis:
    def __init__(self, ylim: tuple[float, float], xlim: tuple[float, float] = (0.0, 1.0)) -> None:
        self.ylim = ylim
        self.xlim = xlim
        self.set_ylim_calls = 0
        self.set_xlim_calls = 0

    def get_xlim(self) -> tuple[float, float]:
        return self.xlim

    def set_xlim(self, lo: float, hi: float) -> None:
        self.xlim = (lo, hi)
        self.set_xlim_calls += 1

    def get_ylim(self) -> tuple[float, float]:
        return self.ylim

    def set_ylim(self, lo: float, hi: float) -> None:
        self.ylim = (lo, hi)
        self.set_ylim_calls += 1


class _FakeFuture:
    def __init__(self, done: bool) -> None:
        self._done = done

    def done(self) -> bool:
        return self._done


def test_ads1292r_channel_labels_name_ti_board_semantics() -> None:
    assert ads1292r_channel_label("CH2") == "CH2 ECG Lead I (LA-RA)"
    assert ads1292r_channel_label("CH1") == "CH1 Respiration raw"
    assert ads1292r_channel_label("UNKNOWN") == "UNKNOWN"


def test_ads1292r_secondary_channel_label_names_remaining_plot() -> None:
    assert ads1292r_secondary_channel_label("CH2") == "CH1 Respiration raw"
    assert ads1292r_secondary_channel_label("CH1") == "CH2 ECG Lead I (LA-RA)"


def test_default_display_is_raw_without_ecg_inversion() -> None:
    values = np.array([10.0, -20.0, 30.0])

    assert DEFAULT_FILTER_ENABLED is False
    assert DEFAULT_ECG_INVERTED is False
    np.testing.assert_array_equal(
        display_signal_values(values, filter_enabled=DEFAULT_FILTER_ENABLED, invert=DEFAULT_ECG_INVERTED),
        values,
    )
    np.testing.assert_array_equal(
        display_signal_values(values, filter_enabled=DEFAULT_FILTER_ENABLED, invert=True),
        np.array([-10.0, 20.0, -30.0]),
    )


def test_display_signal_gain_is_display_only() -> None:
    values = np.array([10.0, -20.0, 30.0])

    display = display_signal_values(
        values,
        filter_enabled=False,
        filter_settings=SoftwareFilterSettings(),
        gain=2.0,
    )

    np.testing.assert_array_equal(display, np.array([20.0, -40.0, 60.0]))
    np.testing.assert_array_equal(values, np.array([10.0, -20.0, 30.0]))


def test_compute_live_quality_result_keeps_generation_and_metrics() -> None:
    ch1_values = tuple(0.0 for _ in range(1000))
    ch2_values = tuple(1000.0 if index % 250 == 0 else 0.0 for index in range(1000))
    status_values = tuple(0 for _ in range(1000))

    result = compute_live_quality_result(
        generation=7,
        source="CH2",
        valid_rr=3,
        ch1_values=ch1_values,
        ch2_values=ch2_values,
        status_values=status_values,
    )

    assert result.generation == 7
    assert result.source == "CH2"
    assert result.valid_rr == 3
    assert result.error is None
    assert result.metrics is not None
    assert result.metrics.sample_count == len(ch2_values)
    assert len(result.samples) == len(ch2_values)


def test_live_quality_sample_count_waits_for_one_second_of_data() -> None:
    assert live_quality_sample_count_ready(499, 500.0) is False
    assert live_quality_sample_count_ready(500, 500.0) is True
    assert live_quality_sample_count_ready(1000, 500.0) is True
    assert live_quality_sample_count_ready(0, 0.0) is False


def test_worker_helpers_live_outside_app_module() -> None:
    assert compute_live_quality_result.__module__ == "ads1292_studio.gui_workers"
    assert compute_review_render_result.__module__ == "ads1292_studio.gui_workers"
    assert build_live_quality_samples.__module__ == "ads1292_studio.gui_workers"
    assert live_quality_sample_count_ready.__module__ == "ads1292_studio.gui_workers"


def test_compute_review_render_result_prepares_offline_frame() -> None:
    samples = tuple(
        StreamSample(
            timestamp=index / 500.0,
            ch1=0,
            ch2=1000 if index % 250 == 0 else 0,
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index in range(1000)
    )

    result = compute_review_render_result(
        generation=11,
        samples=samples,
        display_settings=EcgDisplaySettings(gain=2.0),
        filter_settings=SoftwareFilterSettings(),
    )

    assert result.generation == 11
    assert result.samples == samples
    assert result.error is None
    assert result.frame is not None
    assert result.frame.sample_count == len(samples)
    assert result.frame.mode == "raw | 2x | 8s | 25 mm/s, display-smoothed"


def test_build_live_quality_samples_preserves_channel_and_status_order() -> None:
    samples = build_live_quality_samples(
        ch1_values=(10.0, 20.0),
        ch2_values=(-1.0, -2.0),
        status_values=(0, 3),
    )

    assert [sample.timestamp for sample in samples] == [0.0, 1 / 500.0]
    assert [sample.ch1 for sample in samples] == [10, 20]
    assert [sample.ch2 for sample in samples] == [-1, -2]
    assert [sample.lead_off_bits for sample in samples] == [0, 3]


def test_set_string_var_if_changed_skips_redundant_tk_updates() -> None:
    var = _FakeStringVar("ready")

    assert set_string_var_if_changed(var, "ready") is False
    assert var.set_calls == 0
    assert set_string_var_if_changed(var, "running") is True
    assert var.value == "running"
    assert var.set_calls == 1


def test_configure_widget_option_if_changed_skips_redundant_tk_updates() -> None:
    widget = _FakeWidget(state="normal")

    assert configure_widget_option_if_changed(widget, "state", "normal") is False
    assert widget.configure_calls == 0
    assert configure_widget_option_if_changed(widget, "state", "disabled") is True
    assert widget.values["state"] == "disabled"
    assert widget.configure_calls == 1


def test_apply_status_card_if_changed_skips_redundant_tk_updates() -> None:
    card = GuiStatusCard("Signal", "Good ECG/QRS", "ready")
    variable = _FakeStringVar("Good ECG/QRS")
    value_label = _FakeWidget(style=status_tone_style("ready"))
    stripe = _FakeWidget(bg=status_tone_color("ready"))

    changed = apply_status_card_if_changed(
        variable=variable,
        value_label=value_label,
        stripe=stripe,
        card=card,
    )

    assert changed is False
    assert variable.set_calls == 0
    assert value_label.configure_calls == 0
    assert stripe.configure_calls == 0


def test_apply_status_card_if_changed_updates_only_changed_fields() -> None:
    card = GuiStatusCard("Signal", "Needs review", "warning")
    variable = _FakeStringVar("Good ECG/QRS")
    value_label = _FakeWidget(style=status_tone_style("ready"))
    stripe = _FakeWidget(bg=status_tone_color("ready"))

    changed = apply_status_card_if_changed(
        variable=variable,
        value_label=value_label,
        stripe=stripe,
        card=card,
    )

    assert changed is True
    assert variable.value == "Needs review"
    assert variable.set_calls == 1
    assert value_label.values["style"] == status_tone_style("warning")
    assert value_label.configure_calls == 1
    assert stripe.values["bg"] == status_tone_color("warning")
    assert stripe.configure_calls == 1


def test_drain_queue_items_bounds_work_and_preserves_backlog() -> None:
    values: queue.Queue[int] = queue.Queue()
    for value in range(5):
        values.put(value)

    assert drain_queue_items(values, max_items=3) == (0, 1, 2)
    assert drain_queue_items(values, max_items=10) == (3, 4)


def test_drain_queue_items_does_not_consume_when_limit_is_zero() -> None:
    values: queue.Queue[str] = queue.Queue()
    values.put("pending")

    assert drain_queue_items(values, max_items=0) == tuple()
    assert values.get_nowait() == "pending"


def test_display_refresh_key_changes_only_when_visible_display_state_changes() -> None:
    base = display_refresh_key(
        mode="live",
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(),
        autoscale=True,
        sample_index=100,
        loaded_count=0,
        recording_path=None,
    )

    assert base == display_refresh_key(
        mode="live",
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(),
        autoscale=True,
        sample_index=100,
        loaded_count=0,
        recording_path=None,
    )
    assert base != display_refresh_key(
        mode="live",
        display_settings=EcgDisplaySettings(gain=2.0),
        filter_settings=SoftwareFilterSettings(),
        autoscale=True,
        sample_index=100,
        loaded_count=0,
        recording_path=None,
    )
    assert base != display_refresh_key(
        mode="live",
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(notch_enabled=True),
        autoscale=True,
        sample_index=100,
        loaded_count=0,
        recording_path=None,
    )
    assert base != display_refresh_key(
        mode="live",
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(),
        autoscale=True,
        sample_index=101,
        loaded_count=0,
        recording_path=None,
    )


def test_live_render_refresh_key_skips_duplicate_live_frames_only() -> None:
    base = live_render_refresh_key(
        sample_index=100,
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(),
        autoscale=True,
        source="CH2",
        ecg_inverted=False,
    )

    assert base == live_render_refresh_key(
        sample_index=100,
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(),
        autoscale=True,
        source="CH2",
        ecg_inverted=False,
    )
    assert base != live_render_refresh_key(
        sample_index=101,
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(),
        autoscale=True,
        source="CH2",
        ecg_inverted=False,
    )
    assert base != live_render_refresh_key(
        sample_index=100,
        display_settings=EcgDisplaySettings(gain=2.0),
        filter_settings=SoftwareFilterSettings(),
        autoscale=True,
        source="CH2",
        ecg_inverted=False,
    )
    assert base != live_render_refresh_key(
        sample_index=100,
        display_settings=EcgDisplaySettings(),
        filter_settings=SoftwareFilterSettings(notch_enabled=True),
        autoscale=True,
        source="CH2",
        ecg_inverted=False,
    )


def test_axis_limits_changed_uses_small_float_tolerance() -> None:
    assert axis_limits_changed((0.0, 1.0), (0.0, 1.0)) is False
    assert axis_limits_changed((0.0, 1.0), (0.0, 1.0 + 5e-10)) is False
    assert axis_limits_changed((0.0, 1.0), (-0.1, 1.0)) is True
    assert axis_limits_changed((0.0, 1.0), (0.0, 1.1)) is True


def test_set_axis_ylim_if_changed_skips_redundant_matplotlib_writes() -> None:
    axis = _FakeAxis((-1.0, 1.0))

    assert set_axis_ylim_if_changed(axis, (-1.0, 1.0)) is False
    assert axis.set_ylim_calls == 0

    assert set_axis_ylim_if_changed(axis, (-2.0, 2.0)) is True
    assert axis.ylim == (-2.0, 2.0)
    assert axis.set_ylim_calls == 1


def test_set_axis_xlim_if_changed_skips_redundant_matplotlib_writes() -> None:
    axis = _FakeAxis((-1.0, 1.0), xlim=(0.0, 8.0))

    assert set_axis_xlim_if_changed(axis, (0.0, 8.0)) is False
    assert axis.set_xlim_calls == 0

    assert set_axis_xlim_if_changed(axis, (1.0, 9.0)) is True
    assert axis.xlim == (1.0, 9.0)
    assert axis.set_xlim_calls == 1


def test_toolbar_display_hint_text_summarizes_channel_and_display_mode() -> None:
    hint = toolbar_display_hint_text(
        EcgDisplaySettings(time_window_seconds=12.0, gain=2.0, sweep_speed_mm_s=50),
        SoftwareFilterSettings(highpass_enabled=True, notch_enabled=True),
    )

    assert hint == "CH2 Lead I | CH1 Resp | Contact | HP+notch | 2x | 12s | 50 mm/s"


def test_display_scale_reference_label_does_not_claim_voltage_calibration() -> None:
    label = display_scale_reference_label(EcgDisplaySettings(gain=4.0))

    assert label == "Scale ref | 5x"
    assert "mV" not in label


def test_compact_ecg_source_label_keeps_status_cards_short() -> None:
    assert compact_ecg_source_label("CH2") == "CH2"
    assert compact_ecg_source_label("CH1") == "CH1"
    assert compact_ecg_source_label("Auto") == "--"
    assert compact_ecg_source_label(None) == "--"


def test_tick_queue_limits_are_above_normal_streaming_rate() -> None:
    assert MAX_SAMPLES_PER_TICK >= 2 * 500 * 0.05
    assert MAX_LOG_MESSAGES_PER_TICK >= 50


def test_should_apply_control_state_skips_unchanged_state() -> None:
    state = GuiState(connected=True, streaming=True, has_data=True, has_recording_path=True)

    assert should_apply_control_state(None, state) is True
    assert should_apply_control_state(state, state) is False
    assert should_apply_control_state(state, state, force=True) is True
    assert (
        should_apply_control_state(
            state,
            GuiState(connected=True, streaming=False, has_data=True, has_recording_path=True),
        )
        is True
    )


def test_live_ecg_axis_title_keeps_dynamic_counts_out_of_plot_title() -> None:
    title = live_ecg_axis_title("CH2 ECG Lead I (LA-RA)", "raw | 1x | 8s | 25 mm/s", inverted=True)

    assert title == "ECG display: CH2 ECG Lead I (LA-RA) | raw | 1x | 8s | 25 mm/s, inverted"
    assert "R peaks" not in title
    assert "samples" not in title


def test_live_axis_titles_are_static_until_display_mode_changes() -> None:
    titles = live_axis_titles(
        ecg_label="CH2 ECG Lead I (LA-RA)",
        resp_label="CH1 respiration raw",
        contact_label="lead-off/contact status",
        mode="raw | 1x | 8s | 25 mm/s",
        inverted=False,
    )

    assert titles == (
        "ECG display: CH2 ECG Lead I (LA-RA) | raw | 1x | 8s | 25 mm/s",
        "CH1 respiration raw",
        "lead-off/contact status",
    )
    assert all("samples" not in title and "R peaks" not in title for title in titles)


def test_live_redraw_caches_axis_title_updates() -> None:
    import inspect

    from ads1292_studio.app import App

    redraw_source = inspect.getsource(App._redraw_live)
    apply_source = inspect.getsource(App._apply_live_axis_titles)
    init_source = inspect.getsource(App.__init__)

    assert "self.last_live_axis_titles: tuple[str, str, str] | None = None" in init_source
    assert "self._apply_live_axis_titles(display_settings, filter_settings)" in redraw_source
    assert "set_signal_axis_title(" not in redraw_source
    assert "if self.last_live_axis_titles == titles:" in apply_source
    assert "return" in apply_source
    assert "self.last_live_axis_titles = titles" in apply_source


def test_live_redraw_skips_duplicate_render_keys() -> None:
    import inspect

    from ads1292_studio.app import App

    redraw_source = inspect.getsource(App._redraw_live)
    clear_source = inspect.getsource(App._clear_signal_buffers)
    init_source = inspect.getsource(App.__init__)

    assert "self.last_live_render_key: tuple[object, ...] | None = None" in init_source
    assert "render_key = live_render_refresh_key(" in redraw_source
    assert "if self.last_live_render_key == render_key:" in redraw_source
    assert "self.last_live_render_key = render_key" in redraw_source
    assert "self.last_live_render_key = None" in clear_source
    assert redraw_source.index("if self.last_live_render_key == render_key:") < redraw_source.index(
        "build_live_render_frame("
    )
    assert redraw_source.index("if frame is None:") < redraw_source.index("self.last_live_render_key = render_key")
    assert redraw_source.index("build_live_render_frame(") < redraw_source.index("self._clear_empty_plot_state()")


def test_live_redraw_skips_unchanged_y_axis_limit_writes() -> None:
    import inspect

    from ads1292_studio.app import App
    from ads1292_studio.gui_plots import apply_live_render_frame

    redraw_source = inspect.getsource(App._redraw_live)
    apply_source = inspect.getsource(apply_live_render_frame)

    assert "apply_live_render_frame(" in redraw_source
    assert "set_axis_xlim_if_changed(ax, (frame.left, frame.right))" in apply_source
    assert "set_axis_ylim_if_changed(app.ax_live_ecg" in apply_source
    assert "set_axis_ylim_if_changed(app.ax_live_resp" in apply_source
    assert "set_axis_ylim_if_changed(app.ax_live_status" in apply_source
    assert "ax.set_xlim(frame.left, frame.right)" not in apply_source
    assert "self.ax_live_ecg.set_ylim(" not in redraw_source
    assert "self.ax_live_resp.set_ylim(" not in redraw_source
    assert "self.ax_live_status.set_ylim(" not in redraw_source


def test_live_metrics_text_carries_dynamic_runtime_counts() -> None:
    text = live_metrics_text(
        sample_index=1234,
        duration_seconds=2.468,
        ecg_label="CH2 ECG Lead I (LA-RA)",
        heart_rate_bpm=72.4,
        peak_count=5,
    )

    assert text == "samples 1234 | duration 2.5 s | source CH2 ECG Lead I (LA-RA) | HR 72 bpm | R peaks 5"


def test_live_quality_worker_available_skips_when_future_is_running() -> None:
    assert live_quality_worker_available(None) is True
    assert live_quality_worker_available(_FakeFuture(done=True)) is True
    assert live_quality_worker_available(_FakeFuture(done=False)) is False


def test_live_quality_scheduler_checks_sample_count_before_copying_buffers() -> None:
    import inspect

    from ads1292_studio.app import App

    source = inspect.getsource(App._schedule_live_quality_update)

    assert "live_quality_sample_count_ready(" in source
    assert source.index("live_quality_sample_count_ready(") < source.index("ch1_values = tuple(self.ch1)")


def test_gui_control_states_start_with_safe_disabled_defaults() -> None:
    states = gui_control_states(
        connected=False,
        streaming=False,
        has_data=False,
        has_recording_path=False,
    )

    assert states["Start"] == "disabled"
    assert states["Stop"] == "disabled"
    assert states["Export Report"] == "disabled"
    assert states["Export Package"] == "disabled"
    assert states["Load CSV"] == "normal"
    assert states["Batch Compare"] == "normal"
    assert states["Session Index"] == "normal"


def test_gui_control_states_disable_connect_until_a_port_is_available() -> None:
    state = GuiState(
        connected=False,
        streaming=False,
        has_data=False,
        has_recording_path=False,
        has_port=False,
    )

    states = gui_control_states(state=state)

    assert states["Refresh"] == "normal"
    assert states["Connect"] == "disabled"
    assert states["Load CSV"] == "normal"


def test_gui_control_cursors_track_enabled_button_states() -> None:
    states = {
        "Refresh": "normal",
        "Connect": "disabled",
        "Start": "disabled",
        "Load CSV": "normal",
    }

    assert gui_control_cursors(states) == {
        "Refresh": "hand2",
        "Connect": "arrow",
        "Start": "arrow",
        "Load CSV": "hand2",
    }


def test_port_refresh_and_edits_recompute_control_state() -> None:
    import inspect

    from ads1292_studio.app import App
    from ads1292_studio.gui_layout import build_acquisition_toolbar

    refresh_source = inspect.getsource(App.refresh_ports)
    toolbar_source = inspect.getsource(build_acquisition_toolbar)

    assert "self._apply_control_states(force=True)" in refresh_source
    assert "app.port_var.trace_add(\"write\"" in toolbar_source


def test_port_entry_connection_message_tracks_manual_port_edits() -> None:
    assert port_entry_connection_message(
        port_text="",
        connected=False,
        busy=False,
        streaming=False,
    ) == "No ADS1x9x port"
    assert port_entry_connection_message(
        port_text="/dev/cu.usbmodem214301",
        connected=False,
        busy=False,
        streaming=False,
    ) == "Not connected"
    assert port_entry_connection_message(
        port_text="/dev/cu.usbmodem214301",
        connected=True,
        busy=False,
        streaming=False,
    ) is None
    assert port_entry_connection_message(
        port_text="",
        connected=False,
        busy=True,
        streaming=False,
    ) is None


def test_app_reexports_gui_state_helpers_from_focused_module() -> None:
    import inspect

    from ads1292_studio.app import App

    source = inspect.getsource(App)

    assert GuiState.__module__ == "ads1292_studio.gui_state"
    assert GuiStatusCard.__module__ == "ads1292_studio.gui_state"
    assert "class GuiState" not in source
    assert "class GuiStatusCard" not in source


def test_gui_control_states_disable_conflicting_actions_while_loading_csv() -> None:
    state = GuiState(
        connected=True,
        streaming=False,
        has_data=True,
        has_recording_path=True,
        loading_csv=True,
    )

    states = gui_control_states(state=state)

    assert states["Load CSV"] == "disabled"
    assert states["Start"] == "disabled"
    assert states["Export Report"] == "disabled"
    assert gui_workflow_hint(state=state) == "Loading CSV: keep the window open; review plots will update when parsing finishes."


def test_gui_state_busy_is_true_for_connecting_starting_or_loading() -> None:
    assert GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True).busy is True
    assert GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, starting=True).busy is True
    assert GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, loading_csv=True).busy is True
    assert GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False).busy is False


def test_gui_tick_interval_slows_only_when_idle() -> None:
    idle = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False)
    streaming = GuiState(connected=True, streaming=True, has_data=True, has_recording_path=True)
    connecting = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True)
    loading = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, loading_csv=True)
    starting = GuiState(connected=True, streaming=False, has_data=False, has_recording_path=False, starting=True)

    assert gui_tick_interval_ms(idle) == IDLE_TICK_INTERVAL_MS
    assert gui_tick_interval_ms(streaming) == ACTIVE_TICK_INTERVAL_MS
    assert gui_tick_interval_ms(connecting) == ACTIVE_TICK_INTERVAL_MS
    assert gui_tick_interval_ms(loading) == ACTIVE_TICK_INTERVAL_MS
    assert gui_tick_interval_ms(starting) == ACTIVE_TICK_INTERVAL_MS
    assert ACTIVE_TICK_INTERVAL_MS <= 40


def test_gui_control_states_disable_everything_while_connecting() -> None:
    state = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True)

    states = gui_control_states(state=state)

    assert states["Connect"] == "disabled"
    assert states["Start"] == "disabled"
    assert states["Load CSV"] == "disabled"


def test_gui_control_states_disable_everything_while_starting() -> None:
    state = GuiState(connected=True, streaming=False, has_data=False, has_recording_path=False, starting=True)

    states = gui_control_states(state=state)

    assert states["Start"] == "disabled"
    assert states["Stop"] == "disabled"
    assert states["Load CSV"] == "disabled"


def test_gui_workflow_hint_explains_connecting_and_starting() -> None:
    connecting = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True)
    starting = GuiState(connected=True, streaming=False, has_data=False, has_recording_path=False, starting=True)

    assert "Connecting" in gui_workflow_hint(state=connecting)
    assert "Starting" in gui_workflow_hint(state=starting)


def test_gui_status_cards_show_connecting_and_starting_acquisition_values() -> None:
    connecting = GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True)
    starting = GuiState(connected=True, streaming=False, has_data=False, has_recording_path=False, starting=True)

    connecting_cards = {card.label: card.value for card in gui_status_cards(state=connecting)}
    starting_cards = {card.label: card.value for card in gui_status_cards(state=starting)}

    assert connecting_cards["Acquisition"] == "connecting"
    assert starting_cards["Acquisition"] == "starting stream"


def test_gui_control_states_enable_acquisition_after_connection() -> None:
    states = gui_control_states(
        connected=True,
        streaming=False,
        has_data=False,
        has_recording_path=False,
    )

    assert states["Start"] == "normal"
    assert states["Stop"] == "disabled"


def test_gui_control_states_enable_stop_and_report_while_streaming_with_data() -> None:
    states = gui_control_states(
        connected=True,
        streaming=True,
        has_data=True,
        has_recording_path=True,
    )

    assert states["Start"] == "disabled"
    assert states["Stop"] == "normal"
    assert states["Export Report"] == "normal"
    assert states["Export Package"] == "normal"


def test_gui_control_states_allow_report_but_not_package_for_unsaved_loaded_data() -> None:
    states = gui_control_states(
        connected=False,
        streaming=False,
        has_data=True,
        has_recording_path=False,
    )

    assert states["Export Report"] == "normal"
    assert states["Export Package"] == "disabled"


def test_gui_workflow_hint_guides_disconnected_state() -> None:
    hint = gui_workflow_hint(
        connected=False,
        streaming=False,
        has_data=False,
        has_recording_path=False,
    )

    assert hint == "Next: select an ADS1292 port and press Connect, or load an existing CSV."


def test_gui_workflow_hint_guides_missing_port_state() -> None:
    hint = gui_workflow_hint(
        state=GuiState(
            connected=False,
            streaming=False,
            has_data=False,
            has_recording_path=False,
            has_port=False,
        )
    )

    assert hint == "No ADS1292 port detected: plug in the board, press Refresh, or load an existing CSV."


def test_gui_workflow_hint_guides_ready_to_start_state() -> None:
    hint = gui_workflow_hint(
        connected=True,
        streaming=False,
        has_data=False,
        has_recording_path=False,
    )

    assert hint == "Next: press Start to begin acquisition, or load a CSV for offline review."


def test_gui_workflow_hint_guides_streaming_state() -> None:
    hint = gui_workflow_hint(
        connected=True,
        streaming=True,
        has_data=True,
        has_recording_path=True,
    )

    assert hint == "Streaming: monitor signal quality, add events if needed, then press Stop."


def test_gui_workflow_hint_guides_unsaved_loaded_data_state() -> None:
    hint = gui_workflow_hint(
        connected=False,
        streaming=False,
        has_data=True,
        has_recording_path=False,
    )

    assert hint == "Data loaded: export a report; package export needs a saved CSV path."


def test_gui_workflow_hint_guides_packagable_data_state() -> None:
    hint = gui_workflow_hint(
        connected=True,
        streaming=False,
        has_data=True,
        has_recording_path=True,
    )

    assert hint == "Data ready: export a report or package the recording with its sidecars."


def test_gui_status_overview_summarizes_empty_disconnected_state() -> None:
    overview = gui_status_overview(
        connected=False,
        streaming=False,
        has_data=False,
        has_recording_path=False,
    )

    assert overview == (
        "Connection: disconnected\n"
        "Acquisition: idle\n"
        "Data: none loaded\n"
        "Package: unavailable"
    )


def test_gui_status_overview_summarizes_missing_port_state() -> None:
    overview = gui_status_overview(
        state=GuiState(
            connected=False,
            streaming=False,
            has_data=False,
            has_recording_path=False,
            has_port=False,
        )
    )

    assert overview == (
        "Connection: no port\n"
        "Acquisition: idle\n"
        "Data: none loaded\n"
        "Package: unavailable"
    )


def test_gui_status_overview_summarizes_connected_idle_state() -> None:
    overview = gui_status_overview(
        connected=True,
        streaming=False,
        has_data=False,
        has_recording_path=False,
    )

    assert overview == (
        "Connection: connected\n"
        "Acquisition: ready to start\n"
        "Data: none loaded\n"
        "Package: unavailable"
    )


def test_gui_status_overview_summarizes_streaming_with_saved_data() -> None:
    overview = gui_status_overview(
        connected=True,
        streaming=True,
        has_data=True,
        has_recording_path=True,
    )

    assert overview == (
        "Connection: connected\n"
        "Acquisition: streaming\n"
        "Data: live or loaded\n"
        "Package: ready"
    )


def test_gui_status_overview_summarizes_loaded_unsaved_data() -> None:
    overview = gui_status_overview(
        connected=False,
        streaming=False,
        has_data=True,
        has_recording_path=False,
    )

    assert overview == (
        "Connection: disconnected\n"
        "Acquisition: idle\n"
        "Data: live or loaded\n"
        "Package: needs saved CSV"
    )


def test_gui_status_cards_expose_scan_friendly_disconnected_state() -> None:
    cards = gui_status_cards(
        connected=False,
        streaming=False,
        has_data=False,
        has_recording_path=False,
    )

    assert [(card.label, card.value, card.tone) for card in cards] == [
        ("Connection", "disconnected", "warning"),
        ("Acquisition", "idle", "neutral"),
        ("Data", "none loaded", "neutral"),
        ("Package", "unavailable", "neutral"),
    ]


def test_gui_status_cards_expose_missing_port_state() -> None:
    cards = gui_status_cards(
        state=GuiState(
            connected=False,
            streaming=False,
            has_data=False,
            has_recording_path=False,
            has_port=False,
        )
    )

    assert cards[0] == GuiStatusCard("Connection", "no port", "warning")


def test_gui_status_cards_expose_scan_friendly_streaming_state() -> None:
    cards = gui_status_cards(
        connected=True,
        streaming=True,
        has_data=True,
        has_recording_path=True,
    )

    assert [(card.label, card.value, card.tone) for card in cards] == [
        ("Connection", "connected", "ready"),
        ("Acquisition", "streaming", "running"),
        ("Data", "live or loaded", "ready"),
        ("Package", "ready", "ready"),
    ]


def test_gui_status_cards_mark_unsaved_loaded_data_as_package_warning() -> None:
    cards = gui_status_cards(
        connected=False,
        streaming=False,
        has_data=True,
        has_recording_path=False,
    )

    assert cards[2].label == "Data"
    assert cards[2].tone == "ready"
    assert cards[3].label == "Package"
    assert cards[3].value == "needs saved CSV"
    assert cards[3].tone == "warning"


def test_status_tone_style_maps_known_and_unknown_tones() -> None:
    assert status_tone_style("ready") == "Ready.Status.TLabel"
    assert status_tone_style("running") == "Running.Status.TLabel"
    assert status_tone_style("warning") == "Warning.Status.TLabel"
    assert status_tone_style("unexpected") == "Neutral.Status.TLabel"


def test_status_label_spec_makes_card_values_easy_to_scan() -> None:
    assert status_label_spec() == {
        "font": ("Aptos", 12, "bold"),
        "padding": (8, 4),
        "backgrounds": {
            "ready": "#E9F6EE",
            "running": "#EAF1FF",
            "warning": "#FFF4E3",
            "neutral": "#EEF3FA",
        },
        "foregrounds": {
            "ready": "#1E7A46",
            "running": "#2F6FED",
            "warning": "#A76400",
            "neutral": "#657084",
        },
    }


def test_header_connection_style_maps_known_and_unknown_tones() -> None:
    assert header_connection_style("ready") == "Ready.Connection.TLabel"
    assert header_connection_style("running") == "Running.Connection.TLabel"
    assert header_connection_style("warning") == "Warning.Connection.TLabel"
    assert header_connection_style("unexpected") == "Neutral.Connection.TLabel"


def test_header_connection_tone_tracks_acquisition_state() -> None:
    assert header_connection_tone(connected=False, streaming=False) == "warning"
    assert header_connection_tone(connected=True, streaming=False) == "ready"
    assert header_connection_tone(connected=True, streaming=True) == "running"
    assert header_connection_tone(
        state=GuiState(connected=False, streaming=False, has_data=False, has_recording_path=False, connecting=True)
    ) == "running"
    assert header_connection_tone(
        state=GuiState(connected=True, streaming=False, has_data=False, has_recording_path=False, starting=True)
    ) == "running"


def test_status_tone_color_maps_card_stripe_colors() -> None:
    assert status_tone_color("ready") == "#1E7A46"
    assert status_tone_color("running") == "#2F6FED"
    assert status_tone_color("warning") == "#A76400"
    assert status_tone_color("neutral") == "#A9B4C3"
    assert status_tone_color("unexpected") == "#A9B4C3"


def test_gui_state_snapshot_drives_all_status_helpers() -> None:
    state = GuiState(
        connected=True,
        streaming=True,
        has_data=True,
        has_recording_path=True,
    )

    assert gui_control_states(state=state)["Stop"] == "normal"
    assert gui_workflow_hint(state=state) == "Streaming: monitor signal quality, add events if needed, then press Stop."
    assert gui_status_overview(state=state) == (
        "Connection: connected\n"
        "Acquisition: streaming\n"
        "Data: live or loaded\n"
        "Package: ready"
    )
    assert [(card.label, card.value, card.tone) for card in gui_status_cards(state=state)] == [
        ("Connection", "connected", "ready"),
        ("Acquisition", "streaming", "running"),
        ("Data", "live or loaded", "ready"),
        ("Package", "ready", "ready"),
    ]


def test_gui_state_reports_package_readiness() -> None:
    unsaved = GuiState(
        connected=False,
        streaming=False,
        has_data=True,
        has_recording_path=False,
    )
    saved = GuiState(
        connected=False,
        streaming=False,
        has_data=True,
        has_recording_path=True,
    )

    assert unsaved.package_ready is False
    assert saved.package_ready is True


def test_gui_signal_quality_cards_expose_real_recording_summary() -> None:
    cards = gui_signal_quality_cards(
        quality_label="Good ECG/QRS",
        ecg_source="CH2",
        contact_ok_percent=99.9376,
        lead_off_bad_samples=28,
        r_peaks=129,
        hr_median_bpm=86.705,
        baseline_drift_counts=44.0,
        noise_rms_counts=50.461,
        peak_to_peak_counts=8709.0,
    )

    assert [(card.label, card.value, card.tone) for card in cards] == [
        ("Signal", "Good ECG/QRS | CH2", "ready"),
        ("Contact", "99.9% OK | 28 bad", "ready"),
        ("Heart rate", "86.7 bpm | 129 R", "ready"),
        ("Artifacts", "drift 44 | noise 50.5 | p2p 8709 ct", "neutral"),
    ]


def test_gui_signal_quality_cards_warn_when_loaded_signal_needs_review() -> None:
    cards = gui_signal_quality_cards(
        quality_label="Needs review",
        ecg_source="CH1",
        contact_ok_percent=88.0,
        lead_off_bad_samples=1200,
        r_peaks=1,
        hr_median_bpm=0.0,
        baseline_drift_counts=300.0,
        noise_rms_counts=220.0,
        peak_to_peak_counts=7000.0,
    )

    assert [(card.label, card.value, card.tone) for card in cards] == [
        ("Signal", "Needs review | CH1", "warning"),
        ("Contact", "88.0% OK | 1200 bad", "warning"),
        ("Heart rate", "-- bpm | 1 R", "warning"),
        ("Artifacts", "drift 300 | noise 220.0 | p2p 7000 ct", "warning"),
    ]


def test_gui_signal_quality_cards_have_empty_defaults() -> None:
    cards = gui_signal_quality_cards()

    assert [(card.label, card.value, card.tone) for card in cards] == [
        ("Signal", "not reviewed", "neutral"),
        ("Contact", "--", "neutral"),
        ("Heart rate", "--", "neutral"),
        ("Artifacts", "--", "neutral"),
    ]
