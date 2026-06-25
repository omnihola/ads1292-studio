#pragma once
// core/include/ads1292/view/ReviewRender.h
// Portable full-recording review frame builder.
// Pure C++17, no Qt, no OS. All computations in double.

#include "ads1292/dsp/ChannelSelect.h"
#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/EcgReview.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/model/StreamSample.h"

#include <string>
#include <utility>
#include <vector>

namespace ads1292::view {

/// A fully-rendered review frame for a complete recording.
/// All plot arrays use double precision. Produced by build_review_render_frame().
struct ReviewRenderFrame {
    // ── Metadata ──────────────────────────────────────────────────────────────
    std::string source;          ///< Original source string passed by the caller
    std::string mode;            ///< display_mode_label(...) + ", display-smoothed"
    int    sample_count  = 0;   ///< Total number of samples
    double duration_seconds = 0.0; ///< sample_count / sample_rate_hz

    // ── Raw status values ─────────────────────────────────────────────────────
    std::vector<int> status_values; ///< lead_off_bits() for each sample

    // ── Decimated plot arrays ─────────────────────────────────────────────────
    std::vector<double> plot_ecg_x;    ///< Decimated ECG x (seconds)
    std::vector<double> plot_ecg;      ///< Decimated ECG amplitude (smoothed)
    std::vector<double> plot_resp_x;   ///< Decimated resp x (seconds)
    std::vector<double> plot_resp;     ///< Decimated resp amplitude (smoothed)
    std::vector<double> plot_status_x; ///< Decimated status x (seconds)
    std::vector<double> plot_status;   ///< Decimated status values (double)

    // ── R-peak markers (in smoothed ECG coordinates) ──────────────────────────
    std::vector<double> peak_x; ///< peak index / sr
    std::vector<double> peak_y; ///< display_ecg[peak_index] (smoothed)

    // ── Axis limits ───────────────────────────────────────────────────────────
    double x_right = 1.0;                       ///< max(1.0, x.back())
    std::pair<double, double> ecg_ylim;         ///< robust_ylim of smoothed ECG
    std::pair<double, double> resp_ylim;        ///< robust_ylim of smoothed resp
    std::pair<double, double> status_ylim;      ///< (-0.5, max(1.0, max(status)+0.5))

    // ── Review analytics ──────────────────────────────────────────────────────
    ads1292::dsp::ChannelChoice    review_source; ///< channel choice result
    std::vector<int>               review_peaks;  ///< R-peak indices in full signal
    ads1292::dsp::HeartRateSummary review_hr;     ///< HR statistics
    ads1292::dsp::PqrstReview      pqrst;         ///< Average-beat morphology
    ads1292::dsp::QualityMetrics   metrics;       ///< Full quality summary
};

/// Build a full-recording review frame from raw StreamSamples.
///
/// Matches review_render.py build_review_render_frame() exactly.
///
/// @param samples              All stream samples for the recording
/// @param display_settings     Time window, gain, sweep speed
/// @param filter_settings      Software display filter chain settings
/// @param source               Channel source hint ("Auto", "CH1", "CH2")
/// @param sample_rate_hz       Acquisition sample rate in Hz (<=0 / non-finite → 500.0)
/// @param smoothing_window     Box-filter width for smooth_for_plot
/// @param max_points           Maximum points in decimated output traces
/// @param ecg_inverted         If true, negate the ECG signal
/// @param min_ecg_span_counts  Minimum ECG amplitude span for robust_ylim
/// @param min_resp_span_counts Minimum resp amplitude span for robust_ylim
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
    double min_resp_span_counts);

} // namespace ads1292::view
