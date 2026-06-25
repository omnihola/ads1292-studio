#pragma once

#include "ads1292/gui/IWaveformPlot.h"

#include <unordered_map>

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

    /// Overlay scatter markers (e.g. R-peak dots) on the graph at \p graphIndex.
    /// Each logical graphIndex gets its own dedicated scatter graph (no line,
    /// ssCircle style). Created lazily on first call; cleared when x/y are empty.
    /// Only QCustomPlotWaveform.cpp includes qcustomplot.h — GPL isolation preserved.
    void setMarkers(int graphIndex,
                    const std::vector<double>& x,
                    const std::vector<double>& y) override;

private:
    QCustomPlot* m_plot{nullptr};
    bool m_autoscale{false};

    // Maps logical graphIndex → the QCustomPlot graph() index of the marker
    // scatter graph. Stored as plain int (no QCustomPlot types in the header).
    // Created lazily in setMarkers(); -1 means not yet created.
    std::unordered_map<int, int> m_markerGraphIndex;
};

} // namespace ads1292::gui
