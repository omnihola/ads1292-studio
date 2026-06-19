from ads1292_studio.app import gui_control_states, gui_workflow_hint


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
