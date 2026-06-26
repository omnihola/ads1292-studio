// io/src/RecordingBundle.cpp
// Recording-bundle READ side: recording_bundle_path, is_recording_bundle_path,
// read_recording_bundle, and the 7 *_from_bundle extractors.
//
// Each extractor delegates to the corresponding *_from_json helper (defined in
// the individual sidecar Io modules), guaranteeing bundle-read ≡ sidecar-read.
//
// No Qt; pure C++17 + nlohmann.

#include "ads1292/io/RecordingBundle.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/CalibrationIo.h"
#include "ads1292/io/EventsIo.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/io/ProtocolIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/io/ProcessingIo.h"

#include <nlohmann/json.hpp>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>

namespace ads1292 {
namespace io {

namespace {
static constexpr const char* BUNDLE_SCHEMA = "ads1292-recording-bundle-v1";
}  // namespace

// ---------------------------------------------------------------------------
// recording_bundle_path
// Mirrors Python recording_bundle_path = Path(csv_path).with_suffix(".json").
// ---------------------------------------------------------------------------
std::string recording_bundle_path(const std::string& csv_path) {
    namespace fs = std::filesystem;
    return fs::path(csv_path).replace_extension(".json").string();
}

// ---------------------------------------------------------------------------
// is_recording_bundle_path
// Swallows ALL errors → false.  Mirrors Python try/except → False pattern.
// ---------------------------------------------------------------------------
bool is_recording_bundle_path(const std::string& path) {
    try {
        namespace fs = std::filesystem;
        if (!fs::exists(path)) return false;

        std::ifstream f(path);
        if (!f.is_open()) return false;

        nlohmann::json j;
        f >> j;

        if (!j.is_object()) return false;
        return j.value("schema", std::string()) == BUNDLE_SCHEMA;
    } catch (...) {
        return false;
    }
}

// ---------------------------------------------------------------------------
// read_recording_bundle
// ---------------------------------------------------------------------------
nlohmann::json read_recording_bundle(const std::string& path_or_csv) {
    namespace fs = std::filesystem;
    fs::path p(path_or_csv);

    // Map non-json paths through recording_bundle_path.
    if (p.extension() != ".json") {
        p = fs::path(recording_bundle_path(path_or_csv));
    }

    std::ifstream f(p);
    if (!f.is_open()) {
        throw std::runtime_error(
            "RecordingBundle: cannot open bundle file: " + p.string());
    }

    nlohmann::json j;
    f >> j;

    if (!j.is_object() || j.value("schema", std::string()) != BUNDLE_SCHEMA) {
        throw std::runtime_error(
            "RecordingBundle: not an ADS1292 recording bundle: " + p.string());
    }

    return j;
}

// ---------------------------------------------------------------------------
// Per-section extractors
// Each reads bundle.at("<section>") then delegates to *_from_json.
// ---------------------------------------------------------------------------

ads1292::SessionMetadata metadata_from_bundle(const nlohmann::json& bundle) {
    return metadata_from_json(bundle.at("metadata"));
}

std::vector<ads1292::EventMarker> events_from_bundle(const nlohmann::json& bundle) {
    return events_from_json(bundle.at("events"));
}

ads1292::Calibration calibration_from_bundle(const nlohmann::json& bundle) {
    return calibration_from_json(bundle.at("calibration"));
}

ads1292::io::AcquisitionProvenance acquisition_from_bundle(const nlohmann::json& bundle) {
    return acquisition_from_json(bundle.at("acquisition"));
}

ads1292::TestProtocol protocol_from_bundle(const nlohmann::json& bundle) {
    return protocol_from_json(bundle.at("protocol"));
}

ads1292::dsp::QualityGate quality_gate_from_bundle(const nlohmann::json& bundle) {
    return quality_gate_from_json(bundle.at("quality_gate"));
}

ads1292::RecordingProcessingSettings processing_from_bundle(const nlohmann::json& bundle) {
    // Match Python: if processing is missing or empty, return defaults.
    if (!bundle.contains("processing") || bundle.at("processing").is_null()) {
        return build_processing_settings();
    }
    return processing_from_json(bundle.at("processing"));
}

}  // namespace io
}  // namespace ads1292
