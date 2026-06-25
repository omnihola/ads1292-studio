#pragma once
// core/include/ads1292/model/RecordingProcessingSettings.h
// Recording processing settings: display + filter sub-objects + acquisition parameters.
// Pure C++17 — no Qt, no nlohmann in this header. JSON I/O lives in io/ProcessingIo.

#include "ads1292/dsp/Display.h"
#include <string>

namespace ads1292 {

struct RecordingProcessingSettings {
    std::string schema          = "ads1292-processing-settings-v1";
    dsp::EcgDisplaySettings    display;
    dsp::SoftwareFilterSettings software_filters;
    double sample_rate_hz       = 500.0;
    bool   ecg_inverted         = false;
    int    smoothing_window      = 11;
    std::string processing_notes = "display settings only; raw CSV samples are unchanged";

    /// Return a copy with all fields clamped/snapped to valid ranges.
    /// - display: snapped via EcgDisplaySettings::normalized()
    /// - software_filters: passed through unchanged (no normalize defined)
    /// - schema: trimmed, falls back to default if empty
    /// - sample_rate_hz: >0 or falls back to 500.0
    /// - smoothing_window: max(1, smoothing_window)
    /// - processing_notes: trimmed, falls back to default if empty
    RecordingProcessingSettings normalized() const;
};

} // namespace ads1292
