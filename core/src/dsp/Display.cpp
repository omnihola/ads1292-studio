// core/src/dsp/Display.cpp
// Software display filter chain — reuses P5a verified filtfilt wrappers.
// Pure C++17, no Qt, no OS.

#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/Filtfilt.h"

namespace ads1292::dsp {

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

} // namespace ads1292::dsp
