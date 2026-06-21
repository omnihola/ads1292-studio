import json
from pathlib import Path

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings
from ads1292_studio.processing import (
    PROCESSING_SCHEMA,
    build_processing_settings,
    read_processing_json,
    write_processing_json,
)


def test_processing_settings_round_trip_preserves_display_and_filter_context(
    tmp_path: Path,
) -> None:
    path = tmp_path / "recording.processing.json"
    processing = build_processing_settings(
        display_settings=EcgDisplaySettings(time_window_seconds=12.0, gain=2.0, sweep_speed_mm_s=50),
        filter_settings=SoftwareFilterSettings(
            highpass_enabled=True,
            notch_enabled=True,
            lowpass_enabled=True,
            bandpass_enabled=False,
        ),
        sample_rate_hz=500.0,
        ecg_inverted=False,
        smoothing_window=11,
    )

    write_processing_json(path, processing)

    payload = json.loads(path.read_text())
    loaded = read_processing_json(path)
    assert payload["schema"] == PROCESSING_SCHEMA
    assert payload["display"]["time_window_seconds"] == 12.0
    assert payload["display"]["gain"] == 2.0
    assert payload["display"]["sweep_speed_mm_s"] == 50
    assert payload["software_filters"]["highpass_enabled"] is True
    assert payload["software_filters"]["notch_hz"] == 60.0
    assert payload["software_filters"]["lowpass_hz"] == 40.0
    assert payload["processing_notes"] == "display settings only; raw CSV samples are unchanged"
    assert loaded == processing.normalized()
