#pragma once
// core/include/ads1292/dsp/Display.h
// Display settings and software filter chain for live ECG rendering.
// Pure C++17, no Qt, no OS. All computations in double.

#include <vector>

namespace ads1292::dsp {

/// Display settings controlling the visible time window, gain, and sweep speed.
struct EcgDisplaySettings {
    double time_window_seconds = 8.0;
    double gain                = 1.0;
    int    sweep_speed_mm_s    = 25;
};

/// Software display filter settings (live filter chain).
struct SoftwareFilterSettings {
    bool   highpass_enabled  = false;
    bool   notch_enabled     = false;
    bool   lowpass_enabled   = false;
    bool   bandpass_enabled  = false;
    double highpass_hz       = 0.5;
    double notch_hz          = 60.0;
    double lowpass_hz        = 40.0;
};

/// Apply the software display filter chain to a signal.
///
/// Matches signal_processing.py apply_software_filters exactly:
///   - If bandpass_enabled: return bandpass(values, sr) immediately.
///   - Else: apply highpass, notch, lowpass in sequence (if each enabled).
std::vector<double> apply_software_filters(const std::vector<double>& values,
                                           double sr,
                                           const SoftwareFilterSettings& s);

} // namespace ads1292::dsp
