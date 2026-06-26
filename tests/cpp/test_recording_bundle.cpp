// tests/cpp/test_recording_bundle.cpp
// Round-trip tests for the recording-bundle READ side (P10 Task 2).
//
// Strategy: build a bundle with known canonical values via build_recording_bundle /
// write_recording_bundle (Task 1), then exercise:
//   recording_bundle_path, is_recording_bundle_path, read_recording_bundle,
//   and all 7 *_from_bundle extractors.

#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/io/RecordingBundle.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/TestProtocol.h"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/model/RecordingProcessingSettings.h"
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

// ---------------------------------------------------------------------------
// Helpers — build the known canonical objects used across all test cases.
// ---------------------------------------------------------------------------
namespace {

ads1292::SessionMetadata make_metadata() {
    ads1292::SessionMetadata m;
    m.session_id  = "bundle-sess";
    m.subject_id  = "subj-42";
    m.electrode   = "Ag/AgCl";
    m.operator_   = "op1";
    m.notes       = "round-trip test";
    return m;
}

ads1292::io::AcquisitionProvenance make_acquisition() {
    ads1292::io::AcquisitionProvenance a;
    a.port            = "COM3";
    a.sample_rate_hz  = 500.0;
    a.acquisition_mode = "live_stream";
    return a;
}

ads1292::Calibration make_calibration() {
    ads1292::Calibration c;
    c.vref_mv  = 2.42;
    c.pga_gain = 6.0;
    c.adc_bits = 24;
    c.label    = "test-cal";
    return c;
}

ads1292::TestProtocol make_protocol() {
    ads1292::TestProtocol p;
    p.name      = "round-trip protocol";
    p.objective = "verify bundle read";
    p.steps.push_back({5.0, 20.0, "rest", "sit still"});
    p.steps.push_back({25.0, 10.0, "motion", "move arm"});
    return p;
}

std::vector<ads1292::EventMarker> make_events() {
    return {
        ads1292::EventMarker{1.5, "start",  "begin",  0.0},
        ads1292::EventMarker{5.0, "marker", "mid",    2.0},
    };
}

ads1292::dsp::QualityGate make_quality_gate() {
    ads1292::dsp::QualityGate g;
    g.min_duration_seconds   = 12.0;
    g.min_contact_ok_percent = 90.0;
    g.min_r_peaks            = 7;
    g.min_hr_bpm             = 40.0;
    g.max_hr_bpm             = 160.0;
    g.require_qrs_clear      = false;
    g.max_baseline_drift_counts = 500.0;
    return g;
}

ads1292::RecordingProcessingSettings make_processing() {
    ads1292::RecordingProcessingSettings p;
    p.sample_rate_hz  = 500.0;
    p.ecg_inverted    = true;
    p.smoothing_window = 5;
    // gain must be one of the DISPLAY_GAIN_CHOICES = {0.5, 1.0, 2.0, 5.0};
    // use 5.0 as a distinctive value that survives normalization.
    p.display.gain    = 5.0;
    p.software_filters.notch_enabled = true;
    p.software_filters.notch_hz      = 50.0;
    return p;
}

// Write a bundle to a temp file; return the bundle json path.
std::string write_test_bundle(const std::string& stem) {
    auto tmp = fs::temp_directory_path() / (stem + ".json");
    auto bundle = ads1292::io::build_recording_bundle(
        (fs::temp_directory_path() / (stem + ".csv")).string(),
        make_metadata(),
        make_events(),
        make_calibration(),
        make_acquisition(),
        make_protocol(),
        make_quality_gate(),
        make_processing(),
        500.0, "2026-01-01T00:00:00Z");
    std::ofstream f(tmp);
    f << bundle.dump(2) << "\n";
    return tmp.string();
}

}  // namespace

