#pragma once
// core/include/ads1292/dsp/Stats.h
// Numpy-faithful statistical primitives.
// Pure C++17, no Qt, no OS. All computations in double.

#include <vector>

namespace ads1292::dsp {

/// Numpy-faithful percentile (method='linear').
/// Algorithm:
///   sorted ascending copy; pos = (q/100.0)*(n-1);
///   lo = floor(pos); frac = pos - lo;
///   result = (lo+1 < n) ? xs[lo] + frac*(xs[lo+1]-xs[lo]) : xs[lo]
/// Assumes x.size() >= 1.
double percentile(const std::vector<double>& x, double q);

/// Arithmetic mean: sum / size. Returns 0.0 if empty.
double mean(const std::vector<double>& x);

} // namespace ads1292::dsp
