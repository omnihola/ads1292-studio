// gui/src/QualityInfoPanel.cpp
// Quality metrics review panel — read-only formatted text view.

#include "ads1292/gui/QualityInfoPanel.h"

#include <QPlainTextEdit>
#include <QVBoxLayout>

#include <sstream>
#include <iomanip>

namespace ads1292::gui {

QualityInfoPanel::QualityInfoPanel(QWidget* parent)
    : QWidget(parent)
    , text_(new QPlainTextEdit(this))
{
    text_->setReadOnly(true);

    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->addWidget(text_);
    setLayout(layout);
}

void QualityInfoPanel::showMetrics(const ads1292::dsp::QualityMetrics& m)
{
    std::ostringstream os;
    os << std::fixed << std::setprecision(2);

    os << "Quality label:       " << ads1292::dsp::quality_label(m) << "\n";
    os << "\n";
    os << "Source:              " << m.ecg_source << "\n";
    os << "Sample count:        " << m.sample_count << "\n";
    os << "Duration (s):        " << m.duration_seconds << "\n";
    os << "\n";
    os << "Contact OK (%):      " << m.contact_ok_percent << "\n";
    os << "Lead-off bad samples:" << m.lead_off_bad_samples << "\n";
    os << "\n";
    os << "R-peaks:             " << m.r_peaks << "\n";
    os << "HR median (bpm):     " << m.hr_median_bpm << "\n";
    os << "HR min (bpm):        " << m.hr_min_bpm << "\n";
    os << "HR max (bpm):        " << m.hr_max_bpm << "\n";
    os << "\n";
    os << "QRS clear:           " << (m.qrs_clear    ? "yes" : "no") << "\n";
    os << "P tentative:         " << (m.p_tentative  ? "yes" : "no") << "\n";
    os << "T tentative:         " << (m.t_tentative  ? "yes" : "no") << "\n";
    os << "\n";
    os << "Score CH1:           " << m.score_ch1 << "\n";
    os << "Score CH2:           " << m.score_ch2 << "\n";
    os << "\n";
    os << "Baseline drift:      " << m.baseline_drift_counts << "\n";
    os << "Noise RMS:           " << m.noise_rms_counts << "\n";
    os << "Peak-to-peak:        " << m.peak_to_peak_counts << "\n";

    text_->setPlainText(QString::fromStdString(os.str()));
}

} // namespace ads1292::gui
