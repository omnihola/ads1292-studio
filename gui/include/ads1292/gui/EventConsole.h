#pragma once
#include <optional>
#include <string>
#include <QWidget>
#include <QLabel>
#include <QLineEdit>
#include "ads1292/view/EventLog.h"

namespace ads1292::gui {

/// Event-annotation console: label + notes inputs, four action buttons,
/// and an owned EventLog. Wired with lambdas — no Q_OBJECT required.
class EventConsole : public QWidget {
public:
    explicit EventConsole(QWidget* parent = nullptr);
    ~EventConsole() override = default;

    /// Update the timestamp used by the quick action buttons.
    void setSampleClock(double seconds);

    /// Read-only access to the owned EventLog.
    const ads1292::view::EventLog& log() const;

    /// Test hook: exercises the same add-point path as the "Add Point" button.
    void addPointEventForTest(const std::string& label, const std::string& notes);

    /// Refresh the status line with the current event count and pending range.
    void setEventStatus(int count, std::optional<double> pendingStart);

private:
    void refreshStatus();

    ads1292::view::EventLog log_;
    double                  sampleClock_ = 0.0;

    QLineEdit* m_labelEdit_ = nullptr;
    QLineEdit* m_notesEdit_ = nullptr;
    QLabel*    m_status_    = nullptr;
};

} // namespace ads1292::gui
