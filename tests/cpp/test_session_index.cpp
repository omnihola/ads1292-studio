// tests/cpp/test_session_index.cpp
#include "catch.hpp"
#include "ads1292/io/SessionIndexScan.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/model/StreamSample.h"
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
