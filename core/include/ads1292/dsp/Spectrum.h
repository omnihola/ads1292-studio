#pragma once
// core/include/ads1292/dsp/Spectrum.h
// Hann-windowed rFFT spectrum analysis and histogram.
// Pure C++17, no Qt. All computations in double. Uses vendored KissFFT (double).

#include "ads1292/model/StreamSample.h"

#include <complex>
#include <string>
#include <vector>

namespace ads1292::dsp {

/// KissFFT real-FFT wrapper (kiss_fftr, double precision).
/// Returns n/2+1 complex bins for a real input of length n.
/// Input must have n >= 1. For odd n, kiss_fftr is called on even(n)?
/// The fixture is N=2048 (even); even input is required.
std::vector<std::complex<double>> rfft(const std::vector<double>& x);

/// Result of build_spectrum_analysis.
struct SpectrumAnalysis {
    std::string ecg_label;
    std::vector<double> ecg_frequency_hz;
    std::vector<double> ecg_power;
    std::vector<long>   histogram_counts;
    std::vector<double> histogram_bin_edges;
};

/// Build Hann-windowed power spectrum and amplitude histogram from StreamSamples.
/// source: "CH1" or "CH2" selects the channel.
/// max_frequency_hz: keep only freq <= this value.
/// histogram_bins: number of histogram bins over the raw sample values.
SpectrumAnalysis build_spectrum_analysis(
    const std::vector<ads1292::StreamSample>& samples,
    const std::string& source,
    double sample_rate_hz,
    double max_frequency_hz = 60.0,
    int histogram_bins = 48);

} // namespace ads1292::dsp
