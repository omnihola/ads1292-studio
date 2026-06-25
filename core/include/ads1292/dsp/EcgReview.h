#pragma once
// core/include/ads1292/dsp/EcgReview.h
// ECG analysis chain: detect_r_peaks.
// Pure C++17, no Qt, no OS. All computations in double.

#include <vector>

namespace ads1292::dsp {

/// Detects R-peaks in an ECG signal using a bandpass + centering + find_peaks chain.
/// Faithfully reproduces signal_processing.py detect_r_peaks().
///
/// Returns empty if:
///   - sample_rate_hz is not finite or <= 0
///   - values.size() < (size_t)(int)sample_rate_hz
///
/// Algorithm:
///   1. filtered  = bandpass(values, sr)
///   2. centered  = filtered - median(filtered)
///   3. scale     = population std of centered (ddof=0)
///   4. prominence = max(20.0, scale * 0.45)
///   5. polarity: pos = max(centered), neg = |min(centered)|
///      peak_signal = (pos >= neg) ? centered : -centered
///   6. peaks = find_peaks(peak_signal, distance=(int)(0.35*sr), prominence)
///   7. return peaks (ascending int indices)
std::vector<int> detect_r_peaks(const std::vector<double>& values,
                                 double sample_rate_hz);

/// Heart rate statistics computed from R-peak indices.
/// All values are in double precision. Matches signal_processing.py
/// heart_rate_summary().
struct HeartRateSummary {
    double median_bpm;     ///< Median beat-rate in BPM (or 0.0 if invalid)
    double min_bpm;        ///< Minimum beat-rate in BPM (or 0.0 if invalid)
    double max_bpm;        ///< Maximum beat-rate in BPM (or 0.0 if invalid)
    int valid_rr_count;    ///< Number of valid R-R intervals (or 0 if invalid)
};

/// Computes heart-rate summary statistics from R-peak indices.
/// Returns {0.0, 0.0, 0.0, 0} if:
///   - peaks.size() < 2
///   - sample_rate_hz is not finite or <= 0
///   - no valid R-R intervals (all BPM values outside 40..180 range)
///
/// Algorithm:
///   1. rr[i] = (peaks[i+1] - peaks[i]) / sr for i in 0..size-2
///   2. bpm[i] = 60.0 / rr[i]
///   3. valid = bpm values with 40 <= bpm <= 180
///   4. if valid.empty(): return {0, 0, 0, 0}
///   5. else: return {median(valid), min(valid), max(valid), valid.size()}
///   (median = numpy semantics: avg of two middles for even length)
HeartRateSummary heart_rate_summary(const std::vector<int>& peaks,
                                     double sample_rate_hz);

} // namespace ads1292::dsp
