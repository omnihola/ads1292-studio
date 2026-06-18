from ads1292_studio.quality import QualityMetrics
from ads1292_studio.quality_gate import QualityGate, evaluate_quality_gate


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
