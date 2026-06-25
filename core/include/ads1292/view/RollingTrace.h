#pragma once

#include <cstddef>
#include <deque>
#include <vector>

namespace ads1292::view {

/// Rolling waveform buffer with peak-preserving decimation.
///
/// Retains the most recent `window_seconds * sample_rate_hz` samples.
/// y() / x() return at most kMaxPoints values; when the window is wider
/// they are peak-decimated so spikes survive (each bucket emits min then max).
class RollingTrace {
public:
    static constexpr std::size_t kMaxPoints = 2000;

    RollingTrace(double sample_rate_hz, double window_seconds);

    /// Push one sample.  Drops oldest samples once the window is full.
    void append(double value);

    /// Resize the visible window (seconds).  Trims excess samples immediately.
    void set_window_seconds(double seconds);

    /// Remove all samples.
    void clear();

    /// Number of samples currently stored.
    std::size_t size() const;

    /// Value array — decimated to kMaxPoints when window is wide.
    std::vector<double> y() const;

    /// Time array (relative seconds, front = 0.0) — same length as y().
    std::vector<double> x() const;

private:
    double sample_rate_hz_;
    double window_seconds_;
    std::deque<double> samples_;

    /// Maximum number of samples that fit in the current window.
    std::size_t capacity() const;

    /// Trim oldest samples so size() <= capacity().
    void trim();

    /// Build the decimated (y, x) pair when size() > kMaxPoints.
    std::pair<std::vector<double>, std::vector<double>> decimate() const;
};

}  // namespace ads1292::view
