// core/src/dsp/QualityGate.cpp
// Quality-gate thresholds and evaluation.
// Pure C++17, no Qt, no OS. All values double.

#include "ads1292/dsp/QualityGate.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <string>

namespace ads1292::dsp {

// ---------------------------------------------------------------------------
// File-local formatting helpers — replicate Python's :.2f / :.1f exactly.
// ---------------------------------------------------------------------------
namespace {

std::string f2(double v) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2) << v;
    return oss.str();
}

std::string f1(double v) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(1) << v;
    return oss.str();
}

} // namespace

// ---------------------------------------------------------------------------
// normalized
// ---------------------------------------------------------------------------
QualityGate normalized(const QualityGate& g) {
    QualityGate n = g;
    n.min_duration_seconds   = std::max(0.0, g.min_duration_seconds);
    n.min_contact_ok_percent = std::max(0.0, std::min(100.0, g.min_contact_ok_percent));
    n.min_r_peaks            = std::max(0, g.min_r_peaks);
    n.min_hr_bpm             = std::max(0.0, g.min_hr_bpm);
    n.max_hr_bpm             = std::max(0.0, g.max_hr_bpm);
    // require_qrs_clear: keep as-is

    if (g.max_baseline_drift_counts.has_value())
        n.max_baseline_drift_counts = std::max(0.0, *g.max_baseline_drift_counts);
    else
        n.max_baseline_drift_counts = std::nullopt;

    if (g.max_noise_rms_counts.has_value())
        n.max_noise_rms_counts = std::max(0.0, *g.max_noise_rms_counts);
    else
        n.max_noise_rms_counts = std::nullopt;

    if (g.max_peak_to_peak_counts.has_value())
        n.max_peak_to_peak_counts = std::max(0.0, *g.max_peak_to_peak_counts);
    else
        n.max_peak_to_peak_counts = std::nullopt;

    return n;
}

// ---------------------------------------------------------------------------
// evaluate_quality_gate
// ---------------------------------------------------------------------------
QualityGateResult evaluate_quality_gate(
    const QualityMetrics& m,
    const QualityGate&    gate)
{
    const QualityGate g = normalized(gate);
    std::vector<std::string> failures;

    // --- Finiteness checks (in the prescribed order) ---
    struct FiniteCheck { const char* name; double value; };
    const FiniteCheck finite_checks[] = {
        { "duration",       m.duration_seconds      },
        { "contact %",      m.contact_ok_percent     },
        { "median HR",      m.hr_median_bpm          },
        { "baseline drift", m.baseline_drift_counts  },
        { "noise RMS",      m.noise_rms_counts       },
        { "peak-to-peak",   m.peak_to_peak_counts    },
    };
    for (const auto& fc : finite_checks) {
        if (!std::isfinite(fc.value)) {
            // Format the non-finite value the same way Python does:
            // float('nan') → "nan", float('inf') → "inf"
            std::string val_str;
            if (std::isnan(fc.value))
                val_str = "nan";
            else if (fc.value > 0)
                val_str = "inf";
            else
                val_str = "-inf";
            failures.push_back(
                std::string(fc.name) + " is not finite (" + val_str + ")");
        }
    }

    // --- Threshold checks (EXACT failure strings, matching quality_gate.py) ---

    if (m.duration_seconds < g.min_duration_seconds)
        failures.push_back(
            "duration " + f2(m.duration_seconds) + "s < " + f2(g.min_duration_seconds) + "s");

    if (m.contact_ok_percent < g.min_contact_ok_percent)
        failures.push_back(
            "contact " + f2(m.contact_ok_percent) + "% < " + f2(g.min_contact_ok_percent) + "%");

    if (g.require_qrs_clear && !m.qrs_clear)
        failures.push_back("QRS not clear");

    if (m.r_peaks < g.min_r_peaks)
        failures.push_back(
            "R peaks " + std::to_string(m.r_peaks) + " < " + std::to_string(g.min_r_peaks));

    if (m.hr_median_bpm > 0.0 && m.hr_median_bpm < g.min_hr_bpm)
        failures.push_back(
            "median HR " + f1(m.hr_median_bpm) + " bpm < " + f1(g.min_hr_bpm) + " bpm");

    if (m.hr_median_bpm > g.max_hr_bpm)
        failures.push_back(
            "median HR " + f1(m.hr_median_bpm) + " bpm > " + f1(g.max_hr_bpm) + " bpm");

    if (g.max_baseline_drift_counts.has_value() &&
        m.baseline_drift_counts > *g.max_baseline_drift_counts)
        failures.push_back(
            "baseline drift " + f1(m.baseline_drift_counts) +
            " counts > " + f1(*g.max_baseline_drift_counts) + " counts");

    if (g.max_noise_rms_counts.has_value() &&
        m.noise_rms_counts > *g.max_noise_rms_counts)
        failures.push_back(
            "noise RMS " + f1(m.noise_rms_counts) +
            " counts > " + f1(*g.max_noise_rms_counts) + " counts");

    if (g.max_peak_to_peak_counts.has_value() &&
        m.peak_to_peak_counts > *g.max_peak_to_peak_counts)
        failures.push_back(
            "peak-to-peak " + f1(m.peak_to_peak_counts) +
            " counts > " + f1(*g.max_peak_to_peak_counts) + " counts");

    return { failures.empty(), failures };
}

} // namespace ads1292::dsp
