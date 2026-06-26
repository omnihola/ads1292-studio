#pragma once
// io/include/ads1292/io/ProcessingIo.h
// JSON read/write/build for RecordingProcessingSettings.
// No Qt.

#include <string>
#include <nlohmann/json.hpp>
#include "ads1292/model/RecordingProcessingSettings.h"

namespace ads1292 {
namespace io {

/// Return the ordered JSON object for @p p (after normalizing).
/// Top-level keys: schema, display, software_filters, sample_rate_hz,
/// ecg_inverted, smoothing_window, processing_notes.
/// Byte-identical to the object written by write_processing_json.
nlohmann::ordered_json processing_to_json(const ads1292::RecordingProcessingSettings& p);

/// Read a processing JSON file from @p path and return a normalized RecordingProcessingSettings.
/// Unknown keys are ignored; missing keys keep struct defaults.
/// Throws std::runtime_error if the file cannot be opened or the root is not a JSON object.
ads1292::RecordingProcessingSettings read_processing_json(const std::string& path);

/// Write @p p (after normalizing) as a pretty-printed JSON object to @p path.
/// Parent directories are created as needed.
void write_processing_json(const std::string& path, const ads1292::RecordingProcessingSettings& p);

/// Return the canonical default RecordingProcessingSettings (all fields at their defaults,
/// normalized). Matches Python build_processing_settings() with no arguments.
ads1292::RecordingProcessingSettings build_processing_settings();

}  // namespace io
}  // namespace ads1292
