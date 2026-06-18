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
