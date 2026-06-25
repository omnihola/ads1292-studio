// core/src/view/ReviewRender.cpp
// Portable full-recording review frame builder.
// Faithful port of review_render.py build_review_render_frame().
// Pure C++17, no Qt, no OS. All computations in double.

#include "ads1292/view/ReviewRender.h"
#include "ads1292/view/PlotDecimate.h"
#include "ads1292/view/PlotStats.h"
#include "ads1292/dsp/ChannelSelect.h"
#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/EcgReview.h"
#include "ads1292/dsp/QualityMetrics.h"

#include <algorithm>
#include <cmath>

namespace ads1292::view {

namespace {

// ─── display_signal_values ───────────────────────────────────────────────────
// Matches review_render.py / live_render.py display_signal_values():
//   disp  = apply_software_filters(raw, sr, settings)
//   scale = invert ? -gain : gain
//   return (scale == 1.0) ? disp : disp * scale
static std::vector<double> display_signal_values(
    const std::vector<double>&                     raw,
    double                                          sample_rate_hz,
    const ads1292::dsp::SoftwareFilterSettings&    settings,
    bool                                            invert,
    double                                          gain)
{
    std::vector<double> disp =
        ads1292::dsp::apply_software_filters(raw, sample_rate_hz, settings);
    const double scale = invert ? -gain : gain;
    if (scale != 1.0) {
        for (double& v : disp) v *= scale;
    }
    return disp;
}

} // anonymous namespace

// ─── build_review_render_frame ───────────────────────────────────────────────
ReviewRenderFrame build_review_render_frame(
    const std::vector<ads1292::StreamSample>&      samples,
    const ads1292::dsp::EcgDisplaySettings&        display_settings,
    const ads1292::dsp::SoftwareFilterSettings&    filter_settings,
    const std::string&                             source,
    double sample_rate_hz,
    int    smoothing_window,
    int    max_points,
    bool   ecg_inverted,
    double min_ecg_span_counts,
    double min_resp_span_counts)
{
    ReviewRenderFrame frame;
    frame.source = source;

    // ── Guard: bad sample rate → use 500 Hz ──────────────────────────────────
    if (!std::isfinite(sample_rate_hz) || sample_rate_hz <= 0.0) {
        sample_rate_hz = 500.0;
    }

    const std::size_t n = samples.size();
    frame.sample_count  = static_cast<int>(n);
    frame.duration_seconds = static_cast<double>(n) / sample_rate_hz; // count/sr

    // ── Extract raw channel arrays ────────────────────────────────────────────
    std::vector<double> full_ch1(n), full_ch2(n);
    frame.status_values.resize(n);
    for (std::size_t i = 0; i < n; ++i) {
        full_ch1[i]           = static_cast<double>(samples[i].ch1);
        full_ch2[i]           = static_cast<double>(samples[i].ch2);
        frame.status_values[i] = samples[i].lead_off_bits();
    }

    // ── Display filter + gain/invert ─────────────────────────────────────────
    // ECG: ch2, user gain, ECG invert flag
    // Resp: ch1, UNITY gain (1.0), no invert — matches P5d fix
    std::vector<double> ecg  = display_signal_values(
        full_ch2, sample_rate_hz, filter_settings, ecg_inverted, display_settings.gain);
    std::vector<double> resp = display_signal_values(
        full_ch1, sample_rate_hz, filter_settings, /*invert=*/false, /*gain=*/1.0);

    // ── Channel review + quality analysis ────────────────────────────────────
    ads1292::dsp::ReviewResult review =
        ads1292::dsp::review_channels(full_ch1, full_ch2, sample_rate_hz, source);

    frame.review_source = review.source;
    frame.review_peaks  = review.peaks;
    frame.review_hr     = review.heart_rate;

    // ── PQRST on the selected (raw) channel ──────────────────────────────────
    const std::vector<double>& pqrst_raw =
        (review.source.channel == "CH2") ? full_ch2 : full_ch1;
    frame.pqrst = ads1292::dsp::pqrst_review(pqrst_raw, review.peaks, sample_rate_hz);

    // ── Quality metrics ───────────────────────────────────────────────────────
    frame.metrics = ads1292::dsp::compute_quality_metrics(samples, sample_rate_hz, source);

    // ── Build x-axis (i/sr) ──────────────────────────────────────────────────
    std::vector<double> x(n);
    for (std::size_t i = 0; i < n; ++i) {
        x[i] = static_cast<double>(i) / sample_rate_hz;
    }

    // ── Smooth both signals ───────────────────────────────────────────────────
    std::vector<double> display_ecg  = smooth_for_plot(ecg,  smoothing_window);
    std::vector<double> display_resp = smooth_for_plot(resp, smoothing_window);

    // ── Decimate ─────────────────────────────────────────────────────────────
    decimate_extrema_for_plot(x, display_ecg,  max_points,
                              frame.plot_ecg_x,    frame.plot_ecg);
    decimate_extrema_for_plot(x, display_resp, max_points,
                              frame.plot_resp_x,   frame.plot_resp);

    // Status as double for decimate_for_plot
    std::vector<double> status_d(n);
    for (std::size_t i = 0; i < n; ++i) {
        status_d[i] = static_cast<double>(frame.status_values[i]);
    }
    decimate_for_plot(x, status_d, max_points,
                      frame.plot_status_x, frame.plot_status);

    // ── R-peak markers (smoothed ECG) ─────────────────────────────────────────
    frame.peak_x.reserve(review.peaks.size());
    frame.peak_y.reserve(review.peaks.size());
    for (int pk : review.peaks) {
        const std::size_t idx = static_cast<std::size_t>(pk);
        if (idx < display_ecg.size()) {
            frame.peak_x.push_back(static_cast<double>(pk) / sample_rate_hz);
            frame.peak_y.push_back(display_ecg[idx]);
        }
    }

    // ── x_right ──────────────────────────────────────────────────────────────
    frame.x_right = std::max(1.0, x.empty() ? 1.0 : x.back());

    // ── Y-axis limits ─────────────────────────────────────────────────────────
    frame.ecg_ylim  = robust_ylim(display_ecg,  min_ecg_span_counts * display_settings.gain);
    frame.resp_ylim = robust_ylim(display_resp, min_resp_span_counts);

    // Status ylim: (-0.5, max(1.0, max(status)+0.5))
    double status_top = 1.0;
    if (!status_d.empty()) {
        const double sm = *std::max_element(status_d.begin(), status_d.end());
        status_top = std::max(1.0, sm + 0.5);
    }
    frame.status_ylim = {-0.5, status_top};

    // ── Mode label ───────────────────────────────────────────────────────────
    frame.mode = ads1292::dsp::display_mode_label(display_settings, filter_settings)
                 + ", display-smoothed";

    return frame;
}

} // namespace ads1292::view
