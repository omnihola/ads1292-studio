#pragma once
#include <QWidget>
#include <QLabel>
#include "ads1292/gui/GuiState.h"

namespace ads1292::gui {

/// Right-side status panel: a vertical stack of labeled QLabel cards.
/// Call updateFromState() whenever the GuiState changes.
class StatusPanel : public QWidget {
public:
    explicit StatusPanel(QWidget* parent = nullptr);
    ~StatusPanel() override = default;

    /// Refresh every card label from the given state snapshot.
    void updateFromState(const GuiState& s);

private:
    QLabel* m_nextStep_     = nullptr;
    QLabel* m_connection_   = nullptr;
    QLabel* m_channelMap_   = nullptr;
    QLabel* m_recording_    = nullptr;
    QLabel* m_eventCount_   = nullptr;
};

} // namespace ads1292::gui
