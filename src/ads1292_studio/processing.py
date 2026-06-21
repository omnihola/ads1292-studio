from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from ads1292_studio.display import EcgDisplaySettings, SoftwareFilterSettings


PROCESSING_SCHEMA = "ads1292-processing-settings-v1"
PROCESSING_NOTES = "display settings only; raw CSV samples are unchanged"


@dataclass(frozen=True)
class RecordingProcessingSettings:
    schema: str = PROCESSING_SCHEMA
    display: dict[str, float | int] | None = None
    software_filters: dict[str, bool | float] | None = None
    sample_rate_hz: float = 500.0
    ecg_inverted: bool = False
    smoothing_window: int = 11
    processing_notes: str = PROCESSING_NOTES

    def normalized(self) -> "RecordingProcessingSettings":
        display_settings = _display_from_dict(self.display).normalized()
        filter_settings = _filters_from_dict(self.software_filters)
        return RecordingProcessingSettings(
            schema=self.schema.strip() or PROCESSING_SCHEMA,
            display=asdict(display_settings),
            software_filters=asdict(filter_settings),
            sample_rate_hz=float(self.sample_rate_hz) if self.sample_rate_hz > 0 else 500.0,
            ecg_inverted=bool(self.ecg_inverted),
            smoothing_window=max(1, int(self.smoothing_window)),
            processing_notes=self.processing_notes.strip() or PROCESSING_NOTES,
        )


def build_processing_settings(
    *,
    display_settings: EcgDisplaySettings | None = None,
    filter_settings: SoftwareFilterSettings | None = None,
    sample_rate_hz: float = 500.0,
    ecg_inverted: bool = False,
    smoothing_window: int = 11,
) -> RecordingProcessingSettings:
    display = (display_settings or EcgDisplaySettings()).normalized()
    filters = filter_settings or SoftwareFilterSettings()
    return RecordingProcessingSettings(
        display=asdict(display),
        software_filters=asdict(filters),
        sample_rate_hz=sample_rate_hz,
        ecg_inverted=ecg_inverted,
        smoothing_window=smoothing_window,
    ).normalized()


def read_processing_json(path: Path | str) -> RecordingProcessingSettings:
    data = json.loads(Path(path).read_text())
    allowed = {field_name for field_name in RecordingProcessingSettings.__dataclass_fields__}
    filtered = {key: value for key, value in data.items() if key in allowed}
    return RecordingProcessingSettings(**filtered).normalized()


def write_processing_json(path: Path | str, processing: RecordingProcessingSettings) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(processing.normalized()), indent=2) + "\n")


def _display_from_dict(values: dict[str, Any] | None) -> EcgDisplaySettings:
    values = values or {}
    return EcgDisplaySettings(
        time_window_seconds=float(values.get("time_window_seconds", 8.0) or 8.0),
        gain=float(values.get("gain", 1.0) or 1.0),
        sweep_speed_mm_s=int(float(values.get("sweep_speed_mm_s", 25) or 25)),
    )


def _filters_from_dict(values: dict[str, Any] | None) -> SoftwareFilterSettings:
    values = values or {}
    return SoftwareFilterSettings(
        highpass_enabled=bool(values.get("highpass_enabled", False)),
        notch_enabled=bool(values.get("notch_enabled", False)),
        lowpass_enabled=bool(values.get("lowpass_enabled", False)),
        bandpass_enabled=bool(values.get("bandpass_enabled", False)),
        highpass_hz=float(values.get("highpass_hz", 0.5) or 0.5),
        notch_hz=float(values.get("notch_hz", 60.0) or 60.0),
        lowpass_hz=float(values.get("lowpass_hz", 40.0) or 40.0),
    )
