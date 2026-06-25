#pragma once
// gui/include/ads1292/gui/SpectrumPanel.h
// Review panel: power spectrum (FFT line) + amplitude histogram (bars).
// GPL isolation: does NOT include qcustomplot.h — uses IXYPlot abstraction only.

#include "ads1292/gui/IXYPlot.h"
#include "ads1292/dsp/Spectrum.h"

#include <QWidget>
#include <memory>

namespace ads1292::gui {

/// A QWidget that shows a power spectrum (FFT line) and an amplitude histogram
/// (bar chart), stacked vertically, for a spectrum analysis result.
class SpectrumPanel : public QWidget {
public:
    explicit SpectrumPanel(QWidget* parent = nullptr);
    ~SpectrumPanel() override = default;

    /// Update both plots from a SpectrumAnalysis.
    /// Guards against empty arrays.
    void showSpectrum(const ads1292::dsp::SpectrumAnalysis& a);

private:
    std::unique_ptr<IXYPlot> fftPlot_;
    std::unique_ptr<IXYPlot> histPlot_;
};

} // namespace ads1292::gui
