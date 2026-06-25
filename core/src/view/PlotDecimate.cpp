// core/src/view/PlotDecimate.cpp
// Plot helpers: smoothing, index selection, and extrema decimation.
// Pure C++17, no Qt, no OS.

#include "ads1292/view/PlotDecimate.h"

#include <algorithm>
#include <cassert>
#include <cstdlib>

namespace ads1292::view {

// ── smooth_for_plot ──────────────────────────────────────────────────────────

std::vector<double> smooth_for_plot(const std::vector<double>& values, int window)
{
    const int size = static_cast<int>(values.size());

    if (window <= 1 || size < window) {
        return values;
    }

    // Force odd window length.
    if (window % 2 == 0) {
        ++window;
    }

    const int pad = window / 2;

    // Build edge-padded array: [first]*pad + values + [last]*pad
    std::vector<double> padded;
    padded.reserve(size + 2 * pad);
    for (int i = 0; i < pad; ++i) {
        padded.push_back(values.front());
    }
    for (const double v : values) {
        padded.push_back(v);
    }
    for (int i = 0; i < pad; ++i) {
        padded.push_back(values.back());
    }

    // Moving average with 'valid' mode convolution (kernel = 1/window).
    // Output length = padded.size() - window + 1 = (size + 2*pad) - window + 1 = size.
    const double inv_w = 1.0 / static_cast<double>(window);
    const int out_size = static_cast<int>(padded.size()) - window + 1;

    std::vector<double> result(out_size);
    double running = 0.0;
    for (int i = 0; i < window; ++i) {
        running += padded[i];
    }
    result[0] = running * inv_w;
    for (int i = 1; i < out_size; ++i) {
        running += padded[i + window - 1] - padded[i - 1];
        result[i] = running * inv_w;
    }

    return result;
}

// ── endpoint_indices ─────────────────────────────────────────────────────────

std::vector<int> endpoint_indices(int size, int max_points)
{
    if (size <= 0 || max_points <= 0) {
        return {};
    }
    if (size <= max_points) {
        std::vector<int> idx(size);
        for (int i = 0; i < size; ++i) {
            idx[i] = i;
        }
        return idx;
    }

    const int count = (max_points > 1) ? max_points : 1;

    // Special case: numpy linspace(0, size-1, 1, dtype=int) returns [0] with no division
    if (count == 1) {
        return std::vector<int>{0};
    }

    std::vector<int> idx(count);
    for (int i = 0; i < count; ++i) {
        // Matches numpy linspace(0, size-1, count, dtype=int): truncate toward zero.
        idx[i] = static_cast<int>(static_cast<double>(i) * (size - 1) / (count - 1));
    }

    // Sort and unique.
    std::sort(idx.begin(), idx.end());
    idx.erase(std::unique(idx.begin(), idx.end()), idx.end());
    return idx;
}

// ── extrema_bin_edges ────────────────────────────────────────────────────────

std::vector<int> extrema_bin_edges(int size, int max_points)
{
    // bin_count = max(1, (max_points - 2) / 2)  (integer division)
    int bin_count = (max_points - 2) / 2;
    if (bin_count < 1) {
        bin_count = 1;
    }

    // edges[i] = (int)(i * size / bin_count) for i in 0..bin_count
    std::vector<int> edges(bin_count + 1);
    for (int i = 0; i <= bin_count; ++i) {
        edges[i] = static_cast<int>(static_cast<double>(i) * size / bin_count);
    }
    return edges;
}

// ── decimate_for_plot ────────────────────────────────────────────────────────

void decimate_for_plot(const std::vector<double>& x,
                       const std::vector<double>& y,
                       int max_points,
                       std::vector<double>& ox,
                       std::vector<double>& oy)
{
    const int size = static_cast<int>(x.size());
    assert(size == static_cast<int>(y.size()));

    if (size <= max_points) {
        ox = x;
        oy = y;
        return;
    }

    std::vector<int> idx = endpoint_indices(size, max_points);
    ox.resize(idx.size());
    oy.resize(idx.size());
    for (int k = 0; k < static_cast<int>(idx.size()); ++k) {
        ox[k] = x[idx[k]];
        oy[k] = y[idx[k]];
    }
}

// ── decimate_extrema_for_plot ────────────────────────────────────────────────

void decimate_extrema_for_plot(const std::vector<double>& x,
                               const std::vector<double>& y,
                               int max_points,
                               std::vector<double>& ox,
                               std::vector<double>& oy)
{
    const int size = static_cast<int>(x.size());
    assert(size == static_cast<int>(y.size()));

    if (size <= max_points) {
        ox = x;
        oy = y;
        return;
    }
    if (max_points < 4) {
        decimate_for_plot(x, y, max_points, ox, oy);
        return;
    }

    std::vector<int> edges = extrema_bin_edges(size, max_points);

    // Always keep first and last index.
    std::vector<int> keep;
    keep.push_back(0);
    keep.push_back(size - 1);

    const int num_bins = static_cast<int>(edges.size()) - 1;
    for (int b = 0; b < num_bins; ++b) {
        const int start = edges[b];
        const int stop  = edges[b + 1];
        if (stop <= start) {
            continue;
        }

        // argmin: index of first minimum in y[start:stop]
        int local_min = start;
        double min_val = y[start];
        for (int i = start + 1; i < stop; ++i) {
            if (y[i] < min_val) {
                min_val = y[i];
                local_min = i;
            }
        }

        // argmax: index of first maximum in y[start:stop]
        int local_max = start;
        double max_val = y[start];
        for (int i = start + 1; i < stop; ++i) {
            if (y[i] > max_val) {
                max_val = y[i];
                local_max = i;
            }
        }

        keep.push_back(local_min);
        keep.push_back(local_max);
    }

    // Sort and unique-deduplicate.
    std::sort(keep.begin(), keep.end());
    keep.erase(std::unique(keep.begin(), keep.end()), keep.end());

    ox.resize(keep.size());
    oy.resize(keep.size());
    for (int k = 0; k < static_cast<int>(keep.size()); ++k) {
        ox[k] = x[keep[k]];
        oy[k] = y[keep[k]];
    }
}

} // namespace ads1292::view
