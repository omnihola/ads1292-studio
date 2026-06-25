// gui/src/PqrstPanel.cpp
// PQRST average-beat review panel.
// GPL isolation: includes only IXYPlot (not qcustomplot.h).

#include "ads1292/gui/PqrstPanel.h"
#include "ads1292/gui/QCustomPlotXY.h"

#include <QVBoxLayout>

namespace ads1292::gui {

PqrstPanel::PqrstPanel(QWidget* parent)
    : QWidget(parent)
    , plot_(std::make_unique<QCustomPlotXY>())
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->addWidget(plot_->widget());
    setLayout(layout);
}

void PqrstPanel::showFrame(const ads1292::view::ReviewRenderFrame& f)
{
    if (f.pqrst.average_beat.empty()) {
        // Clear by setting empty data — no crash, no-op visually
        plot_->setLine({}, {});
        plot_->replotNow();
        return;
    }

    plot_->setLine(f.pqrst.time_ms, f.pqrst.average_beat);
    plot_->setTitle("PQRST average beat");
    plot_->setAutoscale(true);
    plot_->replotNow();
}

} // namespace ads1292::gui
