// core/src/dsp/Iir.cpp
// Butterworth coefficient generation replicating SciPy's zpk pipeline.
// Pure C++17. No Qt, no OS dependencies.

#include "ads1292/dsp/Iir.h"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <complex>
#include <numeric>
#include <vector>

namespace ads1292::dsp {

// ── Internal helpers ─────────────────────────────────────────────────────────

using Cx = std::complex<double>;
static constexpr double PI = 3.141592653589793238462643383279502884197;

// Multiply polynomial (stored highest-degree first, as returned by poly())
// by the linear factor (x - root), extending length by 1.
static std::vector<Cx> poly_extend(const std::vector<Cx>& p, Cx root) {
    // p has degree n, result has degree n+1.
    std::vector<Cx> q(p.size() + 1, Cx{0, 0});
    // q[i] = p[i-1] - root*p[i]  (with p[-1]=0, p[n]=0 boundaries)
    for (std::size_t i = 0; i < p.size(); ++i) {
        q[i]     += p[i];
        q[i + 1] -= root * p[i];
    }
    return q;
}

// ── poly ─────────────────────────────────────────────────────────────────────

std::vector<double> poly(const std::vector<Cx>& roots) {
    // Start with monic polynomial of degree 0: {1}
    std::vector<Cx> coeffs{Cx{1.0, 0.0}};
    for (const Cx& r : roots) {
        coeffs = poly_extend(coeffs, r);
    }
    // Take real parts (imaginary parts should be ~0 for conjugate-pair roots)
    std::vector<double> result(coeffs.size());
    for (std::size_t i = 0; i < coeffs.size(); ++i) {
        result[i] = coeffs[i].real();
    }
    return result;
}

// ── buttap ───────────────────────────────────────────────────────────────────

Zpk buttap(int N) {
    // Analog Butterworth prototype: z={}, k=1, poles at
    //   p[k] = -exp(i*pi*m/(2*N))  for m in arange(-N+1, N, 2)
    // arange(-N+1, N, 2) produces N values: -N+1, -N+3, ..., N-3, N-1
    Zpk zpk;
    zpk.z.clear();
    zpk.k = 1.0;
    zpk.p.reserve(static_cast<std::size_t>(N));
    for (int i = 0; i < N; ++i) {
        int m = -N + 1 + 2 * i; // arange(-N+1, N, 2)[i]
        // p = -exp(i*pi*m/(2*N))
        double angle = PI * static_cast<double>(m) / (2.0 * static_cast<double>(N));
        Cx e{std::cos(angle), std::sin(angle)};
        zpk.p.push_back(-e);
    }
    return zpk;
}

// ── lp2lp_zpk ────────────────────────────────────────────────────────────────

Zpk lp2lp_zpk(const Zpk& zpk, double wo) {
    // degree = len(p) - len(z)
    int degree = static_cast<int>(zpk.p.size()) - static_cast<int>(zpk.z.size());

    Zpk out;
    // z_lp = z * wo
    out.z.reserve(zpk.z.size());
    for (const Cx& z : zpk.z) out.z.push_back(z * wo);
    // p_lp = p * wo
    out.p.reserve(zpk.p.size());
    for (const Cx& p : zpk.p) out.p.push_back(p * wo);
    // k_lp = k * wo^degree
    out.k = zpk.k * std::pow(wo, static_cast<double>(degree));
    return out;
}

// ── lp2hp_zpk ────────────────────────────────────────────────────────────────

Zpk lp2hp_zpk(const Zpk& zpk, double wo) {
    // degree = len(p) - len(z)
    int degree = static_cast<int>(zpk.p.size()) - static_cast<int>(zpk.z.size());

    Zpk out;
    // z_hp = wo / z  (element-wise), then append 'degree' zeros
    out.z.reserve(zpk.z.size() + static_cast<std::size_t>(degree));
    for (const Cx& z : zpk.z) out.z.push_back(Cx{wo, 0.0} / z);
    for (int i = 0; i < degree; ++i) out.z.push_back(Cx{0.0, 0.0});

    // p_hp = wo / p
    out.p.reserve(zpk.p.size());
    for (const Cx& p : zpk.p) out.p.push_back(Cx{wo, 0.0} / p);

    // k_hp = k * real(prod(-z) / prod(-p))
    // prod(-z): product of (-z[i]) for all original z[i] in zpk.z
    // prod(-p): product of (-p[i]) for all original p[i] in zpk.p
    Cx prod_neg_z{1.0, 0.0};
    for (const Cx& z : zpk.z) prod_neg_z *= (-z);
    Cx prod_neg_p{1.0, 0.0};
    for (const Cx& p : zpk.p) prod_neg_p *= (-p);

    out.k = zpk.k * (prod_neg_z / prod_neg_p).real();
    return out;
}

// ── lp2bp_zpk ────────────────────────────────────────────────────────────────

Zpk lp2bp_zpk(const Zpk& zpk, double wo, double bw) {
    // degree = len(p) - len(z)
    int degree = static_cast<int>(zpk.p.size()) - static_cast<int>(zpk.z.size());

    // Scale: z_lp = z * bw/2,  p_lp = p * bw/2
    std::vector<Cx> z_lp, p_lp;
    z_lp.reserve(zpk.z.size());
    for (const Cx& z : zpk.z) z_lp.push_back(z * (bw / 2.0));
    p_lp.reserve(zpk.p.size());
    for (const Cx& p : zpk.p) p_lp.push_back(p * (bw / 2.0));

    // z_bp = z_lp + sqrt(z_lp^2 - wo^2)  concatenated with
    //        z_lp - sqrt(z_lp^2 - wo^2)
    Cx wo2{wo * wo, 0.0};
    Zpk out;
    out.z.reserve(2 * z_lp.size() + static_cast<std::size_t>(degree));
    for (const Cx& zl : z_lp) {
        Cx disc = std::sqrt(zl * zl - wo2);
        out.z.push_back(zl + disc);
        out.z.push_back(zl - disc);
    }
    // append 'degree' zeros
    for (int i = 0; i < degree; ++i) out.z.push_back(Cx{0.0, 0.0});

    out.p.reserve(2 * p_lp.size());
    for (const Cx& pl : p_lp) {
        Cx disc = std::sqrt(pl * pl - wo2);
        out.p.push_back(pl + disc);
        out.p.push_back(pl - disc);
    }

    // k_bp = k * bw^degree
    out.k = zpk.k * std::pow(bw, static_cast<double>(degree));
    return out;
}

// ── bilinear_zpk ─────────────────────────────────────────────────────────────

Zpk bilinear_zpk(const Zpk& zpk, double fs) {
    double fs2 = 2.0 * fs; // = 4.0 when fs=2.0
    int degree = static_cast<int>(zpk.p.size()) - static_cast<int>(zpk.z.size());

    Zpk out;
    // z_d = (fs2 + z) / (fs2 - z)
    out.z.reserve(zpk.z.size() + static_cast<std::size_t>(degree));
    for (const Cx& z : zpk.z) {
        Cx fs2c{fs2, 0.0};
        out.z.push_back((fs2c + z) / (fs2c - z));
    }
    // Append 'degree' zeros at -1
    for (int i = 0; i < degree; ++i) out.z.push_back(Cx{-1.0, 0.0});

    // p_d = (fs2 + p) / (fs2 - p)
    out.p.reserve(zpk.p.size());
    for (const Cx& p : zpk.p) {
        Cx fs2c{fs2, 0.0};
        out.p.push_back((fs2c + p) / (fs2c - p));
    }

    // k_d = k * real(prod(fs2 - z) / prod(fs2 - p))
    Cx prod_z{1.0, 0.0};
    for (const Cx& z : zpk.z) prod_z *= (Cx{fs2, 0.0} - z);
    Cx prod_p{1.0, 0.0};
    for (const Cx& p : zpk.p) prod_p *= (Cx{fs2, 0.0} - p);

    out.k = zpk.k * (prod_z / prod_p).real();
    return out;
}

// ── zpk2tf ───────────────────────────────────────────────────────────────────

Coeffs zpk2tf(const Zpk& zpk) {
    Coeffs c;
    auto b_poly = poly(zpk.z);
    for (double& v : b_poly) v *= zpk.k;
    c.b = std::move(b_poly);
    c.a = poly(zpk.p);
    return c;
}

// ── butter (single-band, digital, fs=2.0) ────────────────────────────────────

static Coeffs butter_lowpass_impl(int N, double Wn) {
    // Analog prototype
    Zpk zpk = buttap(N);
    // Prewarp: warped = 2*fs*tan(pi*Wn/fs) = 4*tan(pi*Wn/2)  [fs=2.0]
    double warped = 4.0 * std::tan(PI * Wn / 2.0);
    // LP → LP
    zpk = lp2lp_zpk(zpk, warped);
    // Bilinear transform
    zpk = bilinear_zpk(zpk, 2.0);
    return zpk2tf(zpk);
}

static Coeffs butter_highpass_impl(int N, double Wn) {
    Zpk zpk = buttap(N);
    double warped = 4.0 * std::tan(PI * Wn / 2.0);
    zpk = lp2hp_zpk(zpk, warped);
    zpk = bilinear_zpk(zpk, 2.0);
    return zpk2tf(zpk);
}

static Coeffs butter_bandpass_impl(int N, double Wn_low, double Wn_high) {
    // N is the prototype order; result order = 2*N (lp2bp doubles it)
    Zpk zpk = buttap(N);
    // Prewarp each edge
    double warped_low  = 4.0 * std::tan(PI * Wn_low  / 2.0);
    double warped_high = 4.0 * std::tan(PI * Wn_high / 2.0);
    double bw = warped_high - warped_low;
    double wo = std::sqrt(warped_low * warped_high);
    zpk = lp2bp_zpk(zpk, wo, bw);
    zpk = bilinear_zpk(zpk, 2.0);
    return zpk2tf(zpk);
}

// ── Public API ────────────────────────────────────────────────────────────────

Coeffs butter_bandpass(double sample_rate_hz, double low_hz, double high_hz) {
    double nyq   = sample_rate_hz / 2.0;
    double high_n = std::min(high_hz / nyq, 0.99);
    double low_n  = std::max(low_hz  / nyq, 0.0001);
    return butter_bandpass_impl(2, low_n, high_n);
}

Coeffs butter_highpass(double sample_rate_hz, double cutoff_hz) {
    double nyq  = sample_rate_hz / 2.0;
    double cut  = std::max(cutoff_hz / nyq, 0.0001);
    return butter_highpass_impl(2, cut);
}

Coeffs butter_lowpass(double sample_rate_hz, double cutoff_hz) {
    double nyq  = sample_rate_hz / 2.0;
    double cut  = std::min(cutoff_hz / nyq, 0.99);
    return butter_lowpass_impl(2, cut);
}

} // namespace ads1292::dsp
