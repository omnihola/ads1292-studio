// core/src/dsp/EcgReview.cpp
// ECG analysis: detect_r_peaks — bandpass → center → prominence/polarity → find_peaks.
// Faithful port of signal_processing.py. Pure C++17, no Qt. All double.

#include "ads1292/dsp/EcgReview.h"
#include "ads1292/dsp/Filtfilt.h"
#include "ads1292/dsp/Peaks.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <vector>

namespace ads1292::dsp {

namespace {

// ─── median (numpy semantics) ─────────────────────────────────────────────────
// Sorts a copy; for even-length returns average of the two middle elements.
double median(std::vector<double> v) {
    if (v.empty()) return 0.0;
    const std::size_t n = v.size();
    std::sort(v.begin(), v.end());
    if (n % 2 == 1) {
        return v[n / 2];
    } else {
        return (v[n / 2 - 1] + v[n / 2]) * 0.5;
    }
}

// ─── std_pop (population std, ddof=0) ────────────────────────────────────────
// Matches numpy np.std(x) default (ddof=0): sqrt(mean((x - mean(x))^2)).
double std_pop(const std::vector<double>& v) {
    if (v.empty()) return 0.0;
    const std::size_t n = v.size();
    const double mean_val =
        std::accumulate(v.begin(), v.end(), 0.0) / static_cast<double>(n);
    double sum_sq = 0.0;
    for (double x : v) {
        const double d = x - mean_val;
        sum_sq += d * d;
    }
    return std::sqrt(sum_sq / static_cast<double>(n));
}

} // anonymous namespace

// ─── detect_r_peaks ──────────────────────────────────────────────────────────
std::vector<int> detect_r_peaks(const std::vector<double>& values,
                                 double sample_rate_hz) {
    // Early returns
    if (!std::isfinite(sample_rate_hz) || sample_rate_hz <= 0.0) {
        return {};
    }
    const auto sr_int = static_cast<std::size_t>(static_cast<int>(sample_rate_hz));
    if (values.size() < sr_int) {
        return {};
    }

    // Step 1: bandpass filter (defaults 0.7–35 Hz, matches signal_processing.py)
    const std::vector<double> filtered = bandpass(values, sample_rate_hz);

    // Step 2: center around median
    const double med = median(filtered);
    std::vector<double> centered(filtered.size());
    for (std::size_t i = 0; i < filtered.size(); ++i) {
        centered[i] = filtered[i] - med;
    }

    // Step 3: population std of centered
    const double scale = std_pop(centered);

    // Step 4: prominence threshold
    const double prominence = std::max(20.0, scale * 0.45);

    // Step 5: polarity — pick the direction with the larger excursion
    const double pos = *std::max_element(centered.begin(), centered.end());
    const double neg = std::abs(*std::min_element(centered.begin(), centered.end()));

    std::vector<double> peak_signal;
    if (pos >= neg) {
        peak_signal = centered;
    } else {
        peak_signal.resize(centered.size());
        for (std::size_t i = 0; i < centered.size(); ++i) {
            peak_signal[i] = -centered[i];
        }
    }

    // Step 6: find_peaks with distance=(int)(0.35*sr)
    const int distance = static_cast<int>(0.35 * sample_rate_hz);
    return find_peaks(peak_signal, distance, prominence);
}

// ─── heart_rate_summary ──────────────────────────────────────────────────────
HeartRateSummary heart_rate_summary(const std::vector<int>& peaks,
                                     double sample_rate_hz) {
    // Early returns: invalid sample rate or too few peaks
    if (!std::isfinite(sample_rate_hz) || sample_rate_hz <= 0.0) {
        return {0.0, 0.0, 0.0, 0};
    }
    if (peaks.size() < 2) {
        return {0.0, 0.0, 0.0, 0};
    }

    // Compute R-R intervals and corresponding BPM
    std::vector<double> bpm;
    bpm.reserve(peaks.size() - 1);
    for (std::size_t i = 0; i + 1 < peaks.size(); ++i) {
        const double rr = static_cast<double>(peaks[i + 1] - peaks[i]) / sample_rate_hz;
        if (rr > 0.0) {  // Sanity check: R-R should be positive
            bpm.push_back(60.0 / rr);
        }
    }

    // Filter BPM values to valid range [40, 180]
    std::vector<double> valid;
    valid.reserve(bpm.size());
    for (double b : bpm) {
        if (b >= 40.0 && b <= 180.0) {
            valid.push_back(b);
        }
    }

    // Return zeros if no valid BPM values
    if (valid.empty()) {
        return {0.0, 0.0, 0.0, 0};
    }

    // Compute median, min, max of valid BPM
    double median_val = median(valid);
    double min_val = *std::min_element(valid.begin(), valid.end());
    double max_val = *std::max_element(valid.begin(), valid.end());

    return {median_val, min_val, max_val, static_cast<int>(valid.size())};
}

} // namespace ads1292::dsp
