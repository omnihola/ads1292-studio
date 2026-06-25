#pragma once
// core/include/ads1292/dsp/Peaks.h
// Faithful port of scipy.signal.find_peaks (local maxima + distance + prominence).
// Pure C++17, no Qt, no OS. All computations in double/int.

#include <vector>

namespace ads1292::dsp {

/// Returns indices of peaks in x that satisfy the given distance and prominence
/// constraints, applying conditions in SciPy's order:
///   1. local maxima (_local_maxima_1d): plateau midpoint rule.
///   2. distance (_select_by_peak_distance): descending-height priority, stable.
///   3. prominence (_peak_prominences): left/right contour walk.
///
/// Returns surviving peak indices in ascending order.
std::vector<int> find_peaks(const std::vector<double>& x,
                             int distance,
                             double prominence_min);

} // namespace ads1292::dsp
