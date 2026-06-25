#pragma once
// io/include/ads1292/io/ReviewHtml.h
// Qt-free HTML report builder reproducing report.py::_html structure + values.
// Pure C++17, stdlib only, no Qt, no nlohmann.

#include "ads1292/dsp/QualityGate.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/SessionMetadata.h"

#include <optional>
#include <string>
#include <vector>

namespace ads1292::io {

/// All inputs required to render a review HTML report (matches report.py::_html parameters).
struct ReviewHtmlInputs {
    std::string title;

    ads1292::dsp::QualityMetrics  metrics;
    ads1292::dsp::QualityGateResult gate;
    ads1292::Calibration           calibration;

    std::optional<ads1292::SessionMetadata> metadata;
    std::vector<ads1292::EventMarker>       events;

    /// Basename of the ECG PNG to embed (e.g. "ecg.png").
    std::string ecg_png_name;
    /// Basename of the PQRST PNG to embed.
    std::string pqrst_png_name;
    /// Basename of the spectrum PNG to embed.
    std::string spectrum_png_name;
};

/// Renders a styled HTML report reproducing report.py::_html (non-deferred sections).
/// Protocol/segment-metrics/segment-gate sections are DEFERRED (not ported).
/// Returns the complete HTML document as a UTF-8 string.
std::string build_review_html(const ReviewHtmlInputs& in);

} // namespace ads1292::io
