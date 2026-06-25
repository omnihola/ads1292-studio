// gui/src/EventConsole.cpp
#include "ads1292/gui/EventConsole.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QPushButton>
#include <QString>

namespace ads1292::gui {

EventConsole::EventConsole(QWidget* parent)
    : QWidget(parent)
{
    auto* root = new QVBoxLayout(this);
    root->setContentsMargins(8, 8, 8, 8);
    root->setSpacing(6);

    // Label / Notes inputs
    auto* form = new QFormLayout;
    m_labelEdit_ = new QLineEdit(this);
    m_notesEdit_ = new QLineEdit(this);
    form->addRow("Label:", m_labelEdit_);
    form->addRow("Notes:", m_notesEdit_);
    root->addLayout(form);

    // Action buttons
    auto* btnRow = new QHBoxLayout;
    auto* btnAdd      = new QPushButton("Add Point",    this);
    auto* btnStart    = new QPushButton("Start Range",  this);
    auto* btnEnd      = new QPushButton("End Range",    this);
    auto* btnRemove   = new QPushButton("Remove Last",  this);
    btnRow->addWidget(btnAdd);
    btnRow->addWidget(btnStart);
    btnRow->addWidget(btnEnd);
    btnRow->addWidget(btnRemove);
    root->addLayout(btnRow);

    // Status line
    m_status_ = new QLabel("Events: 0", this);
    root->addWidget(m_status_);

    // Wire buttons with lambdas (no Q_OBJECT needed on EventConsole)
    QObject::connect(btnAdd, &QPushButton::clicked, this, [this] {
        addPointEventForTest(
            m_labelEdit_->text().toStdString(),
            m_notesEdit_->text().toStdString());
    });

    QObject::connect(btnStart, &QPushButton::clicked, this, [this] {
        log_.start_range(sampleClock_);
        refreshStatus();
    });

    QObject::connect(btnEnd, &QPushButton::clicked, this, [this] {
        log_.end_range(
            sampleClock_,
            m_labelEdit_->text().toStdString(),
            m_notesEdit_->text().toStdString());
        refreshStatus();
    });

    QObject::connect(btnRemove, &QPushButton::clicked, this, [this] {
        log_.remove_last();
        refreshStatus();
    });
}

void EventConsole::setSampleClock(double seconds) {
    sampleClock_ = seconds;
}

const ads1292::view::EventLog& EventConsole::log() const {
    return log_;
}

void EventConsole::addPointEventForTest(const std::string& label,
                                        const std::string& notes) {
    log_.add_point(sampleClock_, label, notes);
    refreshStatus();
}

void EventConsole::setEventStatus(int count, std::optional<double> pendingStart) {
    QString text = "Events: " + QString::number(count);
    if (pendingStart.has_value()) {
        text += QString("  [range started @ %1 s]").arg(*pendingStart);
    }
    m_status_->setText(text);
}

void EventConsole::refreshStatus() {
    setEventStatus(
        static_cast<int>(log_.events().size()),
        log_.pending_range_start());
}

} // namespace ads1292::gui
