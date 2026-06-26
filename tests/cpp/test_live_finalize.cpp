// tests/cpp/test_live_finalize.cpp
// Tests for ads1292::io::finalize_live_recording (P11 Task 1).
//
// Requires HDF5 (compiled only when ADS1292_BUILD_HDF5 is set).
// Tests:
//   1. Round-trip: write CSV -> finalize -> bundle exists, is_recording_bundle_path,
//      metadata round-trips, H5 file exists.
//   2. Empty-capture: 0-sample CSV -> finalize returns wrote==false, no sidecar.
//   3. (P11.8 Task 3) write_xlsx=true -> xlsx_path non-empty + file exists.
//   4. (P11.8 Task 3) write_xlsx=false -> xlsx_path empty + no .xlsx file.

#include "catch.hpp"
#include "ads1292/io/LiveRecordingFinalize.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/RecordingBundle.h"
#include "ads1292/io/ProtocolIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/dsp/LiveCalibration.h"
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/EventMarker.h"
#include <filesystem>
#include <cstdlib>
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

// ── P11.8 Task 3: finalize_live_recording + write_xlsx wiring ────────────────

TEST_CASE("finalize_live_recording: write_xlsx=true writes xlsx file", "[live_finalize][xlsx]") {
  auto tmp = temp_dir();
  auto csv = tmp / "rec_xlsx_on.csv";

  auto samples = make_samples(20);
  ads1292::io::write_recording_csv(csv.string(), samples);

  // Build one EventMarker
  ads1292::EventMarker ev;
  ev.timestamp_seconds = 0.1;
  ev.label = "test-event";
  ev.notes = "xlsx-test";

  ads1292::io::FinalizeOptions opt;
  opt.write_xlsx       = true;
  opt.write_h5         = false;   // no HDF5 dependency needed for this test
  opt.events           = {ev};
  opt.sample_rate_hz   = 500.0;

  auto r = ads1292::io::finalize_live_recording(csv.string(), opt);

  REQUIRE(r.wrote);
  REQUIRE(!r.xlsx_path.empty());
  REQUIRE(fs::exists(r.xlsx_path));

  // Verify the XLSX is a real ZIP containing the Events sheet
  {
    std::string cmd = "unzip -l '" + r.xlsx_path + "' 2>&1 | grep -q 'xl/worksheets/sheet1.xml'";
    int rc = std::system(cmd.c_str());
    REQUIRE(rc == 0);
  }
}

TEST_CASE("finalize_live_recording: write_xlsx=false leaves xlsx_path empty", "[live_finalize][xlsx]") {
  auto tmp = temp_dir();
  auto csv = tmp / "rec_xlsx_off.csv";

  auto samples = make_samples(20);
  ads1292::io::write_recording_csv(csv.string(), samples);

  ads1292::io::FinalizeOptions opt;
  opt.write_xlsx     = false;
  opt.write_h5       = false;

  auto r = ads1292::io::finalize_live_recording(csv.string(), opt);

  REQUIRE(r.wrote);
  REQUIRE(r.xlsx_path.empty());

  // No .xlsx file should exist alongside the CSV
  auto expected_xlsx = fs::path(csv).replace_extension(".xlsx");
  REQUIRE_FALSE(fs::exists(expected_xlsx));
}

// ── P11.9 Task 2: live_calibration wired into the bundle ─────────────────────

TEST_CASE("finalize_live_recording: live_calibration written into bundle acquisition section",
          "[live_finalize][calibrate]") {
  // Verify that FinalizeOptions.live_calibration, when set, is serialized into
  // the bundle's acquisition.live_calibration JSON object with the 6 correct keys
  // matching Python's _live_calibration_entry() dict.
  auto tmp = temp_dir();
  auto csv = tmp / "rec_live_cal.csv";

  auto samples = make_samples(10);
  ads1292::io::write_recording_csv(csv.string(), samples);

  // Build a known calibration value
  ads1292::LiveStreamCalibration cal;
  cal.mean_uv_per_count = 0.0481;
  cal.std_uv_per_count  = 0.001;
  cal.cv_percent        = 2.0;
  cal.runs              = 5;
  cal.test_signal_pp_uv = 2016.666;
  cal.scale_type        = "live_processed";

  ads1292::io::FinalizeOptions opt;
  opt.live_calibration = cal;
  opt.write_h5         = false;  // no HDF5 dependency needed for this test

  auto r = ads1292::io::finalize_live_recording(csv.string(), opt);

  REQUIRE(r.wrote);
  REQUIRE(fs::exists(r.bundle_path));

  // Read back the bundle and extract the acquisition section
  auto bundle = ads1292::io::read_recording_bundle(r.bundle_path);
  auto acq    = ads1292::io::acquisition_from_bundle(bundle);

  // live_calibration must be a non-empty JSON object with the expected keys
  REQUIRE(acq.live_calibration.is_object());
  REQUIRE_FALSE(acq.live_calibration.empty());
  REQUIRE(acq.live_calibration.contains("mean_uv_per_count"));
  REQUIRE(acq.live_calibration["mean_uv_per_count"].get<double>() == Approx(0.0481));
  REQUIRE(acq.live_calibration.contains("scale_type"));
  REQUIRE(acq.live_calibration["scale_type"].get<std::string>() == "live_processed");
  REQUIRE(acq.live_calibration.contains("runs"));
  REQUIRE(acq.live_calibration["runs"].get<int>() == 5);
}

TEST_CASE("finalize_live_recording: live_calibration absent when not set",
          "[live_finalize][calibrate]") {
  // Verify that when live_calibration is not set, the bundle's acquisition
  // section has an empty live_calibration object (the default).
  auto tmp = temp_dir();
  auto csv = tmp / "rec_no_cal.csv";

  auto samples = make_samples(10);
  ads1292::io::write_recording_csv(csv.string(), samples);

  ads1292::io::FinalizeOptions opt;
  // live_calibration not set (std::nullopt)
  opt.write_h5 = false;

  auto r = ads1292::io::finalize_live_recording(csv.string(), opt);

  REQUIRE(r.wrote);

  auto bundle = ads1292::io::read_recording_bundle(r.bundle_path);
  auto acq    = ads1292::io::acquisition_from_bundle(bundle);

  // Default: live_calibration is an empty JSON object
  REQUIRE(acq.live_calibration.is_object());
  REQUIRE(acq.live_calibration.empty());
}
