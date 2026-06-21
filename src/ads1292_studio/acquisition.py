from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from ads1292_studio.calibration import Calibration, LiveStreamCalibration
from ads1292_studio.csv_io import CANONICAL_HEADER, LIVE_CALIBRATION_COLUMNS, RAW_HEADER


ACQUISITION_SCHEMA = "ads1292-acquisition-provenance-v1"
LIVE_CSV_SCHEMA = "ads1292-studio-live-stream-v1"
RAW_CSV_SCHEMA = "ads1292-studio-raw-adc-v1"
TIMESTAMP_REFERENCE = "relative_seconds_from_recording_start"

_CSV_COLUMN_UNITS = {
    "timestamp": "s",
    "ch1_counts": "live_stream_count",
    "ch2_counts": "live_stream_count",
    "board_heart_rate": "bpm",
    "board_respiration_rate": "breaths/min",
    "status_byte": "bitfield",
    "lead_off_bits": "bitfield",
    "live_scale_uv_per_count": "uV/count",
    "live_scale_std_uv_per_count": "uV/count",
    "live_scale_cv_percent": "%",
    "live_scale_runs": "count",
    "live_test_signal_pp_uv": "uV",
    "live_scale_type": "text",
    "sample_index": "sample",
    "ch1_raw24": "ADC count",
    "ch2_raw24": "ADC count",
    "ch1_uv": "uV",
    "ch2_uv": "uV",
    "vref_mv": "mV",
    "pga_gain": "V/V",
    "adc_bits": "bit",
    "raw_lsb_uv_per_count": "uV/count",
    "acquisition_mode": "text",
}

_CSV_COLUMN_DESCRIPTIONS = {
    "timestamp": "Relative seconds from recording start.",
    "ch1_counts": "CH1 respiration/raw impedance",
    "ch2_counts": "CH2 ECG Lead I (LA-RA)",
    "board_heart_rate": "Heart rate reported by ADS1x9x ECG-FE firmware.",
    "board_respiration_rate": "Respiration rate reported by ADS1x9x ECG-FE firmware.",
    "status_byte": "ADS1x9x status byte from the USB stream.",
    "lead_off_bits": "Low-nibble lead-off/contact status bits.",
    "live_scale_uv_per_count": "Live-stream calibration mean scale.",
    "live_scale_std_uv_per_count": "Live-stream calibration scale standard deviation.",
    "live_scale_cv_percent": "Live-stream calibration coefficient of variation.",
    "live_scale_runs": "Number of live calibration runs.",
    "live_test_signal_pp_uv": "Internal test signal peak-to-peak amplitude used for live calibration.",
    "live_scale_type": "Live-stream scale provenance label.",
    "sample_index": "Zero-based sample index.",
    "ch1_raw24": "CH1 signed 24-bit raw ADS1292 ADC code.",
    "ch2_raw24": "CH2 signed 24-bit raw ADS1292 ADC code.",
    "ch1_uv": "CH1 raw ADC value converted to microvolts using raw_lsb_uv_per_count.",
    "ch2_uv": "CH2 raw ADC value converted to microvolts using raw_lsb_uv_per_count.",
    "vref_mv": "Reference voltage used for raw ADC conversion.",
    "pga_gain": "PGA gain used for raw ADC conversion.",
    "adc_bits": "ADC resolution used for raw ADC conversion.",
    "raw_lsb_uv_per_count": "Raw ADC least-significant-bit scale.",
    "acquisition_mode": "CSV acquisition mode label.",
}


