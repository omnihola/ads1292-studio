// core/src/dsp/LiveCalibration.cpp
// LiveStreamCalibration model + statistics: normalized(), peak-to-peak, summarize.
// Pure C++17, no Qt. All computations in double.

#include "ads1292/dsp/LiveCalibration.h"
#include "ads1292/dsp/Stats.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

namespace {

/// Strip leading/trailing ASCII whitespace (space, tab, CR, LF).
static std::string trim(const std::string& s) {
    const std::string ws = " \t\r\n";
    auto b = s.find_first_not_of(ws);
    if (b == std::string::npos) return "";
    auto e = s.find_last_not_of(ws);
    return s.substr(b, e - b + 1);
}

} // namespace

// ---------------------------------------------------------------------------
// ads1292::LiveStreamCalibration
// ---------------------------------------------------------------------------

namespace ads1292 {

LiveStreamCalibration LiveStreamCalibration::normalized() const {
    double mean  = mean_uv_per_count;                      // as-is (may be negative)
    double std_  = std::max(0.0, std_uv_per_count);
    int    runs_ = std::max(0, runs);
    double cv    = (cv_percent >= 0.0) ? cv_percent : 0.0;
    double sig   = (test_signal_pp_uv > 0.0) ? test_signal_pp_uv : 2016.6666666667;

    std::string st = trim(scale_type);
    if (st.empty()) st = "live_processed";

    return LiveStreamCalibration{mean, std_, cv, runs_, sig, st};
}

} // namespace ads1292

// ---------------------------------------------------------------------------
// ads1292::dsp free functions
// ---------------------------------------------------------------------------

namespace ads1292::dsp {

double live_stream_peak_to_peak_counts(const std::vector<double>& values) {
    if (values.size() < 4) {
        throw std::invalid_argument(
            "live stream calibration requires at least four samples");
    }

    // Keep only finite values.
    std::vector<double> finite;
    finite.reserve(values.size());
    for (double v : values) {
        if (std::isfinite(v)) finite.push_back(v);
    }
    if (finite.size() < 4) {
        throw std::invalid_argument(
            "live stream calibration requires finite samples");
    }

    const double low  = percentile(finite, 1.0);
    const double high = percentile(finite, 99.0);
    const double pp   = high - low;

    if (pp <= 0.0) {
        throw std::invalid_argument(
            "live stream calibration could not resolve low/high test levels");
    }
    return pp;
}

ads1292::LiveStreamCalibration summarize_live_stream_calibration(
    const std::vector<double>& peak_to_peak_counts,
    double test_signal_pp_uv)
{
    // Filter to positive counts only.
    std::vector<double> counts;
    counts.reserve(peak_to_peak_counts.size());
    for (double c : peak_to_peak_counts) {
        if (c > 0.0) counts.push_back(c);
    }
    if (counts.empty()) {
        throw std::invalid_argument(
            "live stream calibration requires at least one positive peak-to-peak count");
    }

    // scales[i] = test_signal_pp_uv / counts[i]
    const std::size_t n = counts.size();
    std::vector<double> scales(n);
    for (std::size_t i = 0; i < n; ++i) {
        scales[i] = test_signal_pp_uv / counts[i];
    }

    // Mean.
    const double mean_val = std::accumulate(scales.begin(), scales.end(), 0.0)
                            / static_cast<double>(n);

    // Sample standard deviation (ddof=1).
    double std_val = 0.0;
    if (n > 1) {
        double sum_sq = 0.0;
        for (double s : scales) {
            const double d = s - mean_val;
            sum_sq += d * d;
        }
        std_val = std::sqrt(sum_sq / static_cast<double>(n - 1));
    }

    // Coefficient of variation (%).
    const double cv = (mean_val != 0.0) ? (std_val / mean_val) * 100.0 : 0.0;

    return ads1292::LiveStreamCalibration{
        mean_val, std_val, cv, static_cast<int>(n), test_signal_pp_uv
    }.normalized();
}

} // namespace ads1292::dsp
