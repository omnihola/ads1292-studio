from pathlib import Path

import numpy as np

from ads1292_studio.calibration import (
    Calibration,
    calibration_template,
    counts_to_microvolts,
    read_calibration_json,
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
