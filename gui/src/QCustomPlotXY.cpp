// QCustomPlotXY.cpp
// *** This is the ONLY source file that includes qcustomplot.h (alongside QCustomPlotWaveform.cpp) ***
// All other GUI files access XY/bar plot functionality through IXYPlot.

#include "ads1292/gui/QCustomPlotXY.h"
#include "qcustomplot.h"

#include <QString>

namespace ads1292::gui {

QCustomPlotXY::QCustomPlotXY()
    : m_plot(new QCustomPlot())
{
    // No parent — will be reparented when added to a layout.
    m_plot->setInteractions(QCP::iRangeDrag | QCP::iRangeZoom);
}

QCustomPlotXY::~QCustomPlotXY()
{
    // If widget() was added to a layout, Qt reparented m_plot and owns it now —
    // deleting here would double-free. Only delete while it is still parentless.
    if (m_plot && m_plot->parent() == nullptr) {
        delete m_plot;
    }
}

void QCustomPlotXY::setLine(const std::vector<double>& x,
                             const std::vector<double>& y)
{
    // Lazily create the line graph on first call (index 0).
    if (m_lineGraphIdx < 0) {
        m_plot->addGraph();
        m_lineGraphIdx = m_plot->graphCount() - 1;
    }

    QVector<double> qx(x.begin(), x.end());
    QVector<double> qy(y.begin(), y.end());
    m_plot->graph(m_lineGraphIdx)->setData(qx, qy);
}

void QCustomPlotXY::setBars(const std::vector<double>& centers,
                             const std::vector<double>& heights,
                             double width)
{
    // Lazily create a QCPBars object on first call.
    // We store it in the plot's plottable list; retrieve by cast when needed.
    if (!m_barsCreated) {
        QCPBars* bars = new QCPBars(m_plot->xAxis, m_plot->yAxis);
        bars->setWidth(width);
        m_barsCreated = true;
    }

    // Retrieve the QCPBars object (always the first QCPBars plottable).
    QCPBars* bars = nullptr;
    for (int i = 0; i < m_plot->plottableCount(); ++i) {
        bars = qobject_cast<QCPBars*>(m_plot->plottable(i));
        if (bars) break;
    }
    if (!bars) return;

    bars->setWidth(width);

    QVector<double> qc(centers.begin(), centers.end());
    QVector<double> qh(heights.begin(), heights.end());
    bars->setData(qc, qh);
}

void QCustomPlotXY::setTitle(const std::string& title)
{
    // Use a QCPTextElement in a dedicated top row of the plot layout.
    // Check if we already have a title row (row 0 is usually the title when added).
    QCPTextElement* titleEl = nullptr;

    // The default plotLayout has one row (for the axes rect) at row 0.
    // We insert the title at row 0 and push the axes rect to row 1.
    // Guard: only insert once (check if row 0 element is already a QCPTextElement).
    if (m_plot->plotLayout()->elementCount() > 0) {
        titleEl = qobject_cast<QCPTextElement*>(m_plot->plotLayout()->element(0, 0));
    }

    if (!titleEl) {
        // Insert a new row at the top for the title element.
        m_plot->plotLayout()->insertRow(0);
        titleEl = new QCPTextElement(m_plot, QString::fromStdString(title),
                                     QFont("sans", 10, QFont::Bold));
        m_plot->plotLayout()->addElement(0, 0, titleEl);
    } else {
        titleEl->setText(QString::fromStdString(title));
    }
}

void QCustomPlotXY::setYRange(double lo, double hi)
{
    m_plot->yAxis->setRange(lo, hi);
}

void QCustomPlotXY::setAutoscale(bool on)
{
    m_autoscale = on;
}

void QCustomPlotXY::replotNow()
{
    if (m_autoscale) {
        m_plot->rescaleAxes();
    }
    m_plot->replot();
}

QWidget* QCustomPlotXY::widget()
{
    return m_plot;
}

bool QCustomPlotXY::savePng(const std::string& path, int width, int height)
{
    m_plot->replot();
    return m_plot->savePng(QString::fromStdString(path), width, height);
}

} // namespace ads1292::gui
