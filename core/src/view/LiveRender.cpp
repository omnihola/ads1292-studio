// core/src/view/LiveRender.cpp
// Portable live-view frame builder: filter → smooth → gated R-peak detection → HR → SNR → decimate.
// Faithful port of live_render.py build_live_render_frame().
// Pure C++17, no Qt, no OS. All computations in double.

#include "ads1292/view/LiveRender.h"
#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/EcgReview.h"
#include "ads1292/dsp/Quality.h"
#include "ads1292/view/PlotDecimate.h"

#include <algorithm>
#include <cmath>
#include <vector>

namespace ads1292::view {

namespace {

// ─── tail helper ─────────────────────────────────────────────────────────────
// Returns the last `n` elements of `v`. Assumes n <= v.size().
template <typename T>
std::vector<T> tail(const std::vector<T>& v, std::size_t n) {
    if (n == 0 || v.empty()) return {};
    std::size_t start = (v.size() >= n) ? (v.size() - n) : 0;
    return std::vector<T>(v.begin() + static_cast<std::ptrdiff_t>(start), v.end());
}

// ─── display_signal_values ───────────────────────────────────────────────────
// Applies display filter chain then gain / polarity inversion.
// Matches live_render.py display_signal_values():
//   display = apply_software_filters(raw, sr, settings)
//   scale   = invert ? -gain : gain
//   return scale == 1.0 ? display : display * scale
std::vector<double> display_signal_values(
    const std::vector<double>& raw,
    double sample_rate_hz,
    const ads1292::dsp::SoftwareFilterSettings& settings,
    bool invert,
    double gain)
{
    std::vector<double> disp = ads1292::dsp::apply_software_filters(raw, sample_rate_hz, settings);
    const double scale = invert ? -gain : gain;
    if (scale == 1.0) {
        return disp;
    }
    for (double& v : disp) {
        v *= scale;
    }
    return disp;
}

// ─── ptp (peak-to-peak) ──────────────────────────────────────────────────────
// Returns max - min. Returns 0.0 for empty vectors.
double ptp(const std::vector<double>& v) {
    if (v.empty()) return 0.0;
    double lo = v[0], hi = v[0];
    for (double x : v) {
        if (x < lo) lo = x;
        if (x > hi) hi = x;
    }
    return hi - lo;
}

} // anonymous namespace

// ─── build_live_render_frame ─────────────────────────────────────────────────
LiveRenderFrame build_live_render_frame(
    const std::vector<int>&    indices,
    const std::vector<double>& ch1,
    const std::vector<double>& ch2,
    const std::vector<int>&    status,
    const ads1292::dsp::EcgDisplaySettings&    display_settings,
    const ads1292::dsp::SoftwareFilterSettings& filter_settings,
    const std::string& source,
    double sample_rate_hz,
    int    smoothing_window,
    int    max_render_points,
    bool   ecg_inverted)
{
    LiveRenderFrame frame;
    frame.source = source;

    // Guard: invalid sample rate
    if (!std::isfinite(sample_rate_hz) || sample_rate_hz <= 0.0) {
        return frame; // valid = false
    }

    // Visible count: min of all buffer sizes and the time-window capacity
    const std::size_t window_samples =
        static_cast<std::size_t>(
            static_cast<int>(display_settings.time_window_seconds * sample_rate_hz) + 2);

    const std::size_t visible_count = std::min({
        indices.size(),
        ch1.size(),
        ch2.size(),
        status.size(),
        window_samples
    });

    if (visible_count == 0) {
        return frame; // valid = false
    }

    // ── Extract tails ─────────────────────────────────────────────────────────
    const std::vector<int>    indices_tail = tail(indices, visible_count);
    const std::vector<double> ecg_raw      = tail(ch2,     visible_count);
    const std::vector<double> resp_raw     = tail(ch1,     visible_count);
    const std::vector<int>    status_tail  = tail(status,  visible_count);

    // ── Visible x axis ────────────────────────────────────────────────────────
    frame.visible_x.resize(visible_count);
    for (std::size_t i = 0; i < visible_count; ++i) {
        frame.visible_x[i] = static_cast<double>(indices_tail[i]) / sample_rate_hz;
    }

    // ── Time window left / right ──────────────────────────────────────────────
    const double x_back = frame.visible_x.back();
    frame.left  = std::max(0.0, x_back - display_settings.time_window_seconds);
    frame.right = std::max(display_settings.time_window_seconds, x_back);

    // ── Display filter + gain/invert ──────────────────────────────────────────
    frame.visible_ecg  = display_signal_values(
        ecg_raw, sample_rate_hz, filter_settings, ecg_inverted, display_settings.gain);

    const std::vector<double> visible_resp = display_signal_values(
        resp_raw, sample_rate_hz, filter_settings, /*invert=*/false, /*gain=*/1.0);

    // ── Smoothing ─────────────────────────────────────────────────────────────
    frame.visible_ecg_plot  = smooth_for_plot(frame.visible_ecg, smoothing_window);
    frame.visible_resp_plot = smooth_for_plot(visible_resp,      smoothing_window);

    // ── Status as double ──────────────────────────────────────────────────────
    frame.visible_status.resize(visible_count);
    for (std::size_t i = 0; i < visible_count; ++i) {
        frame.visible_status[i] = static_cast<double>(status_tail[i]);
    }

    // ── Contact gate ──────────────────────────────────────────────────────────
    // contact_ok = !status.empty() && fraction(status_tail == 0) >= 0.95
    bool contact_ok = false;
    if (!status_tail.empty()) {
        std::size_t zero_count = 0;
        for (int s : status_tail) {
            if (s == 0) ++zero_count;
        }
        const double fraction = static_cast<double>(zero_count) /
                                static_cast<double>(status_tail.size());
        contact_ok = (fraction >= 0.95);
    }

    // ── Signal presence gate ──────────────────────────────────────────────────
    const bool ecg_has_signal = ptp(frame.visible_ecg) > 1e-9;

    // ── R-peak detection ──────────────────────────────────────────────────────
    // Require: contact_ok && ecg_has_signal && visible_count >= 1 second of samples
    const bool enough_duration =
        (static_cast<int>(visible_count) >= static_cast<int>(1.0 * sample_rate_hz));

    if (contact_ok && ecg_has_signal && enough_duration) {
        frame.peaks = ads1292::dsp::detect_r_peaks(
            frame.visible_ecg,
            sample_rate_hz,
            /*prefiltered=*/filter_settings.bandpass_enabled);
    }
    // else peaks stays empty

    // ── Peak markers ─────────────────────────────────────────────────────────
    frame.peaks_x.reserve(frame.peaks.size());
    frame.peaks_y.reserve(frame.peaks.size());
    for (int pk : frame.peaks) {
        frame.peaks_x.push_back(frame.visible_x[static_cast<std::size_t>(pk)]);
        frame.peaks_y.push_back(frame.visible_ecg_plot[static_cast<std::size_t>(pk)]);
    }

    // ── Decimation ────────────────────────────────────────────────────────────
    decimate_extrema_for_plot(
        frame.visible_x, frame.visible_ecg_plot, max_render_points,
        frame.plot_ecg_x, frame.plot_ecg);

    decimate_extrema_for_plot(
        frame.visible_x, frame.visible_resp_plot, max_render_points,
        frame.plot_resp_x, frame.plot_resp);

    decimate_for_plot(
        frame.visible_x, frame.visible_status, max_render_points,
        frame.plot_status_x, frame.plot_status);

    // ── Analytics ─────────────────────────────────────────────────────────────
    frame.heart_rate = ads1292::dsp::heart_rate_summary(frame.peaks, sample_rate_hz);
    frame.snr        = ads1292::dsp::estimate_realtime_snr(frame.visible_ecg, sample_rate_hz);

    frame.valid = true;
    return frame;
}

} // namespace ads1292::view
