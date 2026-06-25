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

    /// Update the live SNR (dB) and HR (bpm) labels.
    /// Shows "—" when snr_valid is false or hr_bpm <= 0.
    void updateLive(double snr_db, bool snr_valid, double hr_bpm);

private:
    QLabel* m_nextStep_     = nullptr;
    QLabel* m_connection_   = nullptr;
    QLabel* m_channelMap_   = nullptr;
    QLabel* m_recording_    = nullptr;
    QLabel* m_eventCount_   = nullptr;
    QLabel* m_snr_          = nullptr;
    QLabel* m_hr_           = nullptr;
};

} // namespace ads1292::gui
