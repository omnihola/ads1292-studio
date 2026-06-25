// core/src/dsp/Peaks.cpp
// Faithful port of scipy.signal.find_peaks:
//   _local_maxima_1d → _select_by_peak_distance → _peak_prominences
// Pure C++17, no Qt, no OS. All computations in double/int.

#include "ads1292/dsp/Peaks.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <vector>

namespace ads1292::dsp {

namespace {

// ─── Step 1: _local_maxima_1d ────────────────────────────────────────────────
// Scan i = 1..n-2.
// If x[i-1] < x[i]:
//   walk i_ahead forward while x[i_ahead] == x[i] and i_ahead < n-1.
//   if x[i_ahead] < x[i]: it's a peak (plateau [i, i_ahead-1]).
//   record midpoint = (i + i_ahead - 1) / 2 (integer division).
//   advance i = i_ahead.
std::vector<int> local_maxima_1d(const std::vector<double>& x) {
    const int n = static_cast<int>(x.size());
    std::vector<int> peaks;
    if (n < 3) return peaks;

    int i = 1;
    while (i < n - 1) {
        if (x[i - 1] < x[i]) {
            int i_ahead = i + 1;
            while (i_ahead < n - 1 && x[i_ahead] == x[i]) {
                ++i_ahead;
            }
            if (x[i_ahead] < x[i]) {
                // Plateau [i, i_ahead - 1]; midpoint by integer division
                int midpoint = (i + i_ahead - 1) / 2;
                peaks.push_back(midpoint);
            }
            i = i_ahead;
        } else {
            ++i;
        }
    }
    return peaks;
}

// ─── Step 2: _select_by_peak_distance ────────────────────────────────────────
// d = distance (already int; ceil of int is itself).
// priority = x[peaks] values.
// Build argsort of priority ASCENDING (stable), then iterate in REVERSE
// (highest priority = tallest first).
// For each kept peak j: suppress neighbours within d samples on both sides.
std::vector<int> select_by_peak_distance(const std::vector<int>& peaks,
                                          const std::vector<double>& x,
                                          int d) {
    const int m = static_cast<int>(peaks.size());
    if (m == 0) return {};

    // priority[j] = x[peaks[j]]
    // argsort ascending by priority, stable (to match numpy stable argsort)
    std::vector<int> order(m);
    std::iota(order.begin(), order.end(), 0);
    std::stable_sort(order.begin(), order.end(), [&](int a, int b) {
        return x[peaks[a]] < x[peaks[b]];
    });

    std::vector<bool> keep(m, true);

    // Iterate in reverse (descending priority = tallest first)
    for (int oi = m - 1; oi >= 0; --oi) {
        int j = order[oi];
        if (!keep[j]) continue;

        // Suppress left neighbours that are too close
        int k = j - 1;
        while (k >= 0 && peaks[j] - peaks[k] < d) {
            keep[k] = false;
            --k;
        }

        // Suppress right neighbours that are too close
        k = j + 1;
        while (k < m && peaks[k] - peaks[j] < d) {
            keep[k] = false;
            ++k;
        }
    }

    std::vector<int> result;
    result.reserve(m);
    for (int j = 0; j < m; ++j) {
        if (keep[j]) result.push_back(peaks[j]);
    }
    // Peaks were found in ascending order, keep[] preserves that order.
    return result;
}

// ─── Step 3: _peak_prominences ───────────────────────────────────────────────
// For each peak p:
//   left: i=p, lmin=x[p]; while i>=0 && x[i]<=x[p]: if x[i]<lmin lmin=x[i]; --i.
//   right: i=p, rmin=x[p]; while i<n && x[i]<=x[p]: if x[i]<rmin rmin=x[i]; ++i.
//   prominence = x[p] - max(lmin, rmin).
// Keep peaks with prominence >= prominence_min.
std::vector<int> filter_by_prominence(const std::vector<int>& peaks,
                                       const std::vector<double>& x,
                                       double prominence_min) {
    const int n = static_cast<int>(x.size());
    std::vector<int> result;
    result.reserve(peaks.size());

    for (int p : peaks) {
        // Left contour walk
        double lmin = x[p];
        for (int i = p; i >= 0 && x[i] <= x[p]; --i) {
            if (x[i] < lmin) lmin = x[i];
        }

        // Right contour walk
        double rmin = x[p];
        for (int i = p; i < n && x[i] <= x[p]; ++i) {
            if (x[i] < rmin) rmin = x[i];
        }

        double prom = x[p] - std::max(lmin, rmin);
        if (prom >= prominence_min) {
            result.push_back(p);
        }
    }
    return result;
}

} // anonymous namespace

// ─── Public API ──────────────────────────────────────────────────────────────
std::vector<int> find_peaks(const std::vector<double>& x,
                             int distance,
                             double prominence_min) {
    // Step 1: local maxima
    std::vector<int> peaks = local_maxima_1d(x);

    // Step 2: distance filter
    if (distance > 1 && !peaks.empty()) {
        peaks = select_by_peak_distance(peaks, x, distance);
    }

    // Step 3: prominence filter
    if (prominence_min > 0.0 && !peaks.empty()) {
        peaks = filter_by_prominence(peaks, x, prominence_min);
    }

    return peaks;
}

} // namespace ads1292::dsp
