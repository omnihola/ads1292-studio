// core/src/dsp/Stats.cpp
// Numpy-faithful statistical primitives: percentile, mean.
// Pure C++17, no Qt. All double.

#include "ads1292/dsp/Stats.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <vector>

namespace ads1292::dsp {

double percentile(const std::vector<double>& x, double q) {
    // Sort a copy ascending
    std::vector<double> xs(x);
    std::sort(xs.begin(), xs.end());

    const std::size_t n = xs.size();
    // n >= 1 assumed by callers

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

} // namespace ads1292::dsp
