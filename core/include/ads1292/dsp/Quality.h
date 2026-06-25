#pragma once
// core/include/ads1292/dsp/Quality.h
// ECG signal quality metrics: noise_rms, baseline_drift, estimate_realtime_snr.
// Pure C++17, no Qt, no OS. All computations in double.

#include <vector>

namespace ads1292::dsp {

/// Result of real-time SNR estimation.
struct SignalNoiseEstimate {
    double snr_db;               ///< Signal-to-noise ratio in dB
    double signal_rms_counts;    ///< RMS of the centered signal
    double noise_rms_counts;     ///< Estimated noise RMS (via MAD of first differences)
    double peak_to_peak_counts;  ///< percentile(95) - percentile(5)
    int sample_count;            ///< Number of finite samples
    double duration_seconds;     ///< (sample_count - 1) / sample_rate_hz
    bool valid;                  ///< True if SNR computation succeeded
};

/// Estimates noise RMS via MAD of first differences.
/// Algorithm:
///   if size < 3 → 0.0
///   diff[i] = v[i+1] - v[i]  (length n-1)
///   mad = median(|diff - median(diff)|)
///   return 1.4826 * mad / sqrt(2.0)
double noise_rms(const std::vector<double>& values);

/// Estimates baseline drift between start and end windows.
/// Algorithm:
///   if size < 2 → 0.0
///   window = max(1, min((int)sr, (int)size/2))
///   start = median(v[0 .. window))
///   end   = median(v[size-window .. size))
///   return |end - start|
double baseline_drift(const std::vector<double>& values, double sample_rate_hz);

/// Estimates real-time SNR of an ECG signal.
/// Algorithm:
///   finite = values[isfinite(v)]
///   if finite.size() < 3 → {0,0,0,0,(int)values.size(),0,false}
///   centered = finite - median(finite)
///   signal_rms = sqrt(mean(centered^2))
///   nrms = noise_rms(finite)
///   p2p = percentile(finite,95) - percentile(finite,5)
///   duration = sr > 0 ? (finite.size()-1)/sr : 0
///   if signal_rms <= 1e-12 → {0,signal_rms,nrms,p2p,size,duration,false}
///   if nrms <= 1e-12       → {80,signal_rms,nrms,p2p,size,duration,true}
///   else snr_db = 20*log10(signal_rms/nrms)
SignalNoiseEstimate estimate_realtime_snr(const std::vector<double>& values,
                                          double sample_rate_hz);

} // namespace ads1292::dsp
