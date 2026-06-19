from ads1292_studio.quality import QualityMetrics
from pathlib import Path

from ads1292_studio.quality_gate import (
    QualityGate,
    evaluate_quality_gate,
    quality_gate_template,
    read_quality_gate_json,
    write_quality_gate_json,
)


def _metrics(**overrides) -> QualityMetrics:
    values = {
        "sample_count": 5000,
        "duration_seconds": 10.0,
        "ecg_source": "CH2",
        "contact_ok_percent": 99.5,
        "lead_off_bad_samples": 0,
        "r_peaks": 12,
        "hr_median_bpm": 72.0,
        "hr_min_bpm": 68.0,
        "hr_max_bpm": 76.0,
        "qrs_clear": True,
        "p_tentative": False,
        "t_tentative": False,
        "score_ch1": 1.0,
        "score_ch2": 10.0,
        "baseline_drift_counts": 5.0,
        "noise_rms_counts": 2.0,
        "peak_to_peak_counts": 700.0,
    }
    values.update(overrides)
    return QualityMetrics(**values)


def test_quality_gate_passes_good_recording() -> None:
    result = evaluate_quality_gate(_metrics(), QualityGate())

    assert result.passed is True
    assert result.failures == tuple()
    assert result.label == "Pass"


def test_quality_gate_fails_contact_qrs_and_duration() -> None:
    result = evaluate_quality_gate(
        _metrics(duration_seconds=3.0, contact_ok_percent=80.0, qrs_clear=False, r_peaks=2),
        QualityGate(min_duration_seconds=8.0, min_contact_ok_percent=95.0, min_r_peaks=5),
    )

    assert result.passed is False
    assert "duration 3.00s < 8.00s" in result.failures
    assert "contact 80.00% < 95.00%" in result.failures
    assert "QRS not clear" in result.failures
    assert "R peaks 2 < 5" in result.failures


def test_quality_gate_fails_artifact_thresholds() -> None:
    result = evaluate_quality_gate(
        _metrics(baseline_drift_counts=250.0, noise_rms_counts=60.0, peak_to_peak_counts=5000.0),
        QualityGate(max_baseline_drift_counts=100.0, max_noise_rms_counts=25.0, max_peak_to_peak_counts=2500.0),
    )

    assert result.passed is False
    assert "baseline drift 250.0 counts > 100.0 counts" in result.failures
    assert "noise RMS 60.0 counts > 25.0 counts" in result.failures
    assert "peak-to-peak 5000.0 counts > 2500.0 counts" in result.failures


def test_quality_gate_json_round_trip_preserves_optional_artifact_limits(tmp_path: Path) -> None:
    path = tmp_path / "gate.quality-gate.json"
    gate = QualityGate(
        min_duration_seconds=30.0,
        min_contact_ok_percent=98.0,
        min_r_peaks=20,
        min_hr_bpm=45.0,
        max_hr_bpm=150.0,
        require_qrs_clear=False,
        max_baseline_drift_counts=500.0,
        max_noise_rms_counts=1200.0,
        max_peak_to_peak_counts=None,
    )

    write_quality_gate_json(path, gate)
    loaded = read_quality_gate_json(path)

    assert loaded == gate


def test_quality_gate_template_is_default_gate() -> None:
    assert quality_gate_template() == QualityGate()
