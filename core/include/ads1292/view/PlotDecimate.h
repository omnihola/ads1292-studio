#pragma once
// core/include/ads1292/view/PlotDecimate.h
// Plot helpers: smoothing, index selection, and decimation for display rendering.
// Pure C++17, no Qt, no OS. All computations in double.

#include <vector>

namespace ads1292::view {

/// Smooth a signal with a box (moving average) filter for display purposes.
///
/// Matches plots.py smooth_for_plot exactly:
///   - window <= 1 or values.size() < window: return values unchanged.
///   - If window is even: window += 1 (force odd).
///   - pad = window / 2; edge-pad values by repeating first/last element pad times.
///   - Apply moving average (convolution with 1/window kernel, 'valid' mode).
///   - Output length equals input length.
std::vector<double> smooth_for_plot(const std::vector<double>& values, int window);

/// Compute indices selecting up to max_points evenly spaced across [0, size-1].
///
/// Matches numpy linspace(0, size-1, count, dtype=int) (truncates toward zero):
///   - size <= 0 or max_points <= 0: return {}.
///   - size <= max_points: return {0, 1, ..., size-1}.
///   - else: count = max(1, max_points); idx[i] = (int)(i*(size-1)/(count-1));
///     return sorted unique set.
std::vector<int> endpoint_indices(int size, int max_points);

/// Compute bin edges for extrema decimation.
///
/// Matches numpy linspace(0, size, bin_count+1, dtype=int):
///   - bin_count = max(1, (max_points - 2) / 2) (integer division).
///   - edges[i] = (int)(i * size / bin_count) for i in 0..bin_count.
///   - Returns bin_count+1 edge values.
std::vector<int> extrema_bin_edges(int size, int max_points);

/// Decimate (x, y) to at most max_points by uniform index selection.
///
/// Writes result into ox, oy. If x.size() <= max_points, copies verbatim.
/// Otherwise uses endpoint_indices to select indices.
void decimate_for_plot(const std::vector<double>& x,
                       const std::vector<double>& y,
                       int max_points,
                       std::vector<double>& ox,
                       std::vector<double>& oy);

/// Decimate (x, y) preserving endpoints and per-bin min/max extrema.
///
/// Matches plots.py decimate_extrema_for_plot:
///   - size <= max_points: copy verbatim.
///   - max_points < 4: delegate to decimate_for_plot.
///   - else: always keep indices {0, size-1}; for each bin [start, stop):
///       if stop > start: add start+argmin and start+argmax of y[start:stop].
///     Sort and unique-deduplicate keep; output x[keep], y[keep].
void decimate_extrema_for_plot(const std::vector<double>& x,
                               const std::vector<double>& y,
                               int max_points,
                               std::vector<double>& ox,
                               std::vector<double>& oy);

} // namespace ads1292::view
