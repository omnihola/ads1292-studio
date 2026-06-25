#pragma once

#include "ads1292/gui/IXYPlot.h"

// Forward-declare QCustomPlot so consumers never need qcustomplot.h.
class QCustomPlot;

namespace ads1292::gui {

/// IXYPlot backend backed by QCustomPlot.
/// This header intentionally does NOT include qcustomplot.h — only the .cpp
/// file includes it, keeping the GPL dependency isolated.
class QCustomPlotXY : public IXYPlot {
public:
    /// Constructs the plot widget (no parent — reparented when added to a layout).
    explicit QCustomPlotXY();
    ~QCustomPlotXY() override;

    // IXYPlot interface
    void setLine(const std::vector<double>& x,
                 const std::vector<double>& y) override;

    void setBars(const std::vector<double>& centers,
                 const std::vector<double>& heights,
                 double width) override;

    void setTitle(const std::string& title) override;
    void setYRange(double lo, double hi) override;
    void setAutoscale(bool on) override;
    void replotNow() override;
    QWidget* widget() override;

    /// Render the current plot to a PNG file at \p path (offscreen-safe).
    /// Calls replot() first so the latest data is captured.
    bool savePng(const std::string& path,
                 int width = 1000,
                 int height = 360) override;

private:
    QCustomPlot* m_plot{nullptr};
    bool  m_autoscale{false};
    // Track whether a line graph (index 0) and a bars object have been created.
    // Stored as plain int/-1 sentinel (no QCP types in the header).
    int  m_lineGraphIdx{-1};
    bool m_barsCreated{false};
};

} // namespace ads1292::gui
