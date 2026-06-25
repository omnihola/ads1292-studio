// tests/cpp/test_processing_io.cpp
#include "catch.hpp"
#include "ads1292/io/ProcessingIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }
TEST_CASE("read golden processing.json", "[sidecar]") {
  auto p = io::read_processing_json(fx("processing.json"));
  REQUIRE(p.schema == "ads1292-processing-settings-v1");
  REQUIRE(p.sample_rate_hz == Approx(500.0));
  REQUIRE(p.smoothing_window == 11);
  REQUIRE(p.display.time_window_seconds == Approx(8.0));
  REQUIRE(p.software_filters.notch_hz == Approx(60.0));
  REQUIRE(p.processing_notes == "display settings only; raw CSV samples are unchanged");
}
TEST_CASE("processing round-trips + normalizes smoothing", "[sidecar]") {
  RecordingProcessingSettings p; p.sample_rate_hz=-1; p.smoothing_window=0; p.schema="  ";
  auto n = p.normalized();
  REQUIRE(n.sample_rate_hz == Approx(500.0)); REQUIRE(n.smoothing_window == 1);
  REQUIRE(n.schema == "ads1292-processing-settings-v1");
  auto path = (std::filesystem::temp_directory_path()/"p7b2_proc.json").string();
  io::write_processing_json(path, io::build_processing_settings());
  REQUIRE(io::read_processing_json(path).smoothing_window == 11);
}
