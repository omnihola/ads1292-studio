// test_bundle_assembly.cpp
// Verifies build_recording_bundle:
//   - reproduces the full golden bundle (value equality)
//   - uses the Python-oracle top-level key order
//   - protocol steps have canonical fields (start_seconds / duration_seconds /
//     label / instruction), NOT the old stub fields (name / description)
//   - acquisition section carries the full canonical field set including
//     sample_rate_hz, channel_map, csv_columns, completion, etc.

#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/TestProtocol.h"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/model/RecordingProcessingSettings.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <vector>
#include <string>

namespace {

ads1292::SessionMetadata fixture_metadata() {
    ads1292::SessionMetadata m;
    m.operator_ = "fixture";
    m.subject_id = "p1";
    return m;
}

}  // namespace

TEST_CASE("build_recording_bundle reproduces the full golden bundle", "[bundle]") {
    std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
    nlohmann::json golden;
    in >> golden;

    std::vector<ads1292::EventMarker> events = {
        {0.02, "touch", "n1", 0.0}, {0.04, "motion", "n2", 0.03}};

    auto got = ads1292::io::build_recording_bundle(
        "rec.csv", fixture_metadata(), events,
        ads1292::Calibration{},
        ads1292::io::AcquisitionProvenance{},
        ads1292::TestProtocol{},
        ads1292::dsp::QualityGate{},
        ads1292::RecordingProcessingSettings{},
        500.0, "");

    // Convert to plain json (alphabetical) for value comparison with the golden.
    REQUIRE(nlohmann::json(got) == golden);
}

TEST_CASE("bundle top-level key order matches Python oracle", "[bundle]") {
    std::vector<ads1292::EventMarker> events;
    auto bundle = ads1292::io::build_recording_bundle(
        "rec.csv", ads1292::SessionMetadata{}, events,
        ads1292::Calibration{},
        ads1292::io::AcquisitionProvenance{},
        ads1292::TestProtocol{},
        ads1292::dsp::QualityGate{},
        ads1292::RecordingProcessingSettings{},
        500.0, "2024-01-01T00:00:00Z");

    // Iterate ordered_json to get insertion-order keys.
    std::vector<std::string> keys;
    for (auto& [k, v] : bundle.items()) keys.push_back(k);

    const std::vector<std::string> expected = {
        "schema", "created_at", "csv_name", "metadata", "events",
        "calibration", "acquisition", "protocol", "quality_gate", "processing"};
    REQUIRE(keys == expected);
}

TEST_CASE("bundle protocol steps have canonical fields (not old stub name/description)", "[bundle]") {
    ads1292::TestProtocol proto;
    proto.steps.push_back({0.0, 30.0, "baseline", "Subject seated and still."});

    std::vector<ads1292::EventMarker> events;
    auto bundle = ads1292::io::build_recording_bundle(
        "rec.csv", ads1292::SessionMetadata{}, events,
        ads1292::Calibration{},
        ads1292::io::AcquisitionProvenance{},
        proto,
        ads1292::dsp::QualityGate{},
        ads1292::RecordingProcessingSettings{},
        500.0, "");

    auto& step0 = bundle["protocol"]["steps"][0];

    // Canonical fields present.
    REQUIRE(step0.contains("start_seconds"));
    REQUIRE(step0.contains("duration_seconds"));
    REQUIRE(step0.contains("label"));
    REQUIRE(step0.contains("instruction"));

    // Old stub fields absent (the bug being fixed).
    REQUIRE_FALSE(step0.contains("name"));
    REQUIRE_FALSE(step0.contains("description"));

    REQUIRE(step0["start_seconds"].get<double>()    == Approx(0.0));
    REQUIRE(step0["duration_seconds"].get<double>() == Approx(30.0));
    REQUIRE(step0["label"].get<std::string>()       == "baseline");
    REQUIRE(step0["instruction"].get<std::string>() == "Subject seated and still.");
}

TEST_CASE("bundle acquisition carries the full canonical field set", "[bundle]") {
    std::vector<ads1292::EventMarker> events;
    auto bundle = ads1292::io::build_recording_bundle(
        "rec.csv", ads1292::SessionMetadata{}, events,
        ads1292::Calibration{},
        ads1292::io::AcquisitionProvenance{},
        ads1292::TestProtocol{},
        ads1292::dsp::QualityGate{},
        ads1292::RecordingProcessingSettings{},
        500.0, "");

    auto& acq = bundle["acquisition"];

    // Fields from canonical AcquisitionProvenance (not the old 7-field stub).
    REQUIRE(acq.contains("schema"));
    REQUIRE(acq.contains("csv_name"));
    REQUIRE(acq.contains("csv_schema"));
    REQUIRE(acq.contains("acquisition_mode"));
    REQUIRE(acq.contains("port"));
    REQUIRE(acq.contains("sample_rate_hz"));
    REQUIRE(acq.contains("started_at"));
    REQUIRE(acq.contains("timestamp_reference"));
    REQUIRE(acq.contains("channel_map"));
    REQUIRE(acq.contains("csv_columns"));
    REQUIRE(acq.contains("raw_adc"));
    REQUIRE(acq.contains("live_calibration"));
    REQUIRE(acq.contains("completion"));

    // sample_rate_hz is propagated from the struct (not the bundle parameter).
    REQUIRE(acq["sample_rate_hz"].get<double>() == Approx(500.0));
}
