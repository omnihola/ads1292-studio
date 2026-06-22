from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path

from ads1292_studio.quality import QualityMetrics


@dataclass(frozen=True)
class QualityGate:
    min_duration_seconds: float = 8.0
    min_contact_ok_percent: float = 95.0
    min_r_peaks: int = 5
    min_hr_bpm: float = 35.0
    max_hr_bpm: float = 180.0
    require_qrs_clear: bool = True
    max_baseline_drift_counts: float | None = None
    max_noise_rms_counts: float | None = None
    max_peak_to_peak_counts: float | None = None

    def normalized(self) -> "QualityGate":
        return QualityGate(
            min_duration_seconds=max(0.0, float(self.min_duration_seconds)),
            min_contact_ok_percent=max(0.0, min(100.0, float(self.min_contact_ok_percent))),
            min_r_peaks=max(0, int(self.min_r_peaks)),
            min_hr_bpm=max(0.0, float(self.min_hr_bpm)),
            max_hr_bpm=max(0.0, float(self.max_hr_bpm)),
            require_qrs_clear=bool(self.require_qrs_clear),
            max_baseline_drift_counts=_optional_nonnegative(self.max_baseline_drift_counts),
            max_noise_rms_counts=_optional_nonnegative(self.max_noise_rms_counts),
            max_peak_to_peak_counts=_optional_nonnegative(self.max_peak_to_peak_counts),
        )


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    failures: tuple[str, ...]

    @property
    def label(self) -> str:
        return "Pass" if self.passed else "Fail"


def evaluate_quality_gate(metrics: QualityMetrics, gate: QualityGate | None = None) -> QualityGateResult:
    gate = (gate or QualityGate()).normalized()
    failures: list[str] = []
    # A non-finite metric (NaN/inf) makes every threshold comparison False and
    # would silently pass corrupt data — fail explicitly instead.
    for name, value in (
        ("duration", metrics.duration_seconds),
        ("contact %", metrics.contact_ok_percent),
        ("median HR", metrics.hr_median_bpm),
        ("baseline drift", metrics.baseline_drift_counts),
        ("noise RMS", metrics.noise_rms_counts),
        ("peak-to-peak", metrics.peak_to_peak_counts),
    ):
        if not math.isfinite(value):
            failures.append(f"{name} is not finite ({value})")
    if metrics.duration_seconds < gate.min_duration_seconds:
        failures.append(f"duration {metrics.duration_seconds:.2f}s < {gate.min_duration_seconds:.2f}s")
    if metrics.contact_ok_percent < gate.min_contact_ok_percent:
        failures.append(f"contact {metrics.contact_ok_percent:.2f}% < {gate.min_contact_ok_percent:.2f}%")
    if gate.require_qrs_clear and not metrics.qrs_clear:
        failures.append("QRS not clear")
    if metrics.r_peaks < gate.min_r_peaks:
        failures.append(f"R peaks {metrics.r_peaks} < {gate.min_r_peaks}")
    if metrics.hr_median_bpm > 0 and metrics.hr_median_bpm < gate.min_hr_bpm:
        failures.append(f"median HR {metrics.hr_median_bpm:.1f} bpm < {gate.min_hr_bpm:.1f} bpm")
    if metrics.hr_median_bpm > gate.max_hr_bpm:
        failures.append(f"median HR {metrics.hr_median_bpm:.1f} bpm > {gate.max_hr_bpm:.1f} bpm")
    if gate.max_baseline_drift_counts is not None and metrics.baseline_drift_counts > gate.max_baseline_drift_counts:
        failures.append(
            f"baseline drift {metrics.baseline_drift_counts:.1f} counts > {gate.max_baseline_drift_counts:.1f} counts"
        )
    if gate.max_noise_rms_counts is not None and metrics.noise_rms_counts > gate.max_noise_rms_counts:
        failures.append(f"noise RMS {metrics.noise_rms_counts:.1f} counts > {gate.max_noise_rms_counts:.1f} counts")
    if gate.max_peak_to_peak_counts is not None and metrics.peak_to_peak_counts > gate.max_peak_to_peak_counts:
        failures.append(
            f"peak-to-peak {metrics.peak_to_peak_counts:.1f} counts > {gate.max_peak_to_peak_counts:.1f} counts"
        )
    return QualityGateResult(passed=not failures, failures=tuple(failures))


def quality_gate_template() -> QualityGate:
    return QualityGate()


def read_quality_gate_json(path: Path | str) -> QualityGate:
    data = json.loads(Path(path).read_text())
    return QualityGate(
        min_duration_seconds=float(data.get("min_duration_seconds", 8.0)),
        min_contact_ok_percent=float(data.get("min_contact_ok_percent", 95.0)),
        min_r_peaks=int(data.get("min_r_peaks", 5)),
        min_hr_bpm=float(data.get("min_hr_bpm", 35.0)),
        max_hr_bpm=float(data.get("max_hr_bpm", 180.0)),
        require_qrs_clear=bool(data.get("require_qrs_clear", True)),
        max_baseline_drift_counts=_json_optional_float(data.get("max_baseline_drift_counts")),
        max_noise_rms_counts=_json_optional_float(data.get("max_noise_rms_counts")),
        max_peak_to_peak_counts=_json_optional_float(data.get("max_peak_to_peak_counts")),
    ).normalized()


def write_quality_gate_json(path: Path | str, gate: QualityGate) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(gate.normalized()), indent=2) + "\n")


def _json_optional_float(value) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_nonnegative(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, float(value))
