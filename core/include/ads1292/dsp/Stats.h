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

/// Numpy-faithful Hann window of length M.
/// M<=0 -> empty; M==1 -> {1.0}; else w[n] = 0.5 - 0.5*cos(2*pi*n/(M-1)).
std::vector<double> hanning(int M);

/// Numpy-faithful uniform histogram.
/// lo=min(v), hi=max(v); if lo==hi: lo-=0.5, hi+=0.5.
/// edges has bins+1 entries; counts has bins entries.
/// Reproduces numpy's decrement/increment float-correction.
void histogram(const std::vector<double>& v, int bins,
               std::vector<long>& counts, std::vector<double>& edges);

} // namespace ads1292::dsp
