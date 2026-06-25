// core/src/dsp/Quality.cpp
// ECG signal quality: noise_rms, baseline_drift, estimate_realtime_snr.
// Pure C++17, no Qt. All double.

#include "ads1292/dsp/Quality.h"
#include "ads1292/dsp/Stats.h"

#include <algorithm>
#include <cmath>
#include <vector>

namespace ads1292::dsp {

namespace {

// Numpy-faithful median: sort ascending copy; for even length return average
// of the two middle elements.
double median_local(std::vector<double> v) {
    if (v.empty()) return 0.0;
    const std::size_t n = v.size();
    std::sort(v.begin(), v.end());
    if (n % 2 == 1) {
        return v[n / 2];
    }
    return (v[n / 2 - 1] + v[n / 2]) * 0.5;
}

} // anonymous namespace

// ─── noise_rms ───────────────────────────────────────────────────────────────
double noise_rms(const std::vector<double>& values) {
    const std::size_t n = values.size();
    if (n < 3) return 0.0;

    // diff[i] = v[i+1] - v[i], length n-1
    std::vector<double> diff(n - 1);
    for (std::size_t i = 0; i + 1 < n; ++i) {
        diff[i] = values[i + 1] - values[i];
    }

    // Median of diff
    const double med_diff = median_local(diff);

    // Absolute deviations from median
    std::vector<double> abs_dev(diff.size());
    for (std::size_t i = 0; i < diff.size(); ++i) {
        abs_dev[i] = std::abs(diff[i] - med_diff);
    }

    // MAD = median of absolute deviations
    const double mad = median_local(abs_dev);

    return 1.4826 * mad / std::sqrt(2.0);
}

// ─── baseline_drift ──────────────────────────────────────────────────────────
double baseline_drift(const std::vector<double>& values, double sample_rate_hz) {
    const std::size_t n = values.size();
    if (n < 2) return 0.0;

    // window = max(1, min((int)sr, (int)n/2))
    const int window = std::max(1,
        std::min(static_cast<int>(sample_rate_hz),
                 static_cast<int>(n / 2)));

    // start = median of v[0 .. window)
    const std::vector<double> start_win(values.begin(),
                                        values.begin() + window);
    const double start_med = median_local(start_win);

    // end = median of v[n-window .. n)
    const std::vector<double> end_win(values.end() - window, values.end());
    const double end_med = median_local(end_win);

    return std::abs(end_med - start_med);
}

// ─── estimate_realtime_snr ───────────────────────────────────────────────────
SignalNoiseEstimate estimate_realtime_snr(const std::vector<double>& values,
                                          double sample_rate_hz) {
    // Filter to finite values only
    std::vector<double> finite;
    finite.reserve(values.size());
    for (double v : values) {
        if (std::isfinite(v)) {
            finite.push_back(v);
        }
    }

    const int total_size = static_cast<int>(values.size());
    const int finite_size = static_cast<int>(finite.size());

    // Not enough data
    if (finite_size < 3) {
        return {0.0, 0.0, 0.0, 0.0, finite_size, 0.0, false};
    }

    // Centered signal: finite - median(finite)
    const double med = median_local(finite);
    std::vector<double> centered(finite_size);
    for (int i = 0; i < finite_size; ++i) {
        centered[i] = finite[i] - med;
    }

    // signal_rms = sqrt(mean(centered^2))
    double sum_sq = 0.0;
    for (double c : centered) {
        sum_sq += c * c;
    }
    const double signal_rms = std::sqrt(sum_sq / static_cast<double>(finite_size));

    // Noise RMS via MAD of first differences
    const double nrms = noise_rms(finite);

    // Peak-to-peak: percentile(95) - percentile(5)
    const double p2p = percentile(finite, 95.0) - percentile(finite, 5.0);

    // Duration
    const double duration = (sample_rate_hz > 0.0)
        ? static_cast<double>(finite_size - 1) / sample_rate_hz
        : 0.0;

    // Guard: flat signal
    if (signal_rms <= 1e-12) {
        return {0.0, signal_rms, nrms, p2p, finite_size, duration, false};
    }

    // Guard: no noise → cap at 80 dB
    if (nrms <= 1e-12) {
        return {80.0, signal_rms, nrms, p2p, finite_size, duration, true};
    }

    // SNR in dB
    const double snr_db = 20.0 * std::log10(signal_rms / nrms);

    return {snr_db, signal_rms, nrms, p2p, finite_size, duration, true};
}

} // namespace ads1292::dsp
