// gui/src/SessionPanel.cpp
#include "ads1292/gui/SessionPanel.h"
#include <QCheckBox>
#include <QFormLayout>
#include <QLineEdit>
#include <QString>
#include <QTabWidget>
#include <QVBoxLayout>
#include <QWidget>

namespace ads1292::gui {

SessionPanel::SessionPanel(QWidget* parent)
    : QWidget(parent)
{
    // ── Session tab ──────────────────────────────────────────────────────────
    sessionId_ = new QLineEdit;
    subject_   = new QLineEdit;
    electrode_ = new QLineEdit;
    montage_   = new QLineEdit;
    operator_  = new QLineEdit;
    notes_     = new QLineEdit;

    // Pre-fill defaults that match SessionMetadata{}
    subject_->setText("anonymous");
    montage_->setText("RA/LA/RL torso");

    auto* sessionWidget = new QWidget;
    auto* sessionForm   = new QFormLayout(sessionWidget);
    sessionForm->setContentsMargins(8, 8, 8, 8);
    sessionForm->setSpacing(6);
    sessionForm->addRow("Session ID", sessionId_);
    sessionForm->addRow("Subject",    subject_);
    sessionForm->addRow("Electrode",  electrode_);
    sessionForm->addRow("Montage",    montage_);
    sessionForm->addRow("Operator",   operator_);
    sessionForm->addRow("Notes",      notes_);

    // ── Validation tab ───────────────────────────────────────────────────────
    minDuration_ = new QLineEdit;
    minContact_  = new QLineEdit;
    minRPeaks_   = new QLineEdit;
    minHr_       = new QLineEdit;
    maxHr_       = new QLineEdit;
    qrsCheck_    = new QCheckBox("Require QRS clear");
    maxDrift_    = new QLineEdit;
    maxNoise_    = new QLineEdit;
    maxPtp_      = new QLineEdit;

    // Pre-fill with QualityGate{} defaults
    minDuration_->setText("8");
    minContact_->setText("95");
    minRPeaks_->setText("5");
    minHr_->setText("35");
    maxHr_->setText("180");
    qrsCheck_->setChecked(true);
    // Optional caps: empty by default (→ nullopt)

    auto* validationWidget = new QWidget;
    auto* validationForm   = new QFormLayout(validationWidget);
    validationForm->setContentsMargins(8, 8, 8, 8);
    validationForm->setSpacing(6);
    validationForm->addRow("Min duration (s)",            minDuration_);
    validationForm->addRow("Min contact OK (%)",          minContact_);
    validationForm->addRow("Min R peaks",                 minRPeaks_);
    validationForm->addRow("Min HR (bpm)",                minHr_);
    validationForm->addRow("Max HR (bpm)",                maxHr_);
    validationForm->addRow("",                            qrsCheck_);
    validationForm->addRow("Max baseline drift (counts)", maxDrift_);
    validationForm->addRow("Max noise RMS (counts)",      maxNoise_);
    validationForm->addRow("Max peak-to-peak (counts)",   maxPtp_);

    // ── Protocol tab ─────────────────────────────────────────────────────────
    protName_         = new QLineEdit;
    protObjective_    = new QLineEdit;
    protInstructions_ = new QLineEdit;
    protAccept_       = new QLineEdit;

    // Pre-fill with TestProtocol{} defaults
    protName_->setText("ADS1292 validation protocol");
    protObjective_->setText("");  // explicit empty
    protInstructions_->setText("Follow the listed protocol steps.");
    protAccept_->setText("Review quality gate and artifacts before accepting the run.");

    auto* protocolWidget = new QWidget;
    auto* protocolForm   = new QFormLayout(protocolWidget);
    protocolForm->setContentsMargins(8, 8, 8, 8);
    protocolForm->setSpacing(6);
    protocolForm->addRow("Name",                  protName_);
    protocolForm->addRow("Objective",             protObjective_);
    protocolForm->addRow("Operator instructions", protInstructions_);
    protocolForm->addRow("Acceptance notes",      protAccept_);

    // ── Assemble QTabWidget ──────────────────────────────────────────────────
    auto* tabs = new QTabWidget(this);
    tabs->addTab(sessionWidget,    "Session");
    tabs->addTab(validationWidget, "Validation");
    tabs->addTab(protocolWidget,   "Protocol");

    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->addWidget(tabs);
}

// ── Session tab ──────────────────────────────────────────────────────────────

ads1292::SessionMetadata SessionPanel::metadata() const {
    ads1292::SessionMetadata m;
    m.session_id = sessionId_->text().toStdString();
    m.subject_id = subject_->text().toStdString();
    m.electrode  = electrode_->text().toStdString();
    m.montage    = montage_->text().toStdString();
    m.operator_  = operator_->text().toStdString();
    m.notes      = notes_->text().toStdString();
    // acquisition_mode left at its default ("live_stream")
    return m;
}

void SessionPanel::setMetadata(const ads1292::SessionMetadata& m) {
    sessionId_->setText(QString::fromStdString(m.session_id));
    subject_->setText(  QString::fromStdString(m.subject_id));
    electrode_->setText(QString::fromStdString(m.electrode));
    montage_->setText(  QString::fromStdString(m.montage));
    operator_->setText( QString::fromStdString(m.operator_));
    notes_->setText(    QString::fromStdString(m.notes));
}

// ── Validation tab ───────────────────────────────────────────────────────────

ads1292::dsp::QualityGate SessionPanel::qualityGate() const {
    ads1292::dsp::QualityGate g;

    {
        bool ok;
        double v = minDuration_->text().toDouble(&ok);
        if (ok) g.min_duration_seconds = v;
    }
    {
        bool ok;
        double v = minContact_->text().toDouble(&ok);
        if (ok) g.min_contact_ok_percent = v;
    }
    {
        bool ok;
        int v = minRPeaks_->text().toInt(&ok);
        if (ok) g.min_r_peaks = v;
    }
    {
        bool ok;
        double v = minHr_->text().toDouble(&ok);
        if (ok) g.min_hr_bpm = v;
    }
    {
        bool ok;
        double v = maxHr_->text().toDouble(&ok);
        if (ok) g.max_hr_bpm = v;
    }

    g.require_qrs_clear = qrsCheck_->isChecked();

    // Optional caps: empty field → leave as nullopt
    if (!maxDrift_->text().trimmed().isEmpty()) {
        bool ok;
        double v = maxDrift_->text().toDouble(&ok);
        if (ok) g.max_baseline_drift_counts = v;
    }
    if (!maxNoise_->text().trimmed().isEmpty()) {
        bool ok;
        double v = maxNoise_->text().toDouble(&ok);
        if (ok) g.max_noise_rms_counts = v;
    }
    if (!maxPtp_->text().trimmed().isEmpty()) {
        bool ok;
        double v = maxPtp_->text().toDouble(&ok);
        if (ok) g.max_peak_to_peak_counts = v;
    }

    return g;
}

// ── Protocol tab ─────────────────────────────────────────────────────────────

ads1292::TestProtocol SessionPanel::protocol() const {
    ads1292::TestProtocol p;
    p.name                 = protName_->text().toStdString();
    p.objective            = protObjective_->text().toStdString();
    p.operator_instructions = protInstructions_->text().toStdString();
    p.acceptance_notes     = protAccept_->text().toStdString();
    p.steps                = {};
    return p;
}

// ── Test seams ───────────────────────────────────────────────────────────────

void SessionPanel::setMinDurationForTest(double d) {
    minDuration_->setText(QString::number(d));
}

void SessionPanel::setProtocolNameForTest(const std::string& n) {
    protName_->setText(QString::fromStdString(n));
}

} // namespace ads1292::gui
