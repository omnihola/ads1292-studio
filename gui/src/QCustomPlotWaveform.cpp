// QCustomPlotWaveform.cpp
// *** This is the ONLY source file that includes qcustomplot.h ***
// All other GUI files access QCustomPlot functionality through IWaveformPlot.

#include "ads1292/gui/QCustomPlotWaveform.h"
#include "qcustomplot.h"

namespace ads1292::gui {

QCustomPlotWaveform::QCustomPlotWaveform()
    : m_plot(new QCustomPlot())
{
    // Pre-create two graphs: graph(0) = ECG, graph(1) = respiration.
    m_plot->addGraph();
    m_plot->addGraph();

    m_plot->xAxis->setLabel("Sample");
    m_plot->yAxis->setLabel("Amplitude");
}

QCustomPlotWaveform::~QCustomPlotWaveform()
{
    // If widget() was added to a layout, Qt reparented m_plot and owns it now —
    // deleting here would double-free. Only delete while it is still parentless.
    if (m_plot && m_plot->parent() == nullptr) {
        delete m_plot;
    }
}

void QCustomPlotWaveform::setData(int graphIndex,
                                   const std::vector<double>& x,
                                   const std::vector<double>& y)
{
    if (graphIndex < 0 || graphIndex >= m_plot->graphCount()) {
        return;
    }
    QVector<double> qx(x.begin(), x.end());
    QVector<double> qy(y.begin(), y.end());
    m_plot->graph(graphIndex)->setData(qx, qy);
}

void QCustomPlotWaveform::setYRange(int graphIndex, double lo, double hi)
{
    // QCustomPlot shares a single y-axis by default; apply range globally.
    (void)graphIndex;
    m_plot->yAxis->setRange(lo, hi);
}

void QCustomPlotWaveform::setAutoscale(bool on)
{
    m_autoscale = on;
}

void QCustomPlotWaveform::replotNow()
{
    if (m_autoscale) {
        m_plot->rescaleAxes();
    }
    m_plot->replot();
}

QWidget* QCustomPlotWaveform::widget()
{
    return m_plot;
}

} // namespace ads1292::gui
