// io/src/Bundle.cpp
// Recording-bundle assembly using canonical sidecar serialisers.
// No Qt.

#include "ads1292/io/Bundle.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/CalibrationIo.h"
#include "ads1292/io/EventsIo.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/io/ProtocolIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/io/ProcessingIo.h"
#include <filesystem>
#include <fstream>
#include <stdexcept>

namespace ads1292 {
namespace io {

// ── build_recording_bundle ────────────────────────────────────────────────

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
    const std::string& created_at)
{
    // Key order matches Python oracle (recording_bundle.py build_recording_bundle):
    // schema, created_at, csv_name, metadata, events, calibration,
    // acquisition, protocol, quality_gate, processing.
    nlohmann::ordered_json bundle;
    bundle["schema"]       = "ads1292-recording-bundle-v1";
    bundle["created_at"]   = created_at;
    bundle["csv_name"]     = csv_name;
    bundle["metadata"]     = metadata_to_json(metadata);
    bundle["events"]       = events_to_json(events, sample_rate_hz);
    bundle["calibration"]  = calibration_to_json(calibration);
    bundle["acquisition"]  = acquisition_to_json(acquisition);
    bundle["protocol"]     = protocol_to_json(protocol);
    bundle["quality_gate"] = quality_gate_to_json(quality_gate);
    bundle["processing"]   = processing_to_json(processing);
    return bundle;
}

// ── write_recording_bundle ────────────────────────────────────────────────

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
    const std::string& created_at)
{
    // Bundle path: replace .csv extension with .json (mirrors recording_bundle_path() in Python).
    const auto bundle_path =
        std::filesystem::path(csv_path).replace_extension(".json");
    const std::string csv_name =
        std::filesystem::path(csv_path).filename().string();

    const auto parent = bundle_path.parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }

    const auto bundle = build_recording_bundle(
        csv_name, metadata, events, calibration, acquisition, protocol,
        quality_gate, processing, sample_rate_hz, created_at);

    std::ofstream f(bundle_path);
    if (!f.is_open()) {
        throw std::runtime_error(
            "Bundle: cannot write file: " + bundle_path.string());
    }
    f << bundle.dump(2) << "\n";
    return bundle_path.string();
}

}  // namespace io
}  // namespace ads1292
