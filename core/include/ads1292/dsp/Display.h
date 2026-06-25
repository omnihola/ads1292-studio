#pragma once
// core/include/ads1292/dsp/Display.h
// Display settings and software filter chain for live ECG rendering.
// Pure C++17, no Qt, no OS. All computations in double.

#include <string>
#include <vector>

namespace ads1292::dsp {

/// Choice tuples from display.py (exactly replicated).
/// DISPLAY_WINDOW_CHOICES = (4.0, 8.0, 12.0, 16.0)
/// DISPLAY_GAIN_CHOICES   = (0.5, 1.0, 2.0, 5.0)
/// SWEEP_SPEED_CHOICES    = (25, 50)
inline const std::vector<double> DISPLAY_WINDOW_CHOICES = {4.0, 8.0, 12.0, 16.0};
inline const std::vector<double> DISPLAY_GAIN_CHOICES   = {0.5, 1.0, 2.0, 5.0};
inline const std::vector<double> SWEEP_SPEED_CHOICES    = {25.0, 50.0};

/// Display settings controlling the visible time window, gain, and sweep speed.
struct EcgDisplaySettings {
    double time_window_seconds = 8.0;
    double gain                = 1.0;
    int    sweep_speed_mm_s    = 25;

    /// Snap each field to the nearest choice from the display.py choice tuples.
    EcgDisplaySettings normalized() const;
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

/// Return the choice from `choices` minimising |choice - v|.
/// Ties broken toward the first (smallest) choice, matching Python min().
double nearest_choice(double v, const std::vector<double>& choices);

/// Apply the software display filter chain to a signal.
///
/// Matches signal_processing.py apply_software_filters exactly:
///   - If bandpass_enabled: return bandpass(values, sr) immediately.
///   - Else: apply highpass, notch, lowpass in sequence (if each enabled).
std::vector<double> apply_software_filters(const std::vector<double>& values,
                                           double sr,
                                           const SoftwareFilterSettings& s);

/// Build a human-readable display mode label.
///
/// Matches display.py display_mode_label():
///   n = settings.normalized()
///   active: if bandpass_enabled → ["QRS"]
///           else: HP/notch/LP as enabled
///   filter_text = "raw" if empty else join with "+"
///   return filter_text + " | " + g(gain) + "x | " + g(window) + "s | " + sweep + " mm/s"
///   where g(x) uses %g formatting (no trailing zeros).
std::string display_mode_label(const EcgDisplaySettings& settings,
                                const SoftwareFilterSettings& filters);

} // namespace ads1292::dsp