// ===========================================================================
// recording_bundle_path
// ===========================================================================
TEST_CASE("recording_bundle_path replaces extension with .json", "[recording_bundle]") {
    REQUIRE(ads1292::io::recording_bundle_path("/x/rec.csv") == "/x/rec.json");
    REQUIRE(ads1292::io::recording_bundle_path("/x/rec.json") == "/x/rec.json");
    REQUIRE(ads1292::io::recording_bundle_path("/x/rec.h5")   == "/x/rec.json");
    REQUIRE(ads1292::io::recording_bundle_path("/x/no_ext")   == "/x/no_ext.json");
}

// ===========================================================================
// is_recording_bundle_path
// ===========================================================================
TEST_CASE("is_recording_bundle_path: true for a real bundle", "[recording_bundle]") {
    auto path = write_test_bundle("is_bundle_true");
    REQUIRE(ads1292::io::is_recording_bundle_path(path) == true);
}

TEST_CASE("is_recording_bundle_path: false for a plain metadata sidecar", "[recording_bundle]") {
    auto path = (fs::temp_directory_path() / "is_bundle_meta.json").string();
    ads1292::io::write_metadata_json(path, make_metadata());
    REQUIRE(ads1292::io::is_recording_bundle_path(path) == false);
}

TEST_CASE("is_recording_bundle_path: false for a plain quality-gate sidecar", "[recording_bundle]") {
    auto path = (fs::temp_directory_path() / "is_bundle_qg.json").string();
    ads1292::io::write_quality_gate_json(path, make_quality_gate());
    REQUIRE(ads1292::io::is_recording_bundle_path(path) == false);
}

TEST_CASE("is_recording_bundle_path: false for nonexistent file (no crash)", "[recording_bundle]") {
    REQUIRE(ads1292::io::is_recording_bundle_path("/does/not/exist/at/all.json") == false);
}

TEST_CASE("is_recording_bundle_path: false for malformed JSON", "[recording_bundle]") {
    auto path = (fs::temp_directory_path() / "is_bundle_bad.json").string();
    std::ofstream f(path);
    f << "{this is not valid JSON";
    REQUIRE(ads1292::io::is_recording_bundle_path(path) == false);
}

// ===========================================================================
// read_recording_bundle
// ===========================================================================
TEST_CASE("read_recording_bundle: accepts .json path directly", "[recording_bundle]") {
    auto path = write_test_bundle("read_direct");
    auto b = ads1292::io::read_recording_bundle(path);
    REQUIRE(b.is_object());
    REQUIRE(b.value("schema", std::string()) == "ads1292-recording-bundle-v1");
}

TEST_CASE("read_recording_bundle: maps .csv path to .json", "[recording_bundle]") {
    auto json_path = write_test_bundle("read_csv_map");
    // Give the .csv path — should resolve to the written .json
    auto csv_path = fs::path(json_path).replace_extension(".csv").string();
    auto b = ads1292::io::read_recording_bundle(csv_path);
    REQUIRE(b.value("schema", std::string()) == "ads1292-recording-bundle-v1");
}

TEST_CASE("read_recording_bundle: throws on nonexistent file", "[recording_bundle]") {
    REQUIRE_THROWS_AS(
        ads1292::io::read_recording_bundle("/nonexistent/bundle.json"),
        std::runtime_error);
}

TEST_CASE("read_recording_bundle: throws on wrong schema", "[recording_bundle]") {
    auto path = (fs::temp_directory_path() / "read_wrong_schema.json").string();
    ads1292::io::write_metadata_json(path, make_metadata());
    REQUIRE_THROWS_AS(
        ads1292::io::read_recording_bundle(path),
        std::runtime_error);
}

// ===========================================================================
// Extractor round-trips — all from a single written bundle
// ===========================================================================
TEST_CASE("metadata_from_bundle round-trip", "[recording_bundle]") {
    auto path = write_test_bundle("rt_metadata");
    auto b = ads1292::io::read_recording_bundle(path);
    auto m = ads1292::io::metadata_from_bundle(b);
    REQUIRE(m.session_id == "bundle-sess");
    REQUIRE(m.subject_id == "subj-42");
    REQUIRE(m.electrode  == "Ag/AgCl");
    REQUIRE(m.operator_  == "op1");
}

