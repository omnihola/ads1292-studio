// core/src/dsp/Filtfilt.cpp
// Zero-phase IIR filtering and public filter wrappers.
// Replicates scipy.signal.filtfilt (SciPy defaults: odd extension, lfilter_zi).
// Pure C++17, no Qt, no OS. All double.

#include "ads1292/dsp/Filtfilt.h"
#include "ads1292/dsp/Iir.h"

#include <algorithm>
#include <cmath>
#include <vector>

namespace ads1292::dsp {

// ── Helpers ───────────────────────────────────────────────────────────────────

/// Compute the median of a vector (numpy.median: average the two middle values
/// for even-length arrays). Returns 0.0 for empty vectors.
static double median(const std::vector<double>& v) {
    if (v.empty()) return 0.0;
    std::vector<double> s = v;
    std::sort(s.begin(), s.end());
    const std::size_t n = s.size();
    if (n % 2 == 1) {
        return s[n / 2];
    } else {
        return 0.5 * (s[n / 2 - 1] + s[n / 2]);
    }
}

// ── filtfilt ──────────────────────────────────────────────────────────────────

std::vector<double> filtfilt(const Coeffs& c, const std::vector<double>& x) {
    // ntaps = max(len(a), len(b))
    const std::size_t ntaps =
        std::max(c.a.size(), c.b.size());

    // padlen = 3 * ntaps   [SciPy default: edge = ntaps * 3 in _validate_pad]
    const std::size_t padlen = 3 * ntaps;

    // Guard: if signal is too short, return as-is (wrappers prevent this
    // for well-formed inputs, but be defensive).
    if (x.empty()) return x;
    if (padlen >= x.size()) {
        // Cannot extend safely; return x unchanged
        return x;
    }

    const std::size_t n = x.size();

    // ── Odd extension ────────────────────────────────────────────────────────
    // SciPy odd_ext(x, padlen):
    //   left  = 2*x[0]  - x[padlen:0:-1]   (i.e. x[padlen], x[padlen-1], ..., x[1])
    //   right = 2*x[-1] - x[-2:-padlen-2:-1] (i.e. x[-2], x[-3], ..., x[-(padlen+1)])
    //
    // Resulting extended signal: [left | x | right], length = n + 2*padlen.
    //
    // left[i]  = 2*x[0]    - x[padlen - i]   for i in 0..padlen-1
    //   (left[0] uses x[padlen], left[padlen-1] uses x[1])
    //
    // right[i] = 2*x[n-1]  - x[n-2 - i]      for i in 0..padlen-1
    //   (right[0] uses x[n-2], right[padlen-1] uses x[n-1-padlen])

    const std::size_t ext_len = n + 2 * padlen;
    std::vector<double> ext;
    ext.reserve(ext_len);

    // Left extension: e[i] = 2*x[0] - x[padlen - i]  for i=0..padlen-1
    for (std::size_t i = 0; i < padlen; ++i) {
        ext.push_back(2.0 * x[0] - x[padlen - i]);
    }
    // Original signal
    for (std::size_t i = 0; i < n; ++i) {
        ext.push_back(x[i]);
    }
    // Right extension: e[i] = 2*x[n-1] - x[n-2 - i]  for i=0..padlen-1
    for (std::size_t i = 0; i < padlen; ++i) {
        ext.push_back(2.0 * x[n - 1] - x[n - 2 - i]);
    }

    // ── Steady-state initial conditions ──────────────────────────────────────
    const std::vector<double> zi = lfilter_zi(c);

    // ── Forward pass ─────────────────────────────────────────────────────────
    // Scale zi by ext[0] (first element of the extended signal)
    std::vector<double> zi_fwd(zi.size());
    for (std::size_t k = 0; k < zi.size(); ++k) {
        zi_fwd[k] = zi[k] * ext[0];
    }
    std::vector<double> y = lfilter(c, ext, zi_fwd);

    // ── Reverse ──────────────────────────────────────────────────────────────
    std::reverse(y.begin(), y.end());

    // ── Backward pass ────────────────────────────────────────────────────────
    // Scale zi by y[0] (first element of the reversed signal)
    std::vector<double> zi_bwd(zi.size());
    for (std::size_t k = 0; k < zi.size(); ++k) {
        zi_bwd[k] = zi[k] * y[0];
    }
    std::vector<double> y2 = lfilter(c, y, zi_bwd);

    // ── Reverse again and strip padding ──────────────────────────────────────
    std::reverse(y2.begin(), y2.end());

    // Slice off padlen from each end → length n
    return std::vector<double>(y2.begin() + static_cast<std::ptrdiff_t>(padlen),
                               y2.begin() + static_cast<std::ptrdiff_t>(padlen + n));
}

// ── Public wrappers ───────────────────────────────────────────────────────────

std::vector<double> bandpass(const std::vector<double>& v,
                             double sr,
                             double low_hz,
                             double high_hz) {
    if (v.size() < 16) {
        // Fallback: subtract median
        if (v.empty()) return v;
        double m = median(v);
        std::vector<double> out(v.size());
        for (std::size_t i = 0; i < v.size(); ++i) out[i] = v[i] - m;
        return out;
    }
    return filtfilt(butter_bandpass(sr, low_hz, high_hz), v);
}

std::vector<double> highpass(const std::vector<double>& v,
                             double sr,
                             double cutoff_hz) {
    if (v.size() < 16) {
        if (v.empty()) return v;
        double m = median(v);
        std::vector<double> out(v.size());
        for (std::size_t i = 0; i < v.size(); ++i) out[i] = v[i] - m;
        return out;
    }
    return filtfilt(butter_highpass(sr, cutoff_hz), v);
}

std::vector<double> lowpass(const std::vector<double>& v,
                            double sr,
                            double cutoff_hz) {
    if (v.size() < 16) {
        // Unchanged
        return v;
    }
    return filtfilt(butter_lowpass(sr, cutoff_hz), v);
}

std::vector<double> notch(const std::vector<double>& v,
                          double sr,
                          double notch_hz,
                          double q) {
    if (v.size() < 16) {
        // Unchanged
        return v;
    }
    return filtfilt(iirnotch(sr, notch_hz, q), v);
}

} // namespace ads1292::dsp
