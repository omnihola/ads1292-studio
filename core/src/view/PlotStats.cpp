// core/src/view/PlotStats.cpp
// Statistical helpers for plot rendering.
// Faithful port of plots.py robust_ylim().
// Pure C++17, no Qt, no OS. All computations in double.

#include "ads1292/view/PlotStats.h"
#include "ads1292/dsp/Stats.h"

#include <algorithm>
#include <cmath>

namespace ads1292::view {

std::pair<double, double> robust_ylim(const std::vector<double>& values,
                                       double min_span)
{
    if (values.empty()) {
        return {-1.0, 1.0};
    }

    double lo, hi;
    if (values.size() > 50) {
        lo = ads1292::dsp::percentile(values, 1.0);
        hi = ads1292::dsp::percentile(values, 99.0);
    } else {
        const auto [mn, mx] = std::minmax_element(values.begin(), values.end());
        lo = *mn;
        hi = *mx;
    }

    if (lo == hi) {
        lo -= 1.0;
        hi += 1.0;
    }

    const double span = hi - lo;
    if (span < min_span) {
        const double center = (hi + lo) / 2.0;
        lo = center - min_span / 2.0;
        hi = center + min_span / 2.0;
    }

    const double pad = std::max(1.0, 0.15 * (hi - lo));
    return {lo - pad, hi + pad};
}

} // namespace ads1292::view
