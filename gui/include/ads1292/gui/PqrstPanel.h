#pragma once
// gui/include/ads1292/gui/PqrstPanel.h
// Review panel: PQRST average-beat line plot.
// GPL isolation: does NOT include qcustomplot.h — uses IXYPlot abstraction only.

#include "ads1292/gui/IXYPlot.h"
#include "ads1292/view/ReviewRender.h"

#include <QWidget>
#include <memory>

namespace ads1292::gui {

/// A QWidget that shows the PQRST average-beat waveform for a review frame.
/// Owns one IXYPlot (line) laid out vertically.
class PqrstPanel : public QWidget {
public:
    explicit PqrstPanel(QWidget* parent = nullptr);
    ~PqrstPanel() override = default;

    /// Update the plot from a review render frame.
    /// If f.pqrst.average_beat is empty, clears/no-ops the plot.
    void showFrame(const ads1292::view::ReviewRenderFrame& f);

private:
    std::unique_ptr<IXYPlot> plot_;
};

} // namespace ads1292::gui
