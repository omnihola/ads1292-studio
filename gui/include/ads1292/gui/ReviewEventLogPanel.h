#pragma once
// gui/include/ads1292/gui/ReviewEventLogPanel.h
// Review panel: read-only event log display.
// Pure Qt widget, no plot backend needed.

#include "ads1292/model/EventMarker.h"

#include <QWidget>
#include <string>
#include <vector>

class QPlainTextEdit;

namespace ads1292::gui {

/// A QWidget showing a scrollable, read-only log of event markers.
class ReviewEventLogPanel : public QWidget {
public:
    explicit ReviewEventLogPanel(QWidget* parent = nullptr);
    ~ReviewEventLogPanel() override = default;

    /// Append a single line of text to the log.
    void appendLine(const std::string& line);

    /// Replace the log contents with a formatted list of EventMarkers.
    /// If events is empty, shows a placeholder message.
    void setEvents(const std::vector<ads1292::EventMarker>& events);

private:
    QPlainTextEdit* text_{nullptr};
};

} // namespace ads1292::gui
