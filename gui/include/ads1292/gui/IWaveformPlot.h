#pragma once

#include <vector>

class QWidget;

namespace ads1292::gui {

/// Abstract waveform plot interface.
/// Decouples consumers (LiveScope, MainWindow) from the QCustomPlot backend.
/// No qcustomplot.h is included here — only QCustomPlotWaveform.cpp sees it.
class IWaveformPlot {
public:
    virtual ~IWaveformPlot() = default;

    /// Replace the data for graph at \p graphIndex with \p x / \p y vectors.
    virtual void setData(int graphIndex,
                         const std::vector<double>& x,
                         const std::vector<double>& y) = 0;

    /// Fix the Y-axis range for graph at \p graphIndex to [\p lo, \p hi].
    virtual void setYRange(int graphIndex, double lo, double hi) = 0;

    /// When \p on is true, axes rescale to fit data on every replot.
    virtual void setAutoscale(bool on) = 0;

    /// Trigger an immediate repaint of the plot widget.
    virtual void replotNow() = 0;

    /// Return the underlying QWidget for embedding in a layout.
    virtual QWidget* widget() = 0;
};

} // namespace ads1292::gui
