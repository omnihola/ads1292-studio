#include "ads1292/view/RollingTrace.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace ads1292::view {

// ---------------------------------------------------------------------------
// Construction
// ---------------------------------------------------------------------------

RollingTrace::RollingTrace(double sample_rate_hz, double window_seconds)
    : sample_rate_hz_(sample_rate_hz), window_seconds_(window_seconds) {
    if (sample_rate_hz_ <= 0.0) {
        throw std::invalid_argument("sample_rate_hz must be positive");
    }
    if (window_seconds_ <= 0.0) {
        throw std::invalid_argument("window_seconds must be positive");
    }
}

// ---------------------------------------------------------------------------
// Mutation
// ---------------------------------------------------------------------------

void RollingTrace::append(double value) {
    samples_.push_back(value);
    trim();
}

void RollingTrace::set_window_seconds(double seconds) {
    if (seconds <= 0.0) {
        throw std::invalid_argument("window_seconds must be positive");
    }
    window_seconds_ = seconds;
    trim();
}

void RollingTrace::clear() {
    samples_.clear();
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

std::size_t RollingTrace::size() const {
    return samples_.size();
}

std::vector<double> RollingTrace::y() const {
    if (samples_.size() <= kMaxPoints) {
        return {samples_.begin(), samples_.end()};
    }
    return decimate().first;
}

std::vector<double> RollingTrace::x() const {
    if (samples_.size() <= kMaxPoints) {
        const double dt = 1.0 / sample_rate_hz_;
        std::vector<double> times;
        times.reserve(samples_.size());
        for (std::size_t i = 0; i < samples_.size(); ++i) {
            times.push_back(static_cast<double>(i) * dt);
        }
        return times;
    }
    return decimate().second;
}

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

std::size_t RollingTrace::capacity() const {
    const double cap = std::floor(window_seconds_ * sample_rate_hz_);
    return static_cast<std::size_t>(cap > 0.0 ? cap : 1.0);
}

void RollingTrace::trim() {
    const std::size_t cap = capacity();
    while (samples_.size() > cap) {
        samples_.pop_front();
    }
}

/// Peak-preserving decimation.
///
/// Strategy: divide the window into kMaxPoints/2 buckets.  Each bucket
/// contributes at most two output points (its min-value sample and its
/// max-value sample, in chronological order).  The result therefore has
/// at most kMaxPoints values, each paired with its source sample's
/// relative timestamp.
std::pair<std::vector<double>, std::vector<double>>
RollingTrace::decimate() const {
    const std::size_t n = samples_.size();
    const std::size_t num_buckets = kMaxPoints / 2;  // 1000 buckets → ≤2000 pts

    std::vector<double> out_y;
    std::vector<double> out_x;
    out_y.reserve(kMaxPoints);
    out_x.reserve(kMaxPoints);

    const double dt = 1.0 / sample_rate_hz_;

    for (std::size_t b = 0; b < num_buckets; ++b) {
        // Integer bucket boundaries (avoids floating-point rounding drift)
        const std::size_t begin = (b * n) / num_buckets;
        const std::size_t end   = ((b + 1) * n) / num_buckets;

        if (begin >= end) {
            continue;
        }

        // Find min and max within this bucket
        std::size_t min_idx = begin;
        std::size_t max_idx = begin;
        for (std::size_t i = begin + 1; i < end; ++i) {
            if (samples_[i] < samples_[min_idx]) min_idx = i;
            if (samples_[i] > samples_[max_idx]) max_idx = i;
        }

        // Emit in chronological order so the waveform shape is preserved
        if (min_idx <= max_idx) {
            out_y.push_back(samples_[min_idx]);
            out_x.push_back(static_cast<double>(min_idx) * dt);
            if (min_idx != max_idx) {
                out_y.push_back(samples_[max_idx]);
                out_x.push_back(static_cast<double>(max_idx) * dt);
            }
        } else {
            out_y.push_back(samples_[max_idx]);
            out_x.push_back(static_cast<double>(max_idx) * dt);
            out_y.push_back(samples_[min_idx]);
            out_x.push_back(static_cast<double>(min_idx) * dt);
        }
    }

    return {out_y, out_x};
}

}  // namespace ads1292::view
