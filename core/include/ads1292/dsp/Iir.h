#pragma once
// core/include/ads1292/dsp/Iir.h
// Pure C++17, no Qt, no OS — Butterworth coefficient generation (SciPy-exact to 1e-12).

#include <complex>
#include <vector>

namespace ads1292::dsp {

/// Transfer-function coefficients b (numerator) and a (denominator).
struct Coeffs {
    std::vector<double> b;
    std::vector<double> a;
};

/// Zero-pole-gain representation used internally.
struct Zpk {
    std::vector<std::complex<double>> z; ///< zeros
    std::vector<std::complex<double>> p; ///< poles
    double k;                            ///< gain
};

// ── Public butter wrappers ──────────────────────────────────────────────────

/// Butterworth band-pass of order 2 (4-pole result).
/// Normalises exactly like signal_processing._bandpass_coefficients:
///   nyq = sr/2; high_n = min(high/nyq, 0.99); low_n = max(low/nyq, 0.0001)
Coeffs butter_bandpass(double sample_rate_hz, double low_hz, double high_hz);

/// Butterworth high-pass of order 2.
/// Normalises: cut = max(cutoff/(sr/2), 0.0001)
Coeffs butter_highpass(double sample_rate_hz, double cutoff_hz);

/// Butterworth low-pass of order 2.
/// Normalises: cut = min(cutoff/(sr/2), 0.99)
Coeffs butter_lowpass(double sample_rate_hz, double cutoff_hz);

/// IIR notch filter.
/// Normalises: w0 = min(notch_hz/(sr/2), 0.99)
Coeffs iirnotch(double sample_rate_hz, double notch_hz, double q);

// ── Internal pipeline (exposed for testing) ─────────────────────────────────

/// Butterworth analog prototype of order N.
/// z = {}, p[k] = -exp(i*pi*m/(2*N)) for m in arange(-N+1,N,2), k=1.
Zpk buttap(int N);

/// Low-pass → low-pass frequency transform in ZPK form.
Zpk lp2lp_zpk(const Zpk& zpk, double wo);

/// Low-pass → high-pass frequency transform in ZPK form.
Zpk lp2hp_zpk(const Zpk& zpk, double wo);

/// Low-pass → band-pass frequency transform in ZPK form.
/// wo = geometric center, bw = bandwidth (both in rad/s after prewarp).
Zpk lp2bp_zpk(const Zpk& zpk, double wo, double bw);

/// Bilinear transform: s-domain ZPK → z-domain ZPK (fs = 2.0 as SciPy default).
Zpk bilinear_zpk(const Zpk& zpk, double fs = 2.0);

/// Expand roots into monic polynomial coefficients (real part taken at end).
/// poly({r0,r1,...}) = coefficients of prod(x - ri), highest-degree first.
std::vector<double> poly(const std::vector<std::complex<double>>& roots);

/// Convert ZPK to transfer-function Coeffs: b = k*poly(z), a = poly(p).
Coeffs zpk2tf(const Zpk& zpk);

} // namespace ads1292::dsp
