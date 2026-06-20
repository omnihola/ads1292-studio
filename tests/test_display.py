import numpy as np

from ads1292_studio.display import (
    EcgDisplaySettings,
    SoftwareFilterSettings,
    display_gain_labels,
    display_mode_label,
    display_window_labels,
    ecg_paper_grid_key,
    ecg_paper_grid_spec,
    parse_display_gain,
    parse_display_window,
    parse_sweep_speed,
    sweep_speed_labels,
)
from ads1292_studio.signal_processing import apply_software_filters


def test_display_choices_use_ecg_workstation_labels() -> None:
    assert display_window_labels() == ("4 s", "8 s", "12 s", "16 s")
    assert display_gain_labels() == ("0.5x", "1x", "2x", "5x")
    assert sweep_speed_labels() == ("25 mm/s", "50 mm/s")


def test_display_parsers_snap_to_supported_values() -> None:
    assert parse_display_window("11 s") == 12.0
    assert parse_display_gain("4x") == 5.0
    assert parse_sweep_speed("49 mm/s") == 50


def test_ecg_paper_grid_matches_sweep_speed() -> None:
    speed_25 = ecg_paper_grid_spec(EcgDisplaySettings(sweep_speed_mm_s=25))
    speed_50 = ecg_paper_grid_spec(EcgDisplaySettings(sweep_speed_mm_s=50))

    assert speed_25["major_x_seconds"] == 0.2
    assert speed_25["minor_x_seconds"] == 0.04
    assert speed_50["major_x_seconds"] == 0.1
    assert speed_50["minor_x_seconds"] == 0.02


def test_ecg_paper_grid_uses_soft_modern_palette() -> None:
    spec = ecg_paper_grid_spec(EcgDisplaySettings())

    assert spec["major_color"] == "#F6CACA"
    assert spec["minor_color"] == "#FCE9E9"
    assert spec["major_alpha"] == 0.42
    assert spec["minor_alpha"] == 0.32


def test_ecg_paper_grid_key_changes_only_when_spacing_changes() -> None:
    settings = EcgDisplaySettings(sweep_speed_mm_s=25)

    key = ecg_paper_grid_key(settings, (-10.0, 10.0))

    assert key == ecg_paper_grid_key(EcgDisplaySettings(sweep_speed_mm_s=25), (-10.0, 10.0))
    assert key != ecg_paper_grid_key(EcgDisplaySettings(sweep_speed_mm_s=50), (-10.0, 10.0))
    assert key != ecg_paper_grid_key(settings, (-50.0, 50.0))


def test_display_mode_label_lists_active_software_filters() -> None:
    settings = EcgDisplaySettings(time_window_seconds=12.0, gain=2.0, sweep_speed_mm_s=50)

    assert display_mode_label(settings, SoftwareFilterSettings()) == "raw | 2x | 12s | 50 mm/s"
    assert (
        display_mode_label(
            settings,
            SoftwareFilterSettings(highpass_enabled=True, notch_enabled=True, lowpass_enabled=True),
        )
        == "HP+notch+LP | 2x | 12s | 50 mm/s"
    )
    assert (
        display_mode_label(settings, SoftwareFilterSettings(highpass_enabled=True, bandpass_enabled=True))
        == "QRS | 2x | 12s | 50 mm/s"
    )


def test_software_filters_are_independently_switchable() -> None:
    sample_rate_hz = 500.0
    t = np.arange(0, 2, 1 / sample_rate_hz)
    values = np.sin(2 * np.pi * 1 * t) + 0.25 * np.sin(2 * np.pi * 60 * t)

    raw = apply_software_filters(values, sample_rate_hz, SoftwareFilterSettings())
    filtered = apply_software_filters(
        values,
        sample_rate_hz,
        SoftwareFilterSettings(highpass_enabled=True, notch_enabled=True, lowpass_enabled=True),
    )

    np.testing.assert_allclose(raw, values)
    assert filtered.shape == values.shape
    assert float(np.std(filtered - values)) > 0.01
