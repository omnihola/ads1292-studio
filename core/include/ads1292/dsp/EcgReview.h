#pragma once
// core/include/ads1292/dsp/EcgReview.h
// ECG analysis chain: detect_r_peaks, heart_rate_summary, pqrst_review.
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
/// @param prefiltered  If true, skip the bandpass step (signal already filtered).
///                     Default false — keeps all existing callers working unchanged.
///
/// Algorithm:
///   1. filtered  = prefiltered ? values : bandpass(values, sr)
///   2. centered  = filtered - median(filtered)
///   3. scale     = population std of centered (ddof=0)
///   4. prominence = max(20.0, scale * 0.45)
///   5. polarity: pos = max(centered), neg = |min(centered)|
///      peak_signal = (pos >= neg) ? centered : -centered
///   6. peaks = find_peaks(peak_signal, distance=(int)(0.35*sr), prominence)
///   7. return peaks (ascending int indices)
std::vector<int> detect_r_peaks(const std::vector<double>& values,
                                 double sample_rate_hz,
                                 bool prefiltered = false);

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

/// Average-beat morphology review computed from windowed, baseline-corrected beats.
/// Matches signal_processing.py pqrst_review().
struct PqrstReview {
    bool qrs_clear;                 ///< True if QRS amplitude is clearly above noise
    bool p_tentative;               ///< True if P-wave range is above noise threshold
    bool t_tentative;               ///< True if T-wave range is above noise threshold
    int beats_used;                 ///< Number of beats contributing to the average
    std::vector<double> average_beat; ///< Per-sample average beat (length pre+post)
    std::vector<double> time_ms;    ///< Timestamps in ms relative to R-peak (length pre+post)
};

/// Computes average-beat ECG morphology and classifies QRS/P/T visibility.
/// Returns {false,false,false,0,{},{}} if:
///   - No beats fall within the signal bounds.
///
/// Algorithm:
///   1. filtered = bandpass(values, sr, low=0.15, high=40.0)
///   2. pre=(int)(0.25*sr), post=(int)(0.55*sr)
///   3. For each peak: skip if peak-pre<0 or peak+post>filtered.size();
///      beat = filtered[peak-pre .. peak+post);
///      baseline = median(beat[0 .. max(1,(int)(0.12*sr))]);
///      subtract baseline from every element of beat; collect.
///   4. avg[j] = mean over collected beats of beat[j]  (per-index average)
///   5. r_amp = |avg[pre]|
///   6. half = max(1, pre/2)
///   7. noise = median(|avg[0..half) - median(avg[0..half))|) + 1e-9  (MAD of first half)
///   8. p_start=pre-(int)(0.22*sr), p_end=pre-(int)(0.08*sr),
///      t_start=pre+(int)(0.12*sr), t_end=pre+(int)(0.38*sr)
///   9. p_range = ptp(avg[p_start..p_end)) if p_end>p_start else 0
///      t_range = ptp(avg[t_start..t_end)) if t_end>t_start else 0
///  10. qrs_clear = r_amp > max(40, noise*8)
///      p_tentative = p_range > max(15, noise*3)
///      t_tentative = t_range > max(25, noise*4)
///  11. time_ms[i] = ((i-pre)/sr)*1000 for i in 0..pre+post-1
PqrstReview pqrst_review(const std::vector<double>& values,
                          const std::vector<int>& peaks,
                          double sample_rate_hz);

} // namespace ads1292::dsp
