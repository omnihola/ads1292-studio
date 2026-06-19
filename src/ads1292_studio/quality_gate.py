from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class QualityGateResult:
    passed: bool
    failures: tuple[str, ...]

    @property
    def label(self) -> str:
        return "Pass" if self.passed else "Fail"


def evaluate_quality_gate(metrics: QualityMetrics, gate: QualityGate | None = None) -> QualityGateResult:
    gate = gate or QualityGate()
    failures: list[str] = []
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
