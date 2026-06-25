// core/src/model/RecordingProcessingSettings.cpp
#include "ads1292/model/RecordingProcessingSettings.h"
#include <algorithm>
#include <string>

namespace ads1292 {

namespace {

/// Trim leading/trailing ASCII whitespace from s.
static std::string trim(const std::string& s) {
    const auto is_ws = [](unsigned char c) {
        return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v';
    };
    auto begin = s.begin();
    while (begin != s.end() && is_ws(static_cast<unsigned char>(*begin)))
        ++begin;
    auto end = s.end();
    while (end != begin && is_ws(static_cast<unsigned char>(*(end - 1))))
        --end;
    return std::string(begin, end);
}

} // namespace

RecordingProcessingSettings RecordingProcessingSettings::normalized() const {
    RecordingProcessingSettings n;

    // schema: trim; if empty fall back to default
    const std::string trimmed_schema = trim(schema);
    n.schema = trimmed_schema.empty() ? "ads1292-processing-settings-v1" : trimmed_schema;

    // display: snap to nearest choice via EcgDisplaySettings::normalized()
    n.display = display.normalized();

    // software_filters: passed through unchanged
    n.software_filters = software_filters;

    // sample_rate_hz: must be positive, else 500.0
    n.sample_rate_hz = (sample_rate_hz > 0.0) ? sample_rate_hz : 500.0;

    // ecg_inverted: pass through
    n.ecg_inverted = ecg_inverted;

    // smoothing_window: at least 1
    n.smoothing_window = std::max(1, smoothing_window);

    // processing_notes: trim; if empty fall back to default
    const std::string trimmed_notes = trim(processing_notes);
    n.processing_notes = trimmed_notes.empty()
        ? "display settings only; raw CSV samples are unchanged"
        : trimmed_notes;

    return n;
}

} // namespace ads1292
