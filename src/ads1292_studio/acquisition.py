from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from ads1292_studio.calibration import Calibration, LiveStreamCalibration


ACQUISITION_SCHEMA = "ads1292-acquisition-provenance-v1"
LIVE_CSV_SCHEMA = "ads1292-studio-live-stream-v1"
RAW_CSV_SCHEMA = "ads1292-studio-raw-adc-v1"


@dataclass(frozen=True)
class AcquisitionProvenance:
    schema: str = ACQUISITION_SCHEMA
    csv_name: str = ""
    csv_schema: str = LIVE_CSV_SCHEMA
    acquisition_mode: str = "live_stream"
    port: str = ""
    sample_rate_hz: float = 500.0
    started_at: str = ""
    channel_map: dict[str, str] = field(default_factory=dict)
    raw_adc: dict[str, Any] = field(default_factory=dict)
    live_calibration: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "AcquisitionProvenance":
        mode = _normalized_mode(self.acquisition_mode)
        csv_schema = RAW_CSV_SCHEMA if mode == "raw_adc_24bit" else LIVE_CSV_SCHEMA
        return AcquisitionProvenance(
            schema=self.schema.strip() or ACQUISITION_SCHEMA,
            csv_name=self.csv_name.strip(),
            csv_schema=csv_schema,
            acquisition_mode=mode,
            port=self.port.strip(),
            sample_rate_hz=float(self.sample_rate_hz) if self.sample_rate_hz > 0 else 500.0,
            started_at=self.started_at.strip(),
            channel_map=_clean_string_map(self.channel_map) or default_channel_map(),
            raw_adc=dict(self.raw_adc),
            live_calibration=dict(self.live_calibration),
        )


def default_channel_map() -> dict[str, str]:
    return {
        "ch1_counts": "CH1 respiration/raw impedance",
        "ch2_counts": "CH2 ECG Lead I (LA-RA)",
        "status_byte": "ADS1x9x status byte",
        "lead_off_bits": "lead-off/contact status low nibble",
    }


def build_acquisition_provenance(
    *,
    csv_path: Path | str,
    acquisition_mode: str,
    port: str,
    sample_rate_hz: float,
    calibration: Calibration | None,
    live_calibration: LiveStreamCalibration | None,
    started_at: str,
) -> AcquisitionProvenance:
    csv = Path(csv_path)
    normalized_mode = _normalized_mode(acquisition_mode)
    raw_calibration = (calibration or Calibration()).normalized()
    normalized_live = live_calibration.normalized() if live_calibration else None
    return AcquisitionProvenance(
        csv_name=csv.name,
        csv_schema=RAW_CSV_SCHEMA if normalized_mode == "raw_adc_24bit" else LIVE_CSV_SCHEMA,
        acquisition_mode=normalized_mode,
        port=port,
        sample_rate_hz=sample_rate_hz,
        started_at=started_at,
        channel_map=default_channel_map(),
        raw_adc={
            "vref_mv": raw_calibration.vref_mv,
            "pga_gain": raw_calibration.pga_gain,
            "adc_bits": raw_calibration.adc_bits,
            "raw_lsb_uv_per_count": raw_calibration.microvolts_per_count,
            "label": raw_calibration.label,
        },
        live_calibration=_live_calibration_entry(normalized_live),
    ).normalized()


def read_acquisition_json(path: Path | str) -> AcquisitionProvenance:
    data = json.loads(Path(path).read_text())
    allowed = {field_name for field_name in AcquisitionProvenance.__dataclass_fields__}
    filtered = {key: value for key, value in data.items() if key in allowed}
    return AcquisitionProvenance(**filtered).normalized()


def write_acquisition_json(path: Path | str, provenance: AcquisitionProvenance) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = provenance.normalized()
    output.write_text(json.dumps(asdict(normalized), indent=2) + "\n")


def _normalized_mode(value: str) -> str:
    text = str(value).strip().lower()
    if text.startswith("acquisitionmode."):
        text = text.split(".", 1)[1]
    if text.startswith("raw"):
        return "raw_adc_24bit"
    return "live_stream"


def _clean_string_map(values: dict[str, str]) -> dict[str, str]:
    return {
        str(key).strip(): str(value).strip()
        for key, value in values.items()
        if str(key).strip() and str(value).strip()
    }


def _live_calibration_entry(calibration: LiveStreamCalibration | None) -> dict[str, Any]:
    if calibration is None:
        return {}
    return {
        "mean_uv_per_count": calibration.mean_uv_per_count,
        "std_uv_per_count": calibration.std_uv_per_count,
        "cv_percent": calibration.cv_percent,
        "runs": calibration.runs,
        "test_signal_pp_uv": calibration.test_signal_pp_uv,
        "scale_type": calibration.scale_type,
    }
