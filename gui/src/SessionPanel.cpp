// gui/src/SessionPanel.cpp
#include "ads1292/gui/SessionPanel.h"
#include <QFormLayout>
#include <QLineEdit>
#include <QString>

namespace ads1292::gui {

SessionPanel::SessionPanel(QWidget* parent)
    : QWidget(parent)
{
    sessionId_ = new QLineEdit(this);
    subject_   = new QLineEdit(this);
    electrode_ = new QLineEdit(this);
    montage_   = new QLineEdit(this);
    operator_  = new QLineEdit(this);
    notes_     = new QLineEdit(this);

    // Pre-fill defaults that match SessionMetadata{}
    subject_->setText("anonymous");
    montage_->setText("RA/LA/RL torso");

    auto* layout = new QFormLayout(this);
    layout->setContentsMargins(8, 8, 8, 8);
    layout->setSpacing(6);

    layout->addRow("Session ID", sessionId_);
    layout->addRow("Subject",    subject_);
    layout->addRow("Electrode",  electrode_);
    layout->addRow("Montage",    montage_);
    layout->addRow("Operator",   operator_);
    layout->addRow("Notes",      notes_);
}

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

} // namespace ads1292::gui
