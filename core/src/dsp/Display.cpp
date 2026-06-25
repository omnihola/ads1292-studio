// core/src/dsp/Display.cpp
// Software display filter chain + display mode label + choice snapping.
// Pure C++17, no Qt, no OS.

#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/Filtfilt.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>

namespace ads1292::dsp {

// ─── nearest_choice ──────────────────────────────────────────────────────────
// Returns the element of `choices` minimising |choice - v|.
// Ties are broken toward the first (smallest) element, matching Python's min()
// which is stable and returns the first minimum found.
double nearest_choice(double v, const std::vector<double>& choices)
{
    if (choices.empty()) return v;
    double best     = choices[0];
    double best_err = std::abs(choices[0] - v);
    for (std::size_t i = 1; i < choices.size(); ++i) {
        const double err = std::abs(choices[i] - v);
        if (err < best_err) {          // strict <  → ties keep the first
            best_err = err;
            best     = choices[i];
        }
    }
    return best;
}

// ─── EcgDisplaySettings::normalized ─────────────────────────────────────────
EcgDisplaySettings EcgDisplaySettings::normalized() const
{
    EcgDisplaySettings n;
    n.time_window_seconds = nearest_choice(time_window_seconds, DISPLAY_WINDOW_CHOICES);
    n.gain                = nearest_choice(gain, DISPLAY_GAIN_CHOICES);
    n.sweep_speed_mm_s    = static_cast<int>(
        nearest_choice(static_cast<double>(sweep_speed_mm_s), SWEEP_SPEED_CHOICES));
    return n;
}

// ─── apply_software_filters ──────────────────────────────────────────────────
std::vector<double> apply_software_filters(const std::vector<double>& values,
                                           double sr,
                                           const SoftwareFilterSettings& s)
{
    // QRS bandpass overrides all individual filters and returns immediately.
    if (s.bandpass_enabled) {
        return bandpass(values, sr);
    }

    std::vector<double> display = values;

    if (s.highpass_enabled) {
        display = highpass(display, sr, s.highpass_hz);
    }
    if (s.notch_enabled) {
        display = notch(display, sr, s.notch_hz);
    }
    if (s.lowpass_enabled) {
        display = lowpass(display, sr, s.lowpass_hz);
    }

    return display;
}

// ─── display_mode_label ──────────────────────────────────────────────────────
// Helper: format a double with %g (no trailing zeros, no unnecessary decimal).
static std::string fmt_g(double v)
{
    char buf[64];
    std::snprintf(buf, sizeof(buf), "%g", v);
    return std::string(buf);
}

std::string display_mode_label(const EcgDisplaySettings& settings,
                                const SoftwareFilterSettings& filters)
{
    const EcgDisplaySettings n = settings.normalized();

    // Build active filter list matching display.py logic exactly.
    std::string filter_text;
    if (filters.bandpass_enabled) {
        filter_text = "QRS";
    } else {
        std::string parts;
        auto append = [&](const char* label) {
            if (!parts.empty()) parts += '+';
            parts += label;
        };
        if (filters.highpass_enabled) append("HP");
        if (filters.notch_enabled)    append("notch");
        if (filters.lowpass_enabled)  append("LP");
        filter_text = parts.empty() ? "raw" : parts;
    }

    // "filter_text | {gain}x | {window}s | {sweep} mm/s"
    return filter_text
        + " | " + fmt_g(n.gain)                 + "x"
        + " | " + fmt_g(n.time_window_seconds)  + "s"
        + " | " + std::to_string(n.sweep_speed_mm_s) + " mm/s";
}

} // namespace ads1292::dsp
