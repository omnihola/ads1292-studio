#pragma once
// io/include/ads1292/io/Bundle.h
// Recording-bundle assembly and write.
// Uses CANONICAL types only — no local duplicate definitions.
// No Qt.

#include <string>
#include <vector>
#include <nlohmann/json.hpp>
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/model/TestProtocol.h"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/model/RecordingProcessingSettings.h"

namespace ads1292 {
namespace io {

/// Assemble a recording bundle from canonical component types.
///
/// Top-level key order (matches Python recording_bundle.py oracle):
///   schema, created_at, csv_name, metadata, events, calibration,
///   acquisition, protocol, quality_gate, processing.
///
/// Each sub-object is produced by the corresponding *_to_json helper
/// (so bundle[section] == section_to_json(section_arg) for every section).
nlohmann::ordered_json build_recording_bundle(
    const std::string& csv_name,
    const ads1292::SessionMetadata& metadata,
    const std::vector<ads1292::EventMarker>& events,
    const ads1292::Calibration& calibration,
    const ads1292::io::AcquisitionProvenance& acquisition,
    const ads1292::TestProtocol& protocol,
    const ads1292::dsp::QualityGate& quality_gate,
    const ads1292::RecordingProcessingSettings& processing,
    double sample_rate_hz,
    const std::string& created_at);

/// Write the recording bundle to <csv_path with .json extension>.
/// Parent directories are created as needed.
/// Returns the bundle file path written.
std::string write_recording_bundle(
    const std::string& csv_path,
    const ads1292::SessionMetadata& metadata,
    const std::vector<ads1292::EventMarker>& events,
    const ads1292::Calibration& calibration,
    const ads1292::io::AcquisitionProvenance& acquisition,
    const ads1292::TestProtocol& protocol,
    const ads1292::dsp::QualityGate& quality_gate,
    const ads1292::RecordingProcessingSettings& processing,
    double sample_rate_hz,
    const std::string& created_at);

}  // namespace io
}  // namespace ads1292
