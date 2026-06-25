#pragma once
#include <string>

namespace ads1292::gui {

/// Snapshot of the application's live state, used to drive the StatusPanel.
struct GuiState {
    std::string nextStep;
    std::string connection;
    std::string channelMap;
    std::string recordingState;
    int         eventCount = 0;
};

} // namespace ads1292::gui
