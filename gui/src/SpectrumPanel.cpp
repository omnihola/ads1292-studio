// gui/src/SpectrumPanel.cpp
// Spectrum review panel: FFT line + amplitude histogram bars.
// GPL isolation: includes only IXYPlot (not qcustomplot.h).

#include "ads1292/gui/SpectrumPanel.h"
#include "ads1292/gui/QCustomPlotXY.h"

#include <QVBoxLayout>
#include <cstddef>

namespace ads1292::gui {

SpectrumPanel::SpectrumPanel(QWidget* parent)
    : QWidget(parent)
    , fftPlot_(std::make_unique<QCustomPlotXY>())
    , histPlot_(std::make_unique<QCustomPlotXY>())
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->addWidget(fftPlot_->widget());
    layout->addWidget(histPlot_->widget());
    setLayout(layout);
}

void SpectrumPanel::showSpectrum(const ads1292::dsp::SpectrumAnalysis& a)
{
    // ── FFT line ──────────────────────────────────────────────────────────────
    if (!a.ecg_frequency_hz.empty() && !a.ecg_power.empty()) {
        fftPlot_->setLine(a.ecg_frequency_hz, a.ecg_power);
        fftPlot_->setTitle("Power spectrum · " + a.ecg_label);
        fftPlot_->setAutoscale(true);
        fftPlot_->replotNow();
    }

    // ── Histogram bars ────────────────────────────────────────────────────────
    const std::size_t nBins = a.histogram_counts.size();
    const std::size_t nEdges = a.histogram_bin_edges.size();

    if (nBins > 0 && nEdges == nBins + 1) {
        const double width = (nEdges > 1)
            ? (a.histogram_bin_edges[1] - a.histogram_bin_edges[0])
            : 1.0;

        std::vector<double> centers(nBins);
        std::vector<double> heights(nBins);
        for (std::size_t i = 0; i < nBins; ++i) {
            centers[i] = (a.histogram_bin_edges[i] + a.histogram_bin_edges[i + 1]) / 2.0;
            heights[i] = static_cast<double>(a.histogram_counts[i]);
        }

        histPlot_->setBars(centers, heights, width);
        histPlot_->setTitle("Amplitude histogram");
        histPlot_->setAutoscale(true);
        histPlot_->replotNow();
    }
}

} // namespace ads1292::gui
