// gui/src/StatusPanel.cpp
#include "ads1292/gui/StatusPanel.h"
#include <QVBoxLayout>
#include <QString>

namespace ads1292::gui {

namespace {
/// Create a card: a QLabel with a descriptive prefix hard-coded into the text.
QLabel* makeCard(QWidget* parent, const QString& prefix) {
    auto* label = new QLabel(prefix + "—", parent);
    label->setWordWrap(true);
    return label;
}
} // namespace

StatusPanel::StatusPanel(QWidget* parent)
    : QWidget(parent)
{
    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(8, 8, 8, 8);
    layout->setSpacing(6);

    m_nextStep_   = makeCard(this, "Next step: ");
    m_connection_ = makeCard(this, "Connection: ");
    m_channelMap_ = makeCard(this, "Channel map: ");
    m_recording_  = makeCard(this, "Recording: ");
    m_eventCount_ = makeCard(this, "Events: ");
    m_snr_        = makeCard(this, "SNR: ");
    m_hr_         = makeCard(this, "HR: ");

    layout->addWidget(m_nextStep_);
    layout->addWidget(m_connection_);
    layout->addWidget(m_channelMap_);
    layout->addWidget(m_recording_);
    layout->addWidget(m_eventCount_);
    layout->addWidget(m_snr_);
    layout->addWidget(m_hr_);
    layout->addStretch();
}

void StatusPanel::updateFromState(const GuiState& s) {
    m_nextStep_->setText("Next step: "   + QString::fromStdString(s.nextStep));
    m_connection_->setText("Connection: " + QString::fromStdString(s.connection));
    m_channelMap_->setText("Channel map: "+ QString::fromStdString(s.channelMap));
    m_recording_->setText("Recording: "  + QString::fromStdString(s.recordingState));
    m_eventCount_->setText("Events: "    + QString::number(s.eventCount));
}

void StatusPanel::updateLive(double snr_db, bool snr_valid, double hr_bpm) {
    if (snr_valid) {
        m_snr_->setText("SNR: " + QString::number(snr_db, 'f', 1) + " dB");
    } else {
        m_snr_->setText("SNR: —");
    }
    if (hr_bpm > 0.0) {
        m_hr_->setText("HR: " + QString::number(static_cast<int>(hr_bpm + 0.5)) + " bpm");
    } else {
        m_hr_->setText("HR: —");
    }
}

} // namespace ads1292::gui
