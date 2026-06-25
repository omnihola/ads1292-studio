#pragma once

#include "ads1292/gui/IWaveformPlot.h"

// Forward-declare QCustomPlot so consumers never need qcustomplot.h.
class QCustomPlot;

namespace ads1292::gui {

/// IWaveformPlot backend backed by QCustomPlot.
/// This header intentionally does NOT include qcustomplot.h — only the .cpp
/// file includes it, keeping the GPL dependency isolated.
class QCustomPlotWaveform : public IWaveformPlot {
public:
    /// Constructs the plot and pre-creates two graphs (0 = ECG, 1 = respiration).
    explicit QCustomPlotWaveform();
    ~QCustomPlotWaveform() override;

    // IWaveformPlot interface
    void setData(int graphIndex,
                 const std::vector<double>& x,
                 const std::vector<double>& y) override;
    void setYRange(int graphIndex, double lo, double hi) override;
    void setAutoscale(bool on) override;
    void replotNow() override;
    QWidget* widget() override;

private:
    QCustomPlot* m_plot{nullptr};
    bool m_autoscale{false};
};

} // namespace ads1292::gui
