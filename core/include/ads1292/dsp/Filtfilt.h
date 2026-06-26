#pragma once
// core/include/ads1292/dsp/Filtfilt.h
// Zero-phase IIR filtering (filtfilt) and public bandpass/highpass/lowpass/notch wrappers.
// Pure C++17, no Qt, no OS. All computations in double.

#include "ads1292/dsp/Iir.h"
#include <vector>

namespace ads1292::dsp {

/// Zero-phase IIR filter using SciPy's filtfilt algorithm:
///   - Odd-extension padding of length padlen = 3*ntaps on each end.
///   - Forward lfilter with zi = lfilter_zi(c) * ext[0].
///   - Backward lfilter with zi = lfilter_zi(c) * y_reversed[0].
///   - Result is the de-padded output, same length as x.
std::vector<double> filtfilt(const Coeffs& c, const std::vector<double>& x);

// ── Public filter wrappers ──────────────────────────────────────────────────
// Each mirrors signal_processing.py exactly, including the <16 median fallback.

/// Band-pass (0.7–35 Hz at 500 Hz SR by default).
/// If v.size() < 16: returns v - median(v) (or v if empty).
/// Else: filtfilt(butter_bandpass(sr, low_hz, high_hz), v).
std::vector<double> bandpass(const std::vector<double>& v,
                             double sr,
                             double low_hz  = 0.7,
                             double high_hz = 35.0);

/// High-pass (0.5 Hz cutoff by default).
/// If v.size() < 16: returns v - median(v) (or v if empty).
/// Else: filtfilt(butter_highpass(sr, cutoff_hz), v).
std::vector<double> highpass(const std::vector<double>& v,
                             double sr,
                             double cutoff_hz = 0.5);

/// Low-pass (40 Hz cutoff by default).
/// If v.size() < 16: returns v unchanged.
/// Else: filtfilt(butter_lowpass(sr, cutoff_hz), v).
std::vector<double> lowpass(const std::vector<double>& v,
                            double sr,
                            double cutoff_hz = 40.0);

/// Notch filter (60 Hz, Q=30 by default).
/// If v.size() < 16: returns v unchanged.
/// Else: filtfilt(iirnotch(sr, notch_hz, q), v).
std::vector<double> notch(const std::vector<double>& v,
                          double sr,
                          double notch_hz = 60.0,
                          double q        = 30.0);

} // namespace ads1292::dsp
