// core/src/dsp/ChannelSelect.cpp
// ECG channel selection: qrs_like_score, choose_ecg_channel, review_channels.
// Pure C++17, no Qt, no OS.  All computations in double.

#include "ads1292/dsp/ChannelSelect.h"
#include "ads1292/dsp/EcgReview.h"
#include "ads1292/dsp/Filtfilt.h"
#include "ads1292/dsp/Stats.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <string>
#include <vector>

namespace ads1292::dsp {

namespace {

// ─── median (numpy semantics: avg of two middles for even-length) ─────────────
// File-local copy; the one in EcgReview.cpp is not exported.
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

// ─── ASCII upper-case ─────────────────────────────────────────────────────────
std::string upper(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (unsigned char c : s) {
        out.push_back(static_cast<char>(std::toupper(c)));
    }
    return out;
}

// ─── _channel_selection_score (file-local) ────────────────────────────────────
// Multiplies qrs_like_score by the number of valid RR-intervals detected,
// which rewards channels with regular QRS complexes.
//
//   peaks      = detect_r_peaks(values, sr)
//   summary    = heart_rate_summary(peaks, sr)
//   regularity = max(1, summary.valid_rr_count)
//   return qrs_like_score(values, sr) * regularity
double _channel_selection_score(const std::vector<double>& values, double sr) {
    const std::vector<int>  peaks   = detect_r_peaks(values, sr);
    const HeartRateSummary  summary = heart_rate_summary(peaks, sr);
    const double regularity = static_cast<double>(std::max(1, summary.valid_rr_count));
    return qrs_like_score(values, sr) * regularity;
}

} // anonymous namespace

// ─── qrs_like_score ───────────────────────────────────────────────────────────
double qrs_like_score(const std::vector<double>& values, double sample_rate_hz) {
    // Step 1: bandpass filter (P5a defaults: 0.7–35 Hz)
    const std::vector<double> filtered = bandpass(values, sample_rate_hz);

    // Step 2: size guard
    if (filtered.size() < 100) {
        return 0.0;
    }

    const std::size_t n = filtered.size();

    // Step 3: center by median
    const double med = median(filtered);
    std::vector<double> centered(n);
    for (std::size_t i = 0; i < n; ++i) {
        centered[i] = filtered[i] - med;
    }

    // Step 4: first differences of centered (np.diff, length n-1)
    const std::size_t nd = n - 1;
    std::vector<double> diff(nd);
    for (std::size_t i = 0; i < nd; ++i) {
        diff[i] = centered[i + 1] - centered[i];
    }

    // Step 5: MAD of diff
    //   med_diff = median(diff)
    //   abs_dev[i] = |diff[i] - med_diff|
    //   mad = median(abs_dev) + 1e-9
    const double med_diff = median(diff);
    std::vector<double> abs_dev(nd);
    for (std::size_t i = 0; i < nd; ++i) {
        abs_dev[i] = std::abs(diff[i] - med_diff);
    }
    const double mad = median(abs_dev) + 1e-9;

    // Step 6: percentile(|diff|, 99) / mad
    std::vector<double> abs_diff(nd);
    for (std::size_t i = 0; i < nd; ++i) {
        abs_diff[i] = std::abs(diff[i]);
    }
    return percentile(abs_diff, 99.0) / mad;
}

// ─── choose_ecg_channel ───────────────────────────────────────────────────────
ChannelChoice choose_ecg_channel(const std::vector<double>& ch1,
                                  const std::vector<double>& ch2,
                                  double sample_rate_hz,
                                  const std::string& override_source) {
    const std::string ov = upper(override_source);

    const double score_ch1  = qrs_like_score(ch1, sample_rate_hz);
    const double score_ch2  = qrs_like_score(ch2, sample_rate_hz);

    const double select_ch1 = _channel_selection_score(ch1, sample_rate_hz);
    const double select_ch2 = _channel_selection_score(ch2, sample_rate_hz);

    const double denominator = std::max(std::min(select_ch1, select_ch2), 1e-9);
    const double confidence  = std::max(select_ch1, select_ch2) / denominator;

    if (ov == "CH1" || ov == "CH2") {
        return { ov, score_ch1, score_ch2, confidence };
    }

    const std::string channel = (select_ch2 > select_ch1 * 1.05) ? "CH2" : "CH1";
    return { channel, score_ch1, score_ch2, confidence };
}

// ─── review_channels ─────────────────────────────────────────────────────────
ReviewResult review_channels(const std::vector<double>& ch1,
                              const std::vector<double>& ch2,
                              double sample_rate_hz,
                              const std::string& source) {
    const ChannelChoice choice = choose_ecg_channel(ch1, ch2, sample_rate_hz, source);

    const std::vector<double>& selected = (choice.channel == "CH2") ? ch2 : ch1;

    const std::vector<int>   peaks      = detect_r_peaks(selected, sample_rate_hz);
    const HeartRateSummary   heart_rate = heart_rate_summary(peaks, sample_rate_hz);
    const PqrstReview        pqrst      = pqrst_review(selected, peaks, sample_rate_hz);

    return { choice, peaks, heart_rate, pqrst };
}

} // namespace ads1292::dsp
