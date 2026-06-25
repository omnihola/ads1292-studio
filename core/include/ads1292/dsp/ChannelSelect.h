#pragma once
// core/include/ads1292/dsp/ChannelSelect.h
// ECG channel selection: qrs_like_score, choose_ecg_channel, review_channels.
// Pure C++17, no Qt, no OS.  All computations in double.

#include "ads1292/dsp/EcgReview.h"

#include <string>
#include <vector>

namespace ads1292::dsp {

/// QRS-like quality score for a single channel.
///
/// Algorithm:
///   1. filtered = bandpass(values, sr)            (P5a defaults: 0.7–35 Hz)
///   2. if filtered.size() < 100 → return 0.0
///   3. centered = filtered - median(filtered)
///   4. diff[i] = centered[i+1] - centered[i]      (np.diff, length n-1)
///   5. mad = median(|diff - median(diff)|) + 1e-9
///   6. return percentile(|diff|, 99.0) / mad
double qrs_like_score(const std::vector<double>& values, double sample_rate_hz);

/// Result of choose_ecg_channel / review_channels.
struct ChannelChoice {
    std::string channel;   ///< "CH1" or "CH2"
    double score_ch1;      ///< qrs_like_score for ch1
    double score_ch2;      ///< qrs_like_score for ch2
    double confidence;     ///< max(sel) / max(min(sel), 1e-9)
};

/// Selects the better ECG channel (or honours an override).
///
/// Algorithm:
///   override = upper(override_source)
///   score_ch1 = qrs_like_score(ch1, sr)
///   score_ch2 = qrs_like_score(ch2, sr)
///   select_ch1 = _channel_selection_score(ch1, sr)   (file-local)
///   select_ch2 = _channel_selection_score(ch2, sr)
///   denominator = max(min(select_ch1, select_ch2), 1e-9)
///   confidence  = max(select_ch1, select_ch2) / denominator
///   if override == "CH1" || override == "CH2":
///       return { override, score_ch1, score_ch2, confidence }
///   else:
///       channel = (select_ch2 > select_ch1 * 1.05) ? "CH2" : "CH1"
///       return { channel, score_ch1, score_ch2, confidence }
ChannelChoice choose_ecg_channel(const std::vector<double>& ch1,
                                  const std::vector<double>& ch2,
                                  double sample_rate_hz,
                                  const std::string& override_source);

/// Full channel-selected review result.
struct ReviewResult {
    ChannelChoice         source;
    std::vector<int>      peaks;
    HeartRateSummary      heart_rate;
    PqrstReview           pqrst;
};

/// Runs the full review pipeline on the better (or overridden) channel.
///
/// Algorithm:
///   choice   = choose_ecg_channel(ch1, ch2, sr, source)
///   selected = (choice.channel == "CH2") ? ch2 : ch1
///   peaks    = detect_r_peaks(selected, sr)
///   heart_rate = heart_rate_summary(peaks, sr)
///   pqrst    = pqrst_review(selected, peaks, sr)
///   return { choice, peaks, heart_rate, pqrst }
ReviewResult review_channels(const std::vector<double>& ch1,
                              const std::vector<double>& ch2,
                              double sample_rate_hz,
                              const std::string& source);

} // namespace ads1292::dsp
