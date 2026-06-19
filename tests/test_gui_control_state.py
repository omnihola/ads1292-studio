from ads1292_studio.app import (
    gui_control_states,
    gui_status_cards,
    gui_status_overview,
    gui_workflow_hint,
    status_tone_style,
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
