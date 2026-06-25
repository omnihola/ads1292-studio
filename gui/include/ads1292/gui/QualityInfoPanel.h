#pragma once
// gui/include/ads1292/gui/QualityInfoPanel.h
// Review panel: read-only quality metrics text display.
// Pure Qt widget, no plot backend needed.

#include "ads1292/dsp/QualityMetrics.h"

#include <QWidget>

class QPlainTextEdit;

namespace ads1292::gui {

/// A QWidget showing a formatted, read-only summary of QualityMetrics fields
/// plus the human-readable quality label.
class QualityInfoPanel : public QWidget {
public:
    explicit QualityInfoPanel(QWidget* parent = nullptr);
    ~QualityInfoPanel() override = default;

    /// Render all QualityMetrics fields + quality_label into the text view.
    void showMetrics(const ads1292::dsp::QualityMetrics& m);

private:
    QPlainTextEdit* text_{nullptr};
};

} // namespace ads1292::gui
