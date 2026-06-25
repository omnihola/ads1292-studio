#pragma once

#include <memory>
#include <QWidget>

#include "ads1292/gui/IWaveformPlot.h"
#include "ads1292/gui/QCustomPlotWaveform.h"
#include "ads1292/view/RollingTrace.h"
#include "ads1292/model/StreamSample.h"

namespace ads1292::gui {

/// Two stacked waveform plots: ECG (CH2, top) and respiration (CH1, bottom).
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

    /// Append CH2 → ECG trace, CH1 → respiration trace.
    void pushStreamSample(const ads1292::StreamSample& s);

    /// Pull current trace data into both plots and repaint.
    void refresh();

    /// Resize the rolling window for both traces.
    void setWindowSeconds(double seconds);

    /// Enable / disable autoscale on both plots.
    void setAutoscale(bool on);

    /// Clear both traces and refresh empty.
    void clear();

private:
    std::unique_ptr<QCustomPlotWaveform> m_ecgPlot;
    std::unique_ptr<QCustomPlotWaveform> m_respPlot;

    ads1292::view::RollingTrace m_ecgTrace;
    ads1292::view::RollingTrace m_respTrace;
};

} // namespace ads1292::gui
