#pragma once

#include <string>
#include <vector>

class QWidget;

namespace ads1292::gui {

/// Abstract interface for a generic XY line / bar plot.
/// Decouples consumers (review panels, MainWindow) from the QCustomPlot backend.
/// No qcustomplot.h is included here — only QCustomPlotXY.cpp sees it.
class IXYPlot {
public:
    virtual ~IXYPlot() = default;

    /// Set the line data (XY scatter / line graph).
    virtual void setLine(const std::vector<double>& x,
                         const std::vector<double>& y) = 0;

    /// Set bar data: \p centers = bar centre x positions,
    /// \p heights = bar heights, \p width = uniform bar width.
    virtual void setBars(const std::vector<double>& centers,
                         const std::vector<double>& heights,
                         double width) = 0;

    /// Set a human-readable title displayed at the top of the plot.
    virtual void setTitle(const std::string& title) = 0;

    /// Fix the Y-axis range to [\p lo, \p hi] (disables autoscale for Y).
    virtual void setYRange(double lo, double hi) = 0;

    /// When \p on is true, axes rescale to fit data on every replot.
    virtual void setAutoscale(bool on) = 0;

    /// Trigger an immediate repaint of the plot widget.
    virtual void replotNow() = 0;

    /// Return the underlying QWidget for embedding in a layout.
    virtual QWidget* widget() = 0;

    /// Render the current plot contents to a PNG file at \p path.
    /// \p width and \p height specify the output pixel dimensions (0 = use widget size).
    /// Returns true on success.  Implemented only in the QCustomPlot backend .cpp;
    /// no qcustomplot.h or QCP types are referenced here.
    virtual bool savePng(const std::string& path,
                         int width = 1000,
                         int height = 360) = 0;
};

} // namespace ads1292::gui
