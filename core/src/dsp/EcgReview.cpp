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
                                 double sample_rate_hz,
                                 bool prefiltered) {
    // Early returns
    if (!std::isfinite(sample_rate_hz) || sample_rate_hz <= 0.0) {
        return {};
    }
    const auto sr_int = static_cast<std::size_t>(static_cast<int>(sample_rate_hz));
    if (values.size() < sr_int) {
        return {};
    }

    // Step 1: bandpass filter (defaults 0.7–35 Hz, matches signal_processing.py)
    // If prefiltered=true, skip bandpass — signal already filtered by display chain.
    const std::vector<double> filtered = prefiltered ? values : bandpass(values, sample_rate_hz);

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

// ─── pqrst_review ────────────────────────────────────────────────────────────
PqrstReview pqrst_review(const std::vector<double>& values,
                          const std::vector<int>& peaks,
                          double sample_rate_hz) {
    const double sr = sample_rate_hz;

    // Step 1: bandpass with pqrst-specific cutoffs (0.15–40 Hz)
    const std::vector<double> filtered = bandpass(values, sr, 0.15, 40.0);
    const int n = static_cast<int>(filtered.size());

    // Step 2: window parameters
    const int pre  = static_cast<int>(0.25 * sr);
    const int post = static_cast<int>(0.55 * sr);
    const int win  = pre + post;
    const int bl_end = std::max(1, static_cast<int>(0.12 * sr)); // baseline window end

    // Step 3: collect baseline-corrected beats
    std::vector<std::vector<double>> beats;
    for (int pk : peaks) {
        if (pk - pre < 0 || pk + post > n) continue;

        // Extract beat window
        std::vector<double> beat(filtered.begin() + (pk - pre),
                                 filtered.begin() + (pk + post));

        // Baseline = median of first bl_end samples
        std::vector<double> bl_window(beat.begin(), beat.begin() + bl_end);
        const double base = median(bl_window);

        // Subtract baseline from every sample
        for (double& s : beat) s -= base;

        beats.push_back(std::move(beat));
    }

    // No usable beats → return empty result
    if (beats.empty()) {
        return {false, false, false, 0, {}, {}};
    }

    const int beats_used = static_cast<int>(beats.size());

    // Step 4: per-index average across collected beats
    std::vector<double> avg(win, 0.0);
    for (const auto& beat : beats) {
        for (int j = 0; j < win; ++j) {
            avg[j] += beat[j];
        }
    }
    const double n_beats = static_cast<double>(beats_used);
    for (double& a : avg) a /= n_beats;

    // Step 5: R-peak amplitude at index `pre`
    const double r_amp = std::abs(avg[pre]);

    // Step 6: half = max(1, pre/2)  (integer div)
    const int half = std::max(1, pre / 2);

    // Step 7: noise = MAD of avg[0..half) + 1e-9
    //   noise = median( |avg[0..half) - median(avg[0..half))| ) + 1e-9
    std::vector<double> first_half(avg.begin(), avg.begin() + half);
    const double m_first = median(first_half);
    std::vector<double> abs_dev(half);
    for (int i = 0; i < half; ++i) {
        abs_dev[i] = std::abs(avg[i] - m_first);
    }
    const double noise = median(abs_dev) + 1e-9;

    // Step 8: PQRST window indices
    const int p_start = pre - static_cast<int>(0.22 * sr);
    const int p_end   = pre - static_cast<int>(0.08 * sr);
    const int t_start = pre + static_cast<int>(0.12 * sr);
    const int t_end   = pre + static_cast<int>(0.38 * sr);

    // Step 9: ptp (max - min) over each wave window
    auto ptp = [&](int start, int end) -> double {
        if (end <= start) return 0.0;
        double lo = avg[start], hi = avg[start];
        for (int i = start + 1; i < end; ++i) {
            if (avg[i] < lo) lo = avg[i];
            if (avg[i] > hi) hi = avg[i];
        }
        return hi - lo;
    };

    const double p_range = (p_end > p_start) ? ptp(p_start, p_end) : 0.0;
    const double t_range = (t_end > t_start) ? ptp(t_start, t_end) : 0.0;

    // Step 10: boolean flags
    const bool qrs_clear    = r_amp   > std::max(40.0, noise * 8.0);
    const bool p_tentative  = p_range > std::max(15.0, noise * 3.0);
    const bool t_tentative  = t_range > std::max(25.0, noise * 4.0);

    // Step 11: time_ms array
    std::vector<double> time_ms(win);
    for (int i = 0; i < win; ++i) {
        time_ms[i] = (static_cast<double>(i - pre) / sr) * 1000.0;
    }

    return {qrs_clear, p_tentative, t_tentative, beats_used, avg, time_ms};
}

} // namespace ads1292::dsp