TEST_CASE("events_from_bundle round-trip", "[recording_bundle]") {
    auto path = write_test_bundle("rt_events");
    auto b = ads1292::io::read_recording_bundle(path);
    auto evs = ads1292::io::events_from_bundle(b);
    REQUIRE(evs.size() == 2);
    REQUIRE(evs[0].label == "start");
    REQUIRE(evs[0].timestamp_seconds == Approx(1.5));
    REQUIRE(evs[1].label == "marker");
    REQUIRE(evs[1].duration_seconds == Approx(2.0));
}

TEST_CASE("calibration_from_bundle round-trip", "[recording_bundle]") {
    auto path = write_test_bundle("rt_calibration");
    auto b = ads1292::io::read_recording_bundle(path);
    auto c = ads1292::io::calibration_from_bundle(b);
    REQUIRE(c.vref_mv  == Approx(2.42));
    REQUIRE(c.pga_gain == Approx(6.0));
    REQUIRE(c.adc_bits == 24);
    REQUIRE(c.label    == "test-cal");
}

TEST_CASE("acquisition_from_bundle round-trip", "[recording_bundle]") {
    auto path = write_test_bundle("rt_acquisition");
    auto b = ads1292::io::read_recording_bundle(path);
    auto a = ads1292::io::acquisition_from_bundle(b);
    REQUIRE(a.port            == "COM3");
    REQUIRE(a.sample_rate_hz  == Approx(500.0));
    REQUIRE(a.acquisition_mode == "live_stream");
}

TEST_CASE("protocol_from_bundle round-trip", "[recording_bundle]") {
    auto path = write_test_bundle("rt_protocol");
    auto b = ads1292::io::read_recording_bundle(path);
    auto p = ads1292::io::protocol_from_bundle(b);
    REQUIRE(p.name == "round-trip protocol");
    REQUIRE(p.steps.size() == 2);
    REQUIRE(p.steps[0].start_seconds    == Approx(5.0));
    REQUIRE(p.steps[0].duration_seconds == Approx(20.0));
    REQUIRE(p.steps[0].label            == "rest");
    REQUIRE(p.steps[0].instruction      == "sit still");
    REQUIRE(p.steps[1].label            == "motion");
}

TEST_CASE("quality_gate_from_bundle round-trip", "[recording_bundle]") {
    auto path = write_test_bundle("rt_quality_gate");
    auto b = ads1292::io::read_recording_bundle(path);
    auto g = ads1292::io::quality_gate_from_bundle(b);
    REQUIRE(g.min_duration_seconds   == Approx(12.0));
    REQUIRE(g.min_contact_ok_percent == Approx(90.0));
    REQUIRE(g.min_r_peaks            == 7);
    REQUIRE(g.min_hr_bpm             == Approx(40.0));
    REQUIRE(g.max_hr_bpm             == Approx(160.0));
    REQUIRE(g.require_qrs_clear      == false);
    REQUIRE(g.max_baseline_drift_counts.has_value());
    REQUIRE(g.max_baseline_drift_counts.value() == Approx(500.0));
    REQUIRE_FALSE(g.max_noise_rms_counts.has_value());
    REQUIRE_FALSE(g.max_peak_to_peak_counts.has_value());
}

TEST_CASE("processing_from_bundle round-trip", "[recording_bundle]") {
    auto path = write_test_bundle("rt_processing");
    auto b = ads1292::io::read_recording_bundle(path);
    auto p = ads1292::io::processing_from_bundle(b);
    REQUIRE(p.sample_rate_hz  == Approx(500.0));
    REQUIRE(p.ecg_inverted    == true);
    REQUIRE(p.smoothing_window == 5);
    REQUIRE(p.display.gain    == Approx(5.0));
    REQUIRE(p.software_filters.notch_enabled == true);
    REQUIRE(p.software_filters.notch_hz      == Approx(50.0));
}
