from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Calibration:
    vref_mv: float = 2420.0
    pga_gain: float = 6.0
    adc_bits: int = 24
    label: str = "ADS1292 default"

    def normalized(self) -> "Calibration":
        return Calibration(
            vref_mv=self.vref_mv if self.vref_mv > 0 else 2420.0,
            pga_gain=self.pga_gain if self.pga_gain > 0 else 6.0,
            adc_bits=self.adc_bits if self.adc_bits >= 2 else 24,
            label=self.label.strip() or "ADS1292 default",
        )

    @property
    def microvolts_per_count(self) -> float:
        normalized = self.normalized()
        full_scale_counts = float((2 ** (normalized.adc_bits - 1)) - 1)
        return normalized.vref_mv * 1000.0 / (normalized.pga_gain * full_scale_counts)


@dataclass(frozen=True)
class LiveStreamCalibration:
    mean_uv_per_count: float
    std_uv_per_count: float
    cv_percent: float
    runs: int
    test_signal_pp_uv: float
    scale_type: str = "live_processed"

    def normalized(self) -> "LiveStreamCalibration":
        mean = float(self.mean_uv_per_count)
        std = max(0.0, float(self.std_uv_per_count))
        runs = max(0, int(self.runs))
        cv = float(self.cv_percent) if self.cv_percent >= 0 else 0.0
        test_signal = float(self.test_signal_pp_uv) if self.test_signal_pp_uv > 0 else 2016.6666666667
        return LiveStreamCalibration(
            mean_uv_per_count=mean,
            std_uv_per_count=std,
            cv_percent=cv,
            runs=runs,
            test_signal_pp_uv=test_signal,
            scale_type=self.scale_type.strip() or "live_processed",
        )


def summarize_live_stream_calibration(
    peak_to_peak_counts: tuple[float, ...] | list[float],
    *,
    test_signal_pp_uv: float,
) -> LiveStreamCalibration:
    counts = np.asarray([value for value in peak_to_peak_counts if float(value) > 0], dtype=float)
    if counts.size == 0:
        raise ValueError("live stream calibration requires at least one positive peak-to-peak count")
    scales = float(test_signal_pp_uv) / counts
    mean = float(np.mean(scales))
    std = float(np.std(scales, ddof=1)) if scales.size > 1 else 0.0
    cv = float((std / mean) * 100.0) if mean else 0.0
    return LiveStreamCalibration(
        mean_uv_per_count=mean,
        std_uv_per_count=std,
        cv_percent=cv,
        runs=int(scales.size),
        test_signal_pp_uv=float(test_signal_pp_uv),
    ).normalized()


def live_stream_peak_to_peak_counts(values: tuple[float, ...] | list[float] | np.ndarray) -> float:
    data = np.asarray(values, dtype=float)
    if data.size < 4:
        raise ValueError("live stream calibration requires at least four samples")
    finite = data[np.isfinite(data)]
    if finite.size < 4:
        raise ValueError("live stream calibration requires finite samples")
    low, high = np.percentile(finite, [1.0, 99.0])
    peak_to_peak = float(high - low)
    if peak_to_peak <= 0:
        raise ValueError("live stream calibration could not resolve low/high test levels")
    return peak_to_peak


def counts_to_microvolts(values: np.ndarray, calibration: Calibration | None = None) -> np.ndarray:
    scale = (calibration or Calibration()).microvolts_per_count
    return np.asarray(values, dtype=float) * scale


def read_calibration_json(path: Path | str) -> Calibration:
    data = json.loads(Path(path).read_text())
    allowed = {field.name for field in Calibration.__dataclass_fields__.values()}
    filtered = {key: value for key, value in data.items() if key in allowed}
    return Calibration(**filtered).normalized()


def write_calibration_json(path: Path | str, calibration: Calibration) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(calibration.normalized()), indent=2) + "\n")


def calibration_template() -> Calibration:
    return Calibration()
