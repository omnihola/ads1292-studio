// core/src/dsp/Stats.cpp
// Numpy-faithful statistical primitives: percentile, mean, hanning, histogram.
// Pure C++17, no Qt. All double.

#include "ads1292/dsp/Stats.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <vector>

namespace ads1292::dsp {

double percentile(const std::vector<double>& x, double q) {
    std::vector<double> xs(x);
    std::sort(xs.begin(), xs.end());

    const std::size_t n = xs.size();
    const double pos = (q / 100.0) * static_cast<double>(n - 1);
    const std::size_t lo = static_cast<std::size_t>(std::floor(pos));
    const double frac = pos - static_cast<double>(lo);

    if (lo + 1 < n) {
        return xs[lo] + frac * (xs[lo + 1] - xs[lo]);
    }
    return xs[lo];
}

double mean(const std::vector<double>& x) {
    if (x.empty()) return 0.0;
    return std::accumulate(x.begin(), x.end(), 0.0) /
           static_cast<double>(x.size());
}

std::vector<double> hanning(int M) {
    if (M <= 0) return {};
    if (M == 1) return {1.0};
    const double pi = std::acos(-1.0);
    std::vector<double> w(static_cast<std::size_t>(M));
    for (int n = 0; n < M; ++n) {
        w[static_cast<std::size_t>(n)] =
            0.5 - 0.5 * std::cos(2.0 * pi * n / (M - 1));
    }
    return w;
}

void histogram(const std::vector<double>& v, int bins,
               std::vector<long>& counts, std::vector<double>& edges) {
    if (bins <= 0) bins = 1;
    counts.assign(static_cast<std::size_t>(bins), 0L);
    edges.resize(static_cast<std::size_t>(bins + 1));

    if (v.empty()) {
        for (int i = 0; i <= bins; ++i)
            edges[static_cast<std::size_t>(i)] = static_cast<double>(i);
        return;
    }

    double lo = *std::min_element(v.begin(), v.end());
    double hi = *std::max_element(v.begin(), v.end());
    if (lo == hi) { lo -= 0.5; hi += 0.5; }

    const double range = hi - lo;
    // Build edges: edges[i] = lo + i*(hi-lo)/bins; force last to hi exactly.
    for (int i = 0; i < bins; ++i)
        edges[static_cast<std::size_t>(i)] =
            lo + static_cast<double>(i) * range / static_cast<double>(bins);
    edges[static_cast<std::size_t>(bins)] = hi;

    const double norm = static_cast<double>(bins) / range;

    for (double val : v) {
        int k = static_cast<int>((val - lo) * norm);
        if (k >= bins) k = bins - 1;
        // numpy float correction: decrement if val fell below the bin edge
        while (k > 0 && val < edges[static_cast<std::size_t>(k)]) --k;
        // numpy float correction: increment if val is >= next edge
        while (k < bins - 1 && val >= edges[static_cast<std::size_t>(k + 1)]) ++k;
        counts[static_cast<std::size_t>(k)]++;
    }
}

} // namespace ads1292::dsp
