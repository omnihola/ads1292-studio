// tests/cpp/test_batch.cpp
#include "catch.hpp"
#include "ads1292/io/BatchScan.h"
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

TEST_CASE("aggregate_recordings + group_by_electrode", "[batch]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b3_batch";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  // two recordings, same electrode via metadata
  std::vector<std::string> paths;
  for (auto stem : {"a","b"}) {
    std::vector<StreamSample> rec;
    for (int i=0;i<5000;++i){ StreamSample s; double t=i/500.0,v=0.0; for(double bt=0.2;bt<10.0;bt+=60.0/72.0){double d=t-bt; v+=300.0*std::exp(-(d*d)/(2*0.01*0.01));} s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s);}
    auto p=(dir/(std::string(stem)+".csv")).string(); io::write_recording_csv(p, rec);
    SessionMetadata m; m.electrode="MOTAC"; io::write_metadata_json((dir/(std::string(stem)+".json")).string(), m);
    paths.push_back(p);
  }
  auto rows = io::aggregate_recordings(paths);
  REQUIRE(rows.size() == 2);
  REQUIRE(rows[0].electrode == "MOTAC");
  auto groups = index::group_recordings_by_electrode(rows);
  REQUIRE(groups.size() == 1);
  REQUIRE(groups[0].electrode == "MOTAC");
  REQUIRE(groups[0].recordings == 2);
  REQUIRE(groups[0].mean_r_peaks > 0.0);
}

TEST_CASE("aggregate_recordings reads bundle-backed recording metadata", "[batch][bundle]") {
  auto dir = std::filesystem::temp_directory_path() / "p10_batch_bundle";
  std::filesystem::remove_all(dir);
  std::filesystem::create_directories(dir);

  // Write a synthetic ECG recording CSV.
  std::vector<StreamSample> rec;
  for (int i = 0; i < 5000; ++i) {
    StreamSample s;
    double t = i / 500.0, v = 0.0;
    for (double bt = 0.2; bt < 10.0; bt += 60.0 / 72.0) {
      double d = t - bt;
      v += 300.0 * std::exp(-(d * d) / (2 * 0.01 * 0.01));
    }
    s.ch2 = (int)v; s.ch1 = 0; s.status_byte = 0;
    rec.push_back(s);
  }
  auto csv_path = (dir / "bundle_rec.csv").string();
  io::write_recording_csv(csv_path, rec);

  // Write a recording bundle alongside the csv (replaces the plain metadata sidecar).
  SessionMetadata meta;
  meta.session_id = "bundle-sess";
  meta.electrode  = "MOTAC";

  std::vector<EventMarker> events;
  io::write_recording_bundle(
      csv_path, meta, events,
      Calibration{},
      io::AcquisitionProvenance{},
      TestProtocol{},
      dsp::QualityGate{},
      RecordingProcessingSettings{},
      500.0, "2024-01-01T00:00:00Z");

  auto rows = io::aggregate_recordings({csv_path});
  REQUIRE(rows.size() == 1);
  // Bundle metadata path: must see the distinctive session_id, NOT the default.
  REQUIRE(rows[0].session_id == "bundle-sess");
  REQUIRE(rows[0].electrode  == "MOTAC");
}
