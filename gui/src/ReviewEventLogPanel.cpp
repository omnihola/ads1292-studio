// gui/src/ReviewEventLogPanel.cpp
// Event log review panel — read-only text display of EventMarkers.

#include "ads1292/gui/ReviewEventLogPanel.h"

#include <QPlainTextEdit>
#include <QVBoxLayout>

#include <sstream>
#include <iomanip>

namespace ads1292::gui {

ReviewEventLogPanel::ReviewEventLogPanel(QWidget* parent)
    : QWidget(parent)
    , text_(new QPlainTextEdit(this))
{
    text_->setReadOnly(true);

    auto* layout = new QVBoxLayout(this);
    layout->setContentsMargins(0, 0, 0, 0);
    layout->addWidget(text_);
    setLayout(layout);
}

void ReviewEventLogPanel::appendLine(const std::string& line)
{
    text_->appendPlainText(QString::fromStdString(line));
}

void ReviewEventLogPanel::setEvents(const std::vector<ads1292::EventMarker>& events)
{
    text_->clear();

    if (events.empty()) {
        text_->setPlainText("(no events recorded)");
        return;
    }

    std::ostringstream os;
    os << "— events —\n";

    for (std::size_t i = 0; i < events.size(); ++i) {
        const auto& ev = events[i];
        os << (i + 1) << ". t=" << std::fixed << std::setprecision(3)
           << ev.timestamp_seconds << "s"
           << " [" << ev.label << "]";

        if (!ev.notes.empty()) {
            os << " " << ev.notes;
        }

        if (ev.is_interval()) {
            os << " (duration " << std::setprecision(3)
               << ev.duration_seconds << "s)";
        }

        os << "\n";
    }

    text_->setPlainText(QString::fromStdString(os.str()));
}

} // namespace ads1292::gui
