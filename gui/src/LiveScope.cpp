// gui/src/LiveScope.cpp

#include "ads1292/gui/LiveScope.h"

#include <QVBoxLayout>

namespace ads1292::gui {

static constexpr double kDefaultSampleRateHz  = 500.0;
static constexpr double kDefaultWindowSeconds = 8.0;

LiveScope::LiveScope(QWidget* parent)
    : QWidget(parent)
    , m_ecgPlot(std::make_unique<QCustomPlotWaveform>())
    , m_respPlot(std::make_unique<QCustomPlotWaveform>())
    , m_ecgTrace(kDefaultSampleRateHz, kDefaultWindowSeconds)
    , m_respTrace(kDefaultSampleRateHz, kDefaultWindowSeconds)
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->setSpacing(0);

    // addWidget reparents the inner QCustomPlot to this widget's hierarchy.
    // QCustomPlotWaveform's parent-aware destructor will not double-delete.
    layout->addWidget(m_ecgPlot->widget());
    layout->addWidget(m_respPlot->widget());
}

void LiveScope::pushStreamSample(const ads1292::StreamSample& s) {
    m_ecgTrace.append(static_cast<double>(s.ch2));
    m_respTrace.append(static_cast<double>(s.ch1));
}

void LiveScope::refresh() {
    const auto ecgData  = m_ecgTrace.sampled();
    const auto respData = m_respTrace.sampled();

    m_ecgPlot->setData(0, ecgData.x, ecgData.y);
    m_ecgPlot->replotNow();

    m_respPlot->setData(0, respData.x, respData.y);
    m_respPlot->replotNow();
}

void LiveScope::setWindowSeconds(double seconds) {
    m_ecgTrace.set_window_seconds(seconds);
    m_respTrace.set_window_seconds(seconds);
}

void LiveScope::setAutoscale(bool on) {
    m_ecgPlot->setAutoscale(on);
    m_respPlot->setAutoscale(on);
}

void LiveScope::clear() {
    m_ecgTrace.clear();
    m_respTrace.clear();
    refresh();
}

} // namespace ads1292::gui
