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

} // namespace ads1292::dsp
