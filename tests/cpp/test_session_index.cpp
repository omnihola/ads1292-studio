// tests/cpp/test_session_index.cpp
#include "catch.hpp"
#include "ads1292/io/SessionIndexScan.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/Bundle.h"
#include "ads1292/io/AcquisitionIo.h"
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/EventMarker.h"
#include "ads1292/model/TestProtocol.h"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/model/RecordingProcessingSettings.h"
#include <filesystem>
#include <cmath>
using namespace ads1292;
namespace {
std::string make_clean_recording(const std::filesystem::path& dir, const std::string& stem) {
  std::vector<StreamSample> rec;
  for (int i=0;i<5000;++i){ StreamSample s; double t=i/500.0, v=0.0;
    for(double bt=0.2; bt<10.0; bt+=60.0/72.0){ double d=t-bt; v+=300.0*std::exp(-(d*d)/(2*0.01*0.01)); }
    s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s); }
  auto p = (dir / (stem + ".csv")).string();
  io::write_recording_csv(p, rec); return p;
}
}
TEST_CASE("scan_recording_directory builds rows + summary", "[index]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b3_idx";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  auto csv = make_clean_recording(dir, "rec1");
  // give rec1 a metadata sidecar so some sidecar status is exercised
  SessionMetadata m; m.session_id="run-1"; m.subject_id="subj-A"; io::write_metadata_json((dir/"rec1.json").string(), m);
  auto rows = io::scan_recording_directory(dir.string());
  REQUIRE(rows.size() == 1);
  REQUIRE(rows[0].relative_path == "rec1.csv");
  REQUIRE(rows[0].session_id == "run-1");
  REQUIRE(rows[0].r_peaks >= 5);
  REQUIRE(rows[0].quality_label.size() > 0);
  // sidecar_status: only metadata present -> missing the others
  REQUIRE(rows[0].sidecar_status == "missing");
  REQUIRE(rows[0].missing_sidecars.find("calibration") != std::string::npos);
  // derived fields for missing-sidecar case
  REQUIRE(rows[0].package_ready_status == "incomplete_record");
  REQUIRE(rows[0].next_action == "complete_sidecars");
  // manifest absent -> "missing"
  REQUIRE(rows[0].recording_manifest_status == "missing");
  auto sum = index::summarize_rows(rows);
  REQUIRE(sum.recordings == 1);
  REQUIRE(sum.recording_manifest_missing == 1);
  // export json round-trips structurally (no crash, file written)
  auto out = (dir / "index.json").string();
  io::write_session_index_json(out, rows, sum);
  REQUIRE(std::filesystem::exists(out));
}

TEST_CASE("scan_recording_directory reads bundle-backed recording correctly", "[index][bundle]") {
  // Step 1: Build a recording directory with rec.csv + rec.json that IS a bundle.
  auto dir = std::filesystem::temp_directory_path() / "p10_idx_bundle";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir);

  // Write rec.csv with a few synthetic ECG samples.
  auto csv_path = make_clean_recording(dir, "rec");

  // Build a bundle with distinctive metadata: session_id="bundle-sess", electrode="MOTAC".
  SessionMetadata meta;
  meta.session_id = "bundle-sess";
  meta.electrode  = "MOTAC";
  meta.subject_id = "subj-bundle";

  std::vector<EventMarker> events;  // no events
  io::write_recording_bundle(
      csv_path, meta, events,
      Calibration{},
      io::AcquisitionProvenance{},
      TestProtocol{},
      dsp::QualityGate{},
      RecordingProcessingSettings{},
      500.0, "2024-01-01T00:00:00Z");

  // Step 2: Scan the directory and locate the row for rec.csv.
  auto rows = io::scan_recording_directory(dir.string());
  REQUIRE(rows.size() == 1);

  const auto& row = rows[0];

  // Bundle metadata path: must see the distinctive session_id and electrode, NOT defaults.
  REQUIRE(row.session_id == "bundle-sess");
  REQUIRE(row.electrode  == "MOTAC");

  // Bundle sidecar_status short-circuit: the bundle carries all 7 categories.
  REQUIRE(row.sidecar_status   == "complete");
  REQUIRE(row.missing_sidecars == "");
}

TEST_CASE("scan_recording_directory populates event + completion from bundle", "[index][bundle]") {
  // Proves P10 bundle short-circuits for _event_summary_for and _completion_summary_for.
  // Before the fix these fields were 0/"unknown" because the code fell through
  // to nonexistent individual sidecar files.
  auto dir = std::filesystem::temp_directory_path() / "p10_idx_bundle_evcomp";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir);

  auto csv_path = make_clean_recording(dir, "rec");

  // Two events: one point (duration == 0) and one interval (duration > 0).
  std::vector<EventMarker> events;
  EventMarker e1;
  e1.label             = "marker";
  e1.timestamp_seconds = 0.5;
  e1.duration_seconds  = 0.0;  // point event
  events.push_back(e1);

  EventMarker e2;
  e2.label             = "segment";
  e2.timestamp_seconds = 1.0;
  e2.duration_seconds  = 2.0;  // interval event
  events.push_back(e2);

  // Acquisition with a filled completion block.
  io::AcquisitionProvenance acq;
  acq.completion = {
      {"status",              "finalized"},
      {"sample_count",        1500},
      {"sample_span_seconds", 3.0}
  };

  SessionMetadata meta;
  meta.session_id = "bundle-evcomp";

  io::write_recording_bundle(
      csv_path, meta, events,
      Calibration{},
      acq,
      TestProtocol{},
      dsp::QualityGate{},
      RecordingProcessingSettings{},
      500.0, "2024-01-01T00:00:00Z");

  auto rows = io::scan_recording_directory(dir.string());
  REQUIRE(rows.size() == 1);

  const auto& row = rows[0];

  // Event summary must come from the bundle (not from a nonexistent .events.json).
  REQUIRE(row.event_count          == 2);
  REQUIRE(row.interval_event_count == 1);

  // Completion summary must come from the bundle (not from a nonexistent .acquisition.json).
  REQUIRE(row.completion_status      == "finalized");
  REQUIRE(row.recorded_sample_count  == 1500);
}
