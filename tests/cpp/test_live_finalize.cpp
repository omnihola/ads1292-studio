// tests/cpp/test_live_finalize.cpp
// Tests for ads1292::io::finalize_live_recording (P11 Task 1).
//
// Requires HDF5 (compiled only when ADS1292_BUILD_HDF5 is set).
// Tests:
//   1. Round-trip: write CSV -> finalize -> bundle exists, is_recording_bundle_path,
//      metadata round-trips, H5 file exists.
//   2. Empty-capture: 0-sample CSV -> finalize returns wrote==false, no sidecar.

#include "catch.hpp"
#include "ads1292/io/LiveRecordingFinalize.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/RecordingBundle.h"
#include "ads1292/io/ProtocolIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/model/StreamSample.h"
#include <filesystem>
#include <vector>

namespace fs = std::filesystem;

namespace {

std::vector<ads1292::StreamSample> make_samples(int count) {
  std::vector<ads1292::StreamSample> samples;
  samples.reserve(static_cast<std::size_t>(count));
  for (int i = 0; i < count; ++i) {
    ads1292::StreamSample s;
    s.timestamp    = i / 500.0;
    s.ch1          = 100 + i;
    s.ch2          = 200 + i;
    s.status_byte  = 0;
    s.sample_index = i;
    samples.push_back(s);
  }
  return samples;
}

fs::path temp_dir() {
  auto p = fs::path(SCRATCH_OR_TMP) / "test_live_finalize";
  fs::create_directories(p);
  return p;
}

}  // namespace

TEST_CASE("finalize_live_recording: round-trip write, bundle, and H5", "[live_finalize]") {
  auto tmp = temp_dir();
  auto csv = tmp / "rec.csv";

  auto samples = make_samples(10);
  ads1292::io::write_recording_csv(csv.string(), samples);

  ads1292::io::FinalizeOptions opt;
  opt.metadata.session_id = "live-test";
  opt.protocol            = ads1292::io::protocol_template();
  opt.quality_gate        = ads1292::io::quality_gate_template();
  opt.write_h5            = true;

  auto r = ads1292::io::finalize_live_recording(csv.string(), opt);

  // Wrote flag + sample count
  REQUIRE(r.wrote);
  REQUIRE(r.sample_count == static_cast<int>(samples.size()));
  REQUIRE(r.csv_path == csv.string());

  // Bundle sidecar exists and is recognized
  REQUIRE(fs::exists(r.bundle_path));
  REQUIRE(ads1292::io::is_recording_bundle_path(r.bundle_path));

  // Metadata round-trips through the bundle
  auto bundle = ads1292::io::read_recording_bundle(r.bundle_path);
  REQUIRE(ads1292::io::metadata_from_bundle(bundle).session_id == "live-test");

  // HDF5 file exists
  REQUIRE(fs::exists(r.h5_path));
}

TEST_CASE("finalize_live_recording: empty capture skips all output", "[live_finalize]") {
  auto tmp = temp_dir();
  auto csv = tmp / "empty_rec.csv";

  // Write a CSV with 0 data samples (header only).
  ads1292::io::write_recording_csv(csv.string(), {});

  ads1292::io::FinalizeOptions opt;
  opt.write_h5 = true;

  auto r = ads1292::io::finalize_live_recording(csv.string(), opt);

  // Must not report success
  REQUIRE_FALSE(r.wrote);
  REQUIRE(r.sample_count == 0);

  // No .json bundle must have been written next to the CSV
  auto expected_bundle = fs::path(csv).replace_extension(".json");
  REQUIRE_FALSE(fs::exists(expected_bundle));

  // If the result carries a bundle path, it must not exist either
  if (!r.bundle_path.empty()) {
    REQUIRE_FALSE(fs::exists(r.bundle_path));
  }
}
