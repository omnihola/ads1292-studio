#pragma once
// io/include/ads1292/io/RecordingBundle.h
// Recording-bundle READ side.
// Counterpart to Bundle.h (write side).
// No Qt; pure C++17 + nlohmann.

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

/// Return the bundle sidecar path for the given CSV path.
/// Replaces the file extension with ".json".
/// Mirrors Python recording_bundle_path() / Path.with_suffix(".json").
std::string recording_bundle_path(const std::string& csv_path);

/// Return true iff @p path exists, parses as JSON, and has
/// schema == "ads1292-recording-bundle-v1".
/// Swallows ALL errors (missing file, parse error, wrong/missing schema) → false.
/// Mirrors Python is_recording_bundle_path() (try/except → False).
bool is_recording_bundle_path(const std::string& path);

/// Read and validate a recording bundle.
/// If @p path_or_csv does not end in ".json", maps via recording_bundle_path first.
/// Parses the file; throws std::runtime_error if the file cannot be read or
/// does not carry schema == "ads1292-recording-bundle-v1".
nlohmann::json read_recording_bundle(const std::string& path_or_csv);

// ---------------------------------------------------------------------------
// Per-section extractors
// Each reads bundle["<section>"] and returns the canonical type by delegating
// to the corresponding *_from_json helper (sidecar parse logic reused).
// ---------------------------------------------------------------------------

/// Extract and parse bundle["metadata"] → SessionMetadata.
ads1292::SessionMetadata metadata_from_bundle(const nlohmann::json& bundle);

/// Extract and parse bundle["events"] → vector<EventMarker>.
std::vector<ads1292::EventMarker> events_from_bundle(const nlohmann::json& bundle);

/// Extract and parse bundle["calibration"] → Calibration.
ads1292::Calibration calibration_from_bundle(const nlohmann::json& bundle);

/// Extract and parse bundle["acquisition"] → AcquisitionProvenance.
ads1292::io::AcquisitionProvenance acquisition_from_bundle(const nlohmann::json& bundle);

/// Extract and parse bundle["protocol"] → TestProtocol.
ads1292::TestProtocol protocol_from_bundle(const nlohmann::json& bundle);

/// Extract and parse bundle["quality_gate"] → QualityGate.
ads1292::dsp::QualityGate quality_gate_from_bundle(const nlohmann::json& bundle);

/// Extract and parse bundle["processing"] → RecordingProcessingSettings.
ads1292::RecordingProcessingSettings processing_from_bundle(const nlohmann::json& bundle);

}  // namespace io
}  // namespace ads1292
