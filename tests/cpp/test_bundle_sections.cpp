// test_bundle_sections.cpp
// Verifies that each *_to_json sidecar helper reproduces the corresponding
// section of the golden recording bundle fixture, and that the bundle assembled
// by build_recording_bundle has sub-objects byte-identical to the individual
// sidecar serialisers (bundle≡sidecar invariant).

#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/CalibrationIo.h"
#include "ads1292/io/EventsIo.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/io/ProtocolIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/io/ProcessingIo.h"
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/TestProtocol.h"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/model/RecordingProcessingSettings.h"
#include <nlohmann/json.hpp>
#include <fstream>

namespace {

// Load the golden bundle fixture as plain json (alphabetically sorted).
nlohmann::json golden() {
    std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
    nlohmann::json j;
    in >> j;
    return j;
}

// Build the metadata used in the golden fixture.
ads1292::SessionMetadata fixture_metadata() {
    ads1292::SessionMetadata m;
    m.operator_ = "fixture";
    m.subject_id = "p1";
    return m;
}

// Events used in the golden fixture.
std::vector<ads1292::EventMarker> fixture_events() {
    return {{0.02, "touch", "n1", 0.0}, {0.04, "motion", "n2", 0.03}};
}

}  // namespace

TEST_CASE("each *_to_json reproduces its golden section", "[bundle]") {
    nlohmann::json g = golden();

    // Convert ordered_json → json for comparison with the alphabetically-sorted golden.
    REQUIRE(nlohmann::json(ads1292::io::metadata_to_json(fixture_metadata()))
            == g.at("metadata"));

    REQUIRE(nlohmann::json(ads1292::io::calibration_to_json(ads1292::Calibration{}))
            == g.at("calibration"));

    REQUIRE(nlohmann::json(ads1292::io::quality_gate_to_json(ads1292::dsp::QualityGate{}))
            == g.at("quality_gate"));

    REQUIRE(nlohmann::json(ads1292::io::processing_to_json(ads1292::RecordingProcessingSettings{}))
            == g.at("processing"));

    REQUIRE(nlohmann::json(ads1292::io::protocol_to_json(ads1292::TestProtocol{}))
            == g.at("protocol"));

    REQUIRE(nlohmann::json(ads1292::io::acquisition_to_json(ads1292::io::AcquisitionProvenance{}))
            == g.at("acquisition"));

    REQUIRE(nlohmann::json(ads1292::io::events_to_json(fixture_events(), 500.0))
            == g.at("events"));
}

TEST_CASE("bundle sub-objects equal corresponding *_to_json (bundle≡sidecar)", "[bundle]") {
    auto meta   = fixture_metadata();
    auto events = fixture_events();

    auto bundle = ads1292::io::build_recording_bundle(
        "rec.csv", meta, events,
        ads1292::Calibration{},
        ads1292::io::AcquisitionProvenance{},
        ads1292::TestProtocol{},
        ads1292::dsp::QualityGate{},
        ads1292::RecordingProcessingSettings{},
        500.0, "");

    // Each section of the bundle must equal the corresponding sidecar serialiser.
    REQUIRE(bundle["metadata"]     == ads1292::io::metadata_to_json(meta));
    REQUIRE(bundle["calibration"]  == ads1292::io::calibration_to_json(ads1292::Calibration{}));
    REQUIRE(bundle["events"]       == ads1292::io::events_to_json(events, 500.0));
    REQUIRE(bundle["acquisition"]  == ads1292::io::acquisition_to_json(ads1292::io::AcquisitionProvenance{}));
    REQUIRE(bundle["protocol"]     == ads1292::io::protocol_to_json(ads1292::TestProtocol{}));
    REQUIRE(bundle["quality_gate"] == ads1292::io::quality_gate_to_json(ads1292::dsp::QualityGate{}));
    REQUIRE(bundle["processing"]   == ads1292::io::processing_to_json(ads1292::RecordingProcessingSettings{}));
}
