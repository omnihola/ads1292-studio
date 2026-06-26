#pragma once
#include <QWidget>
#include "ads1292/model/SessionMetadata.h"

class QLineEdit;

namespace ads1292::gui {

/// Left-pane input panel for session metadata (Session ID, Subject, Electrode,
/// Montage, Operator, Notes).  Presents a QFormLayout of 6 QLineEdit fields.
/// Pre-filled with the same defaults as SessionMetadata{} so an unedited panel
/// is parity-neutral with the struct's default-constructed value.
/// No Q_OBJECT — no signals or slots.
class SessionPanel : public QWidget {
public:
    explicit SessionPanel(QWidget* parent = nullptr);
    ~SessionPanel() override = default;

    /// Read the 6 line edits and return a SessionMetadata struct.
    /// Does NOT normalize — leave that to the finalize pipeline.
    /// acquisition_mode is left at its default ("live_stream").
    ads1292::SessionMetadata metadata() const;

    /// Populate all 6 line edits from the given struct (for load/restore).
    void setMetadata(const ads1292::SessionMetadata& m);

private:
    QLineEdit* sessionId_ = nullptr;
    QLineEdit* subject_   = nullptr;
    QLineEdit* electrode_ = nullptr;
    QLineEdit* montage_   = nullptr;
    QLineEdit* operator_  = nullptr;
    QLineEdit* notes_     = nullptr;
};

} // namespace ads1292::gui
