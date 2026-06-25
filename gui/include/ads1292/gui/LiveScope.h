#pragma once

#include <deque>
#include <memory>
#include <QWidget>

#include "ads1292/gui/IWaveformPlot.h"
#include "ads1292/gui/QCustomPlotWaveform.h"
#include "ads1292/model/StreamSample.h"
#include "ads1292/dsp/Display.h"
#include "ads1292/view/LiveRender.h"

namespace ads1292::gui {

/// Two stacked waveform plots: ECG (CH2, top) and respiration (CH1, bottom).
///
/// Data model: raw rolling deques (indices, ch1, ch2, status) are trimmed to
/// (display_.time_window_seconds * sample_rate_hz_) + 2 samples.
/// refresh() builds a LiveRenderFrame via build_live_render_frame() and
/// pushes the decimated traces + R-peak markers to the two plot backends.
///
/// Ownership model:
///   - Each QCustomPlotWaveform backend is held in a std::unique_ptr<QCustomPlotWaveform>.
///   - After addWidget(backend->widget()), Qt owns the inner QCustomPlot widget
///     (parent-aware destructor in QCustomPlotWaveform will not double-delete).
///   - The unique_ptr owns the QCustomPlotWaveform wrapper object.
class LiveScope : public QWidget {
public:
    explicit LiveScope(QWidget* parent = nullptr);
    ~LiveScope() override = default;

    /// Append one StreamSample to the rolling buffers.
    /// ch2 → ECG channel, ch1 → respiration channel.
    /// Buffers are trimmed to the configured window on each push.
    void pushStreamSample(const ads1292::StreamSample& s);

    /// Replace the active software filter settings.
    void setFilterSettings(const ads1292::dsp::SoftwareFilterSettings& f);

    /// Resize the rolling window (adjusts the trim cap on the next push).
    void setWindowSeconds(double s);

    /// Build a live render frame from the current rolling buffers and repaint.
    void refresh();

    /// Enable / disable autoscale on both plots.
    void setAutoscale(bool on);

    /// Clear all rolling buffers and refresh empty.
    void clear();

    /// The last frame produced by refresh() (valid=false before first refresh).
    const ads1292::view::LiveRenderFrame& lastFrame() const;

private:
    std::unique_ptr<QCustomPlotWaveform> m_ecgPlot;
    std::unique_ptr<QCustomPlotWaveform> m_respPlot;

    // Raw rolling buffers
    std::deque<int>    indices_;
    std::deque<double> ch1_;
    std::deque<double> ch2_;
    std::deque<int>    status_;
    int next_index_ = 0;

    // Settings
    ads1292::dsp::SoftwareFilterSettings filter_;
    ads1292::dsp::EcgDisplaySettings     display_;
    double sample_rate_hz_ = 500.0;

    // Last rendered frame
    ads1292::view::LiveRenderFrame last_frame_;
};

} // namespace ads1292::gui
