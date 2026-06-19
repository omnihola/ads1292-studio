from ads1292_studio.app import (
    DEFAULT_ECG_INVERTED,
    DEFAULT_FILTER_ENABLED,
    GuiState,
    ads1292r_channel_label,
    ads1292r_secondary_channel_label,
    display_signal_values,
    gui_control_states,
    gui_signal_quality_cards,
    gui_status_cards,
    gui_status_overview,
    gui_workflow_hint,
    status_tone_color,
    status_tone_style,
)
import numpy as np


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
        ("Signal", "Good ECG/QRS on CH2 ECG Lead I (LA-RA)", "ready"),
        ("Contact", "99.9% OK, 28 bad", "ready"),
        ("Heart rate", "86.7 bpm, 129 R", "ready"),
        ("Artifacts", "drift 44 ct, noise 50.5 ct, p2p 8709 ct", "neutral"),
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
        ("Signal", "Needs review on CH1 Respiration raw", "warning"),
        ("Contact", "88.0% OK, 1200 bad", "warning"),
        ("Heart rate", "-- bpm, 1 R", "warning"),
        ("Artifacts", "drift 300 ct, noise 220.0 ct, p2p 7000 ct", "warning"),
    ]


def test_gui_signal_quality_cards_have_empty_defaults() -> None:
    cards = gui_signal_quality_cards()

    assert [(card.label, card.value, card.tone) for card in cards] == [
        ("Signal", "not reviewed", "neutral"),
        ("Contact", "--", "neutral"),
        ("Heart rate", "--", "neutral"),
        ("Artifacts", "--", "neutral"),
    ]
