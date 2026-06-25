#pragma once
// gui/include/ads1292/gui/ReportExport.h
// Qt-linked report assembly: ECG + PQRST + spectrum PNGs + HTML.
// Requires a QApplication instance (use QT_QPA_PLATFORM=offscreen for headless).

#include "ads1292/model/Calibration.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/StreamSample.h"

#include <optional>
#include <string>
#include <vector>

namespace ads1292::gui {

/// File paths for all artifacts produced by export_review_report.
struct ReportExportResult {
    std::string html_path;
    std::string ecg_png_path;
    std::string pqrst_png_path;
    std::string spectrum_png_path;
};

/// Assembles a complete recording-review report:
///   - ECG waveform PNG (with R-peak markers + resp channel)
///   - PQRST average-beat PNG
///   - Power-spectrum + histogram PNG
///   - Styled HTML summary (metrics / gate / calibration / metadata / events tables)
///
/// File names are deterministic: a slug of \p title + fixed suffixes.
/// No timestamp — the caller may add a stamp to \p title or \p out_dir if needed.
/// Requires a QApplication instance (runs under QT_QPA_PLATFORM=offscreen).
ReportExportResult export_review_report(
    const std::vector<ads1292::StreamSample>& samples,
    const std::string& out_dir,
    const std::string& title         = "ADS1292 Studio Review",
    double sample_rate_hz            = 500.0,
    const std::string& source        = "Auto",
    const std::optional<ads1292::SessionMetadata>& metadata = std::nullopt,
    const std::vector<ads1292::EventMarker>& events         = {},
    const ads1292::Calibration& calibration                 = ads1292::Calibration{});

} // namespace ads1292::gui
