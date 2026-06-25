#pragma once
// core/include/ads1292/dsp/QualityGate.h
// Quality-gate thresholds and evaluation.
// Pure C++17, no Qt, no OS. All values double.

#include "ads1292/dsp/QualityMetrics.h"

#include <optional>
#include <string>
#include <vector>

namespace ads1292::dsp {

/// Configurable thresholds for the quality gate.
struct QualityGate {
    double min_duration_seconds    = 8.0;
    double min_contact_ok_percent  = 95.0;
    int    min_r_peaks             = 5;
    double min_hr_bpm              = 35.0;
    double max_hr_bpm              = 180.0;
    bool   require_qrs_clear       = true;

    // Optional hard caps; unset means unchecked.
    std::optional<double> max_baseline_drift_counts;
    std::optional<double> max_noise_rms_counts;
    std::optional<double> max_peak_to_peak_counts;
};

/// Returns a copy of g with out-of-range fields clamped to valid ranges.
/// min_duration_seconds  = max(0, ·)
/// min_contact_ok_percent = clamp(·, 0, 100)
/// min_r_peaks           = max(0, ·)
/// min_hr_bpm            = max(0, ·)
/// max_hr_bpm            = max(0, ·)
/// each optional cap     = max(0, ·) if set, else unset
QualityGate normalized(const QualityGate& g);

/// Pass/fail result from evaluate_quality_gate.
struct QualityGateResult {
    bool                     passed;
    std::vector<std::string> failures;

    std::string label() const { return passed ? "Pass" : "Fail"; }
};

/// Evaluates the gate against the given metrics.
/// Failure strings match quality_gate.py byte-for-byte.
QualityGateResult evaluate_quality_gate(
    const QualityMetrics& metrics,
    const QualityGate&    gate = QualityGate{});

} // namespace ads1292::dsp