@dataclass(frozen=True)
class AcquisitionProvenance:
    schema: str = ACQUISITION_SCHEMA
    csv_name: str = ""
    csv_schema: str = LIVE_CSV_SCHEMA
    acquisition_mode: str = "live_stream"
    port: str = ""
    sample_rate_hz: float = 500.0
    started_at: str = ""
    timestamp_reference: str = TIMESTAMP_REFERENCE
    channel_map: dict[str, str] = field(default_factory=dict)
    csv_columns: tuple[dict[str, str], ...] = field(default_factory=tuple)
    raw_adc: dict[str, Any] = field(default_factory=dict)
    live_calibration: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> "AcquisitionProvenance":
        mode = _normalized_mode(self.acquisition_mode)
        csv_schema = RAW_CSV_SCHEMA if mode == "raw_adc_24bit" else LIVE_CSV_SCHEMA
        live_calibration = dict(self.live_calibration)
        return AcquisitionProvenance(
            schema=self.schema.strip() or ACQUISITION_SCHEMA,
            csv_name=self.csv_name.strip(),
            csv_schema=csv_schema,
            acquisition_mode=mode,
            port=self.port.strip(),
            sample_rate_hz=float(self.sample_rate_hz) if self.sample_rate_hz > 0 else 500.0,
            started_at=self.started_at.strip(),
            timestamp_reference=_clean_timestamp_reference(self.timestamp_reference),
            channel_map=_clean_string_map(self.channel_map) or default_channel_map(),
            csv_columns=_clean_csv_columns(self.csv_columns)
            or default_csv_columns(mode, include_live_calibration=bool(live_calibration)),
            raw_adc=dict(self.raw_adc),
            live_calibration=live_calibration,
        )


def default_channel_map() -> dict[str, str]:
    return {
        "ch1_counts": "CH1 respiration/raw impedance",
        "ch2_counts": "CH2 ECG Lead I (LA-RA)",
        "status_byte": "ADS1x9x status byte",
        "lead_off_bits": "lead-off/contact status low nibble",
    }


def default_csv_columns(
    acquisition_mode: str,
    *,
    include_live_calibration: bool = False,
) -> tuple[dict[str, str], ...]:
    mode = _normalized_mode(acquisition_mode)
    names = tuple(RAW_HEADER) if mode == "raw_adc_24bit" else tuple(CANONICAL_HEADER)
    if mode != "raw_adc_24bit" and include_live_calibration:
        names = names + tuple(LIVE_CALIBRATION_COLUMNS)
    return tuple(_csv_column_entry(name) for name in names)


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
        timestamp_reference=TIMESTAMP_REFERENCE,
        channel_map=default_channel_map(),
        csv_columns=default_csv_columns(
            normalized_mode,
            include_live_calibration=normalized_live is not None,
        ),
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


def format_acquisition_summary(provenance: AcquisitionProvenance | None) -> str:
    if provenance is None:
        return "Acquisition: no provenance sidecar"
    normalized = provenance.normalized()
    live = normalized.live_calibration
    raw = normalized.raw_adc
    live_text = "Live scale not calibrated"
    if live:
        live_text = (
            f"Live scale {float(live['mean_uv_per_count']):.6g} uV/count"
            f" ({int(live['runs'])} runs, CV {float(live['cv_percent']):.3g}%)"
        )
    raw_text = "Raw LSB unavailable"
    if raw.get("raw_lsb_uv_per_count") is not None:
        raw_text = f"Raw LSB {float(raw['raw_lsb_uv_per_count']):.6f} uV/count"
    return (
        f"{normalized.acquisition_mode} | {normalized.sample_rate_hz:g} Hz | "
        f"{normalized.port or 'port unknown'}\n"
        f"timestamps relative to recording start ({normalized.timestamp_reference})\n"
        f"{live_text}\n"
        f"{raw_text}"
    )


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


def _clean_csv_columns(values) -> tuple[dict[str, str], ...]:
    cleaned: list[dict[str, str]] = []
    for item in values or ():
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        cleaned.append(
            {
                "name": name,
                "unit": str(item.get("unit", "")).strip(),
                "description": str(item.get("description", "")).strip(),
            }
        )
    return tuple(cleaned)


def _clean_timestamp_reference(value: str) -> str:
    text = str(value).strip()
    return text if text else TIMESTAMP_REFERENCE


def _csv_column_entry(name: str) -> dict[str, str]:
    return {
        "name": name,
        "unit": _CSV_COLUMN_UNITS.get(name, ""),
        "description": _CSV_COLUMN_DESCRIPTIONS.get(name, name),
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
