#pragma once
// core/include/ads1292/dsp/LiveCalibration.h
// LiveStreamCalibration model + statistics.
// Pure C++17, no Qt. All computations in double.

#include <stdexcept>
#include <string>
#include <vector>

namespace ads1292 {

/// Calibration result produced from a live-stream test-signal run.
struct LiveStreamCalibration {
    double mean_uv_per_count  = 0.0;
    double std_uv_per_count   = 0.0;
    double cv_percent         = 0.0;
    int    runs               = 0;
    double test_signal_pp_uv  = 0.0;
    std::string scale_type    = "live_processed";

    /// Return a sanitised copy: clamp negatives, fill missing test-signal
    /// fallback (2016.6666666667 µV), strip whitespace from scale_type.
    LiveStreamCalibration normalized() const;
};

} // namespace ads1292

namespace ads1292::dsp {

/// Peak-to-peak count estimate for a live-stream test-signal window.
///
/// Uses the [1, 99] percentile range (numpy-faithful linear interpolation)
/// on the finite subset of `values`.
///
/// Throws std::invalid_argument if:
///   - values.size() < 4
///   - fewer than 4 finite values
///   - the resulting peak-to-peak <= 0
double live_stream_peak_to_peak_counts(const std::vector<double>& values);

/// Summarise multiple peak-to-peak measurements into a LiveStreamCalibration.
///
/// Only positive elements of `peak_to_peak_counts` are used.
/// `scales[i] = test_signal_pp_uv / counts[i]`.
/// std is sample standard deviation (ddof=1); cv = (std/mean)*100.
///
/// Throws std::invalid_argument if no positive counts are provided.
ads1292::LiveStreamCalibration summarize_live_stream_calibration(
    const std::vector<double>& peak_to_peak_counts,
    double test_signal_pp_uv);

} // namespace ads1292::dsp
