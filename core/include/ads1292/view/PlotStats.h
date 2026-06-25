#pragma once
// core/include/ads1292/view/PlotStats.h
// Statistical helpers for plot rendering: robust_ylim.
// Pure C++17, no Qt, no OS. All computations in double.

#include <utility>
#include <vector>

namespace ads1292::view {

/// Compute robust Y-axis limits for a plot, padded to avoid clipping.
///
/// Algorithm (matches plots.py robust_ylim):
///   - size==0 → return {-1.0, 1.0}
///   - lo,hi = (size>50) ? {percentile(values,1), percentile(values,99)}
///                       : {min(values), max(values)}
///   - if lo==hi → lo -= 1.0; hi += 1.0
///   - span = hi - lo
///   - if span < min_span → center=(hi+lo)/2; lo=center-min_span/2; hi=center+min_span/2
///   - pad = max(1.0, 0.15*(hi-lo))
///   - return {lo - pad, hi + pad}
///
/// Uses the P5c numpy-linear percentile() from Stats.h.
std::pair<double, double> robust_ylim(const std::vector<double>& values,
                                       double min_span);

} // namespace ads1292::view
