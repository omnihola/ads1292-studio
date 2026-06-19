from ads1292_studio.app import _quality_gate_from_values, _quality_gate_to_values
from ads1292_studio.quality_gate import QualityGate


def test_quality_gate_from_gui_values_parses_optional_artifact_limits() -> None:
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
    values = _quality_gate_to_values(QualityGate(max_baseline_drift_counts=None, max_noise_rms_counts=1000.0))

    assert values["max_baseline_drift_counts"] == ""
    assert values["max_noise_rms_counts"] == "1000"
    assert values["require_qrs_clear"] is True
