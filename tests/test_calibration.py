from pathlib import Path

import numpy as np

from ads1292_studio.calibration import (
    Calibration,
    LiveStreamCalibration,
    calibration_template,
    counts_to_microvolts,
    live_stream_peak_to_peak_counts,
    read_calibration_json,
    summarize_live_stream_calibration,
    write_calibration_json,
)


def test_calibration_converts_counts_to_microvolts() -> None:
    calibration = Calibration(vref_mv=2420.0, pga_gain=6.0, adc_bits=24)

    values = counts_to_microvolts(np.array([0.0, 1000.0, -1000.0]), calibration)

    assert values[0] == 0.0
    assert 48.0 < values[1] < 48.2
    assert -48.2 < values[2] < -48.0
    assert 0.0480 < calibration.microvolts_per_count < 0.0482


def test_calibration_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "calibration.json"
    calibration = Calibration(vref_mv=2400.0, pga_gain=12.0, adc_bits=24, label="bench-gain-12")

    write_calibration_json(path, calibration)
    loaded = read_calibration_json(path)

    assert loaded == calibration


def test_calibration_normalizes_invalid_values() -> None:
    calibration = Calibration(vref_mv=-1.0, pga_gain=0.0, adc_bits=1, label=" ").normalized()

    assert calibration.vref_mv == 2420.0
    assert calibration.pga_gain == 6.0
    assert calibration.adc_bits == 24
    assert calibration.label == "ADS1292 default"


def test_calibration_template_is_writable(tmp_path: Path) -> None:
    path = tmp_path / "template.json"

    write_calibration_json(path, calibration_template())

    assert read_calibration_json(path).label == "ADS1292 default"


def test_summarize_live_stream_calibration_uses_run_peak_to_peak_counts() -> None:
    calibration = summarize_live_stream_calibration(
        (1064.0, 1064.5, 1064.0, 1065.0, 1063.5),
        test_signal_pp_uv=2016.6666666667,
    )

    assert isinstance(calibration, LiveStreamCalibration)
    assert calibration.runs == 5
    assert 1.89 < calibration.mean_uv_per_count < 1.90
    assert calibration.std_uv_per_count < 0.002
    assert calibration.scale_type == "live_processed"


def test_live_stream_peak_to_peak_counts_uses_robust_low_high_levels() -> None:
    values = [0.0, 1.0, -1.0, 1064.0, 1065.0, 1063.0] * 20

    peak_to_peak = live_stream_peak_to_peak_counts(values)

    assert 1063.0 <= peak_to_peak <= 1067.0


def test_microvolts_per_count_matches_datasheet_formula():
    # ADS1292: 1 LSB = (Vref/PGA) / 2^(bits-1). For 2420 mV, PGA 6, 24-bit:
    from ads1292_studio.calibration import Calibration

    expected = 2420.0 * 1000.0 / (6.0 * 2 ** 23)
    assert Calibration().microvolts_per_count == expected
