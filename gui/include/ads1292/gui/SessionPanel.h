#pragma once
#include <QWidget>
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/model/TestProtocol.h"

class QLineEdit;
class QCheckBox;

namespace ads1292::gui {

/// Left-pane input panel with three tabs:
///   Session    — 6 QLineEdit fields for session metadata
///   Validation — QualityGate threshold fields
///   Protocol   — TestProtocol text fields
/// Pre-filled with struct defaults so an unedited panel is parity-neutral.
/// No Q_OBJECT — no signals or slots.
class SessionPanel : public QWidget {
public:
    explicit SessionPanel(QWidget* parent = nullptr);
    ~SessionPanel() override = default;

    // ── Session tab ──────────────────────────────────────────────────────────

    /// Read the 6 line edits and return a SessionMetadata struct.
    /// Does NOT normalize — leave that to the finalize pipeline.
    /// acquisition_mode is left at its default ("live_stream").
    ads1292::SessionMetadata metadata() const;

    /// Populate all 6 line edits from the given struct (for load/restore).
    void setMetadata(const ads1292::SessionMetadata& m);

    // ── Validation tab ───────────────────────────────────────────────────────

    /// Build a QualityGate from the Validation tab fields.
    /// Numeric parse failure keeps the struct default.
    /// Empty optional-cap fields → std::nullopt.
    ads1292::dsp::QualityGate qualityGate() const;

    // ── Protocol tab ─────────────────────────────────────────────────────────

    /// Build a TestProtocol from the Protocol tab fields.
    /// steps is always left empty (not user-edited here).
    ads1292::TestProtocol protocol() const;

    // ── Test seams ───────────────────────────────────────────────────────────

    void setMinDurationForTest(double d);
    void setProtocolNameForTest(const std::string& n);

private:
    // Session tab widgets
    QLineEdit* sessionId_ = nullptr;
    QLineEdit* subject_   = nullptr;
    QLineEdit* electrode_ = nullptr;
    QLineEdit* montage_   = nullptr;
    QLineEdit* operator_  = nullptr;
    QLineEdit* notes_     = nullptr;

    // Validation tab widgets
    QLineEdit* minDuration_ = nullptr;
    QLineEdit* minContact_  = nullptr;
    QLineEdit* minRPeaks_   = nullptr;
    QLineEdit* minHr_       = nullptr;
    QLineEdit* maxHr_       = nullptr;
    QCheckBox* qrsCheck_    = nullptr;
    QLineEdit* maxDrift_    = nullptr;
    QLineEdit* maxNoise_    = nullptr;
    QLineEdit* maxPtp_      = nullptr;

    // Protocol tab widgets
    QLineEdit* protName_         = nullptr;
    QLineEdit* protObjective_    = nullptr;
    QLineEdit* protInstructions_ = nullptr;
    QLineEdit* protAccept_       = nullptr;
};

} // namespace ads1292::gui
