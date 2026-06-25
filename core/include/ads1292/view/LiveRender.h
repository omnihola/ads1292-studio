#pragma once
// core/include/ads1292/view/LiveRender.h
// Portable live-view frame builder: filter → smooth → gated R-peak detection → HR → SNR → decimate.
// Pure C++17, no Qt, no OS. All computations in double.

#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/EcgReview.h"
#include "ads1292/dsp/Quality.h"

#include <string>
#include <vector>

namespace ads1292::view {

/// A fully-rendered live ECG frame, ready for the GUI to paint.
/// All fields use double precision. Produced by build_live_render_frame().
struct LiveRenderFrame {
    std::string source;   ///< Channel label (e.g. "CH2")
    double left  = 0.0;   ///< Left edge of the visible time window (seconds)
    double right = 0.0;   ///< Right edge of the visible time window (seconds)

    // Full-resolution visible-window arrays (length == visible_count)
    std::vector<double> visible_x;          ///< Sample timestamps (seconds)
    std::vector<double> visible_ecg;        ///< ECG after display filters + gain/invert
    std::vector<double> visible_ecg_plot;   ///< visible_ecg after smoothing
    std::vector<double> visible_resp_plot;  ///< resp after display filters + smoothing
    std::vector<double> visible_status;     ///< Status bytes as double

    // R-peak detection results
    std::vector<int>    peaks;    ///< Indices into visible_* arrays
    std::vector<double> peaks_x;  ///< visible_x[peaks]
    std::vector<double> peaks_y;  ///< visible_ecg_plot[peaks]

    // Decimated traces for rendering (length <= max_render_points)
    std::vector<double> plot_ecg_x;
    std::vector<double> plot_ecg;
    std::vector<double> plot_resp_x;
    std::vector<double> plot_resp;
    std::vector<double> plot_status_x;
    std::vector<double> plot_status;

    // Analytics
    ads1292::dsp::HeartRateSummary  heart_rate;  ///< HR statistics from R-peaks
    ads1292::dsp::SignalNoiseEstimate snr;        ///< Real-time SNR estimate

    bool valid = false;  ///< True iff the frame was successfully built
};

/// Build a live render frame from the current rolling window buffers.
///
/// Implements live_render.py build_live_render_frame() exactly.
///
/// @param indices           Rolling sample indices (monotonically increasing)
/// @param ch1               Respiration channel samples
/// @param ch2               ECG channel samples
/// @param status            Status bytes (0 = leads on, non-zero = lead-off)
/// @param display_settings  Time window, gain, sweep speed
/// @param filter_settings   Software display filter chain settings
/// @param source            Channel label for the frame (copied verbatim)
/// @param sample_rate_hz    Acquisition sample rate in Hz
/// @param smoothing_window  Box-filter half-width for smooth_for_plot
/// @param max_render_points Maximum number of points in the decimated output traces
/// @param ecg_inverted      If true, negate the ECG signal (polarity inversion)
///
/// Returns a frame with valid=false if:
///   - sample_rate_hz is not finite or <= 0
///   - the visible sample count is 0
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
    bool   ecg_inverted);

} // namespace ads1292::view
