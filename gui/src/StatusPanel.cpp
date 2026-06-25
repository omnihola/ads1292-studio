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

    layout->addWidget(m_nextStep_);
    layout->addWidget(m_connection_);
    layout->addWidget(m_channelMap_);
    layout->addWidget(m_recording_);
    layout->addWidget(m_eventCount_);
    layout->addStretch();
}

void StatusPanel::updateFromState(const GuiState& s) {
    m_nextStep_->setText("Next step: "   + QString::fromStdString(s.nextStep));
    m_connection_->setText("Connection: " + QString::fromStdString(s.connection));
    m_channelMap_->setText("Channel map: "+ QString::fromStdString(s.channelMap));
    m_recording_->setText("Recording: "  + QString::fromStdString(s.recordingState));
    m_eventCount_->setText("Events: "    + QString::number(s.eventCount));
}

} // namespace ads1292::gui
