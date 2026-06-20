from ads1292_studio.app import (
    _calibration_from_values,
    _format_protocol_steps,
    _metadata_from_values,
    _parse_protocol_steps,
    _protocol_from_values,
    _quality_gate_from_values,
    _quality_gate_to_values,
)
from ads1292_studio.calibration import Calibration
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.protocol import ProtocolStep
from ads1292_studio.quality_gate import QualityGate


def test_quality_gate_from_gui_values_parses_optional_artifact_limits() -> None:
    assert _quality_gate_from_values.__module__ == "ads1292_studio.gui_forms"

    gate = _quality_gate_from_values(
        {
            "min_duration_seconds": "30",
            "min_contact_ok_percent": "98",
            "min_r_peaks": "20",
            "min_hr_bpm": "45",
            "max_hr_bpm": "150",
            "require_qrs_clear": False,
            "max_baseline_drift_counts": "500",
            "max_noise_rms_counts": "",
            "max_peak_to_peak_counts": "30000",
        }
    )

    assert gate == QualityGate(
        min_duration_seconds=30.0,
        min_contact_ok_percent=98.0,
        min_r_peaks=20,
        min_hr_bpm=45.0,
        max_hr_bpm=150.0,
        require_qrs_clear=False,
        max_baseline_drift_counts=500.0,
        max_noise_rms_counts=None,
        max_peak_to_peak_counts=30000.0,
    )


def test_quality_gate_to_gui_values_uses_blank_optional_limits() -> None:
    assert _quality_gate_to_values.__module__ == "ads1292_studio.gui_forms"

    values = _quality_gate_to_values(QualityGate(max_baseline_drift_counts=None, max_noise_rms_counts=1000.0))

    assert values["max_baseline_drift_counts"] == ""
    assert values["max_noise_rms_counts"] == "1000"
    assert values["require_qrs_clear"] is True


def test_protocol_steps_text_round_trips_through_gui_form_helpers() -> None:
    assert _format_protocol_steps.__module__ == "ads1292_studio.gui_forms"
    assert _parse_protocol_steps.__module__ == "ads1292_studio.gui_forms"

    steps = (
        ProtocolStep(0.0, 10.0, "baseline", "sit still").normalized(),
        ProtocolStep(10.0, 5.0, "motion", "turn head").normalized(),
    )

    text = _format_protocol_steps(steps)

    assert _parse_protocol_steps(text) == steps


def test_metadata_calibration_and_protocol_helpers_live_in_gui_forms() -> None:
    assert _metadata_from_values.__module__ == "ads1292_studio.gui_forms"
    assert _calibration_from_values.__module__ == "ads1292_studio.gui_forms"
    assert _protocol_from_values.__module__ == "ads1292_studio.gui_forms"

    metadata = _metadata_from_values(
        session_id=" run-1 ",
        subject_id="",
        electrode=" motac ",
        montage="Lead I",
        operator="J",
        notes=" quiet ",
    )
    calibration = _calibration_from_values(label=" bench ", vref_mv="2400", pga_gain="12")
    protocol = _protocol_from_values(
        name="ecg check",
        objective="validate",
        steps_text="0,5,baseline,sit still",
        acceptance_notes="review",
    )

    assert metadata == SessionMetadata("run-1", "anonymous", "motac", "Lead I", "J", "quiet")
    assert calibration == Calibration(vref_mv=2400.0, pga_gain=12.0, adc_bits=24, label="bench")
    assert protocol.steps == (ProtocolStep(0.0, 5.0, "baseline", "sit still"),)
