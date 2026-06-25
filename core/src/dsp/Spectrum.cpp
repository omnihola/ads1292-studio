// core/src/dsp/Spectrum.cpp
// Hann-windowed rFFT spectrum analysis using vendored KissFFT (double).
// Pure C++17, no Qt. All double.

#include "ads1292/dsp/Spectrum.h"
#include "ads1292/dsp/Stats.h"

// KissFFT real FFT and complex FFT (compiled with kiss_fft_scalar=double)
#include "kiss_fft.h"
#include "kiss_fftr.h"

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdlib>
#include <string>
#include <vector>

namespace ads1292::dsp {

// ----------------------------------------------------------------------------
// rfft: KissFFT FFT wrapper — matches numpy's np.fft.rfft for any n.
// Returns n/2+1 complex bins for real input of length n.
//   Even n: uses kiss_fftr (real FFT, fast path).
//   Odd  n: uses kiss_fft (complex FFT on zero-imaginary input); returns the
//            first n/2+1 bins, which are exactly numpy's rfft output because
//            rfft is defined as the non-redundant half of the full DFT.
// ----------------------------------------------------------------------------
std::vector<std::complex<double>> rfft(const std::vector<double>& x) {
    const int n = static_cast<int>(x.size());
    if (n < 1) return {};

    const int n_out = n / 2 + 1;

    if (n % 2 == 0) {
        // --- Even path: use kiss_fftr ---
        std::vector<kiss_fft_cpx> raw_out(static_cast<std::size_t>(n_out));
        // kiss_fft_scalar is double (compiled with -Dkiss_fft_scalar=double)
        kiss_fftr_cfg cfg = kiss_fftr_alloc(n, 0, nullptr, nullptr);
        if (!cfg) return {};  // defensive: alloc failed
        kiss_fftr(cfg, x.data(), raw_out.data());
        kiss_fftr_free(cfg);

        std::vector<std::complex<double>> out(static_cast<std::size_t>(n_out));
        for (int i = 0; i < n_out; ++i) {
            out[static_cast<std::size_t>(i)] =
                std::complex<double>(raw_out[static_cast<std::size_t>(i)].r,
                                     raw_out[static_cast<std::size_t>(i)].i);
        }
        return out;
    } else {
        // --- Odd path: use complex kiss_fft on zero-imaginary input ---
        // Build complex input with .i = 0
        std::vector<kiss_fft_cpx> in_buf(static_cast<std::size_t>(n));
        for (int i = 0; i < n; ++i) {
            in_buf[static_cast<std::size_t>(i)].r =
                static_cast<kiss_fft_scalar>(x[static_cast<std::size_t>(i)]);
            in_buf[static_cast<std::size_t>(i)].i = static_cast<kiss_fft_scalar>(0.0);
        }
        std::vector<kiss_fft_cpx> out_buf(static_cast<std::size_t>(n));

        kiss_fft_cfg cfg = kiss_fft_alloc(n, 0, nullptr, nullptr);
        if (!cfg) return {};  // defensive: alloc failed
        kiss_fft(cfg, in_buf.data(), out_buf.data());
        kiss_fft_free(cfg);

        // Take the first n/2+1 bins (the non-redundant half)
        std::vector<std::complex<double>> out(static_cast<std::size_t>(n_out));
        for (int i = 0; i < n_out; ++i) {
            out[static_cast<std::size_t>(i)] =
                std::complex<double>(
                    static_cast<double>(out_buf[static_cast<std::size_t>(i)].r),
                    static_cast<double>(out_buf[static_cast<std::size_t>(i)].i));
        }
        return out;
    }
}

// ----------------------------------------------------------------------------
// _fft_power: internal helper — returns (frequencies, power) filtered to
// freqs <= max_frequency_hz. Mirrors Python's _fft_power().
// ----------------------------------------------------------------------------
static std::pair<std::vector<double>, std::vector<double>>
fft_power(const std::vector<double>& values, double sr, double max_freq) {
    const std::size_t sz = values.size();
    if (sz < 2) return {{}, {}};

    // 1. Center by mean
    const double mu = mean(values);
    std::vector<double> centered(sz);
    for (std::size_t i = 0; i < sz; ++i)
        centered[i] = values[i] - mu;

    // 2. Apply Hann window
    std::vector<double> window = hanning(static_cast<int>(sz));
    std::vector<double> windowed(sz);
    for (std::size_t i = 0; i < sz; ++i)
        windowed[i] = centered[i] * window[i];

    // 3. Real FFT
    auto spectrum = rfft(windowed);
    const std::size_t n_bins = spectrum.size(); // sz/2+1

    // 4. rfftfreq: freqs[i] = i * sr / sz  for i = 0..sz/2
    // 5. power[i] = re^2 + im^2
    // 6. Keep only freqs <= max_freq
    std::vector<double> out_freq;
    std::vector<double> out_power;
    out_freq.reserve(n_bins);
    out_power.reserve(n_bins);

    for (std::size_t i = 0; i < n_bins; ++i) {
        const double freq = static_cast<double>(i) * sr / static_cast<double>(sz);
        if (freq <= max_freq) {
            const double re = spectrum[i].real();
            const double im = spectrum[i].imag();
            out_freq.push_back(freq);
            out_power.push_back(re * re + im * im);
        }
    }
    return {out_freq, out_power};
}

// ----------------------------------------------------------------------------
// build_spectrum_analysis
// ----------------------------------------------------------------------------
SpectrumAnalysis build_spectrum_analysis(
    const std::vector<ads1292::StreamSample>& samples,
    const std::string& source,
    double sample_rate_hz,
    double max_frequency_hz,
    int histogram_bins)
{
    // Extract channel values as double
    std::vector<double> values;
    values.reserve(samples.size());
    const bool use_ch1 = (source == "CH1");
    for (const auto& s : samples)
        values.push_back(use_ch1 ? static_cast<double>(s.ch1)
                                 : static_cast<double>(s.ch2));

    if (values.empty()) {
        return {source, {}, {}, {}, {}};
    }

    // Compute power spectrum
    auto [freqs, power] = fft_power(values, sample_rate_hz, max_frequency_hz);

    // Compute histogram on raw values
    const int bins = std::max(1, histogram_bins);
    std::vector<long>   hist_counts;
    std::vector<double> hist_edges;
    histogram(values, bins, hist_counts, hist_edges);

    return {source, freqs, power, hist_counts, hist_edges};
}

} // namespace ads1292::dsp
