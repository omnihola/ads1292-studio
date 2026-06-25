// tests/cpp/test_acquisition_io.cpp
#include "catch.hpp"
#include "ads1292/io/AcquisitionIo.h"
#include <filesystem>
using namespace ads1292::io;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }
TEST_CASE("read golden acquisition.json", "[sidecar]") {
  auto a = read_acquisition_json(fx("acquisition.json"));
  REQUIRE(a.schema == "ads1292-acquisition-provenance-v1");
  REQUIRE(a.csv_name == "rec.csv");
  REQUIRE(a.csv_schema == "ads1292-studio-live-stream-v1");
  REQUIRE(a.acquisition_mode == "live_stream");
  REQUIRE(a.port == "/dev/ttyUSB0");
  REQUIRE(a.channel_map.at("ch2_counts") == "CH2 ECG Lead I (LA-RA)");
  REQUIRE(a.csv_columns.size() >= 3);
  REQUIRE(a.csv_columns[0].name == "timestamp");
}
TEST_CASE("acquisition normalized fills channel_map default + round-trips", "[sidecar]") {
  AcquisitionProvenance a; a.csv_name="x.csv"; a.acquisition_mode="live_stream"; // empty channel_map
  auto n = a.normalized();
  REQUIRE_FALSE(n.channel_map.empty());            // defaults filled
  REQUIRE(n.csv_schema == "ads1292-studio-live-stream-v1");
  auto path = (std::filesystem::temp_directory_path()/"p7b2_acq.json").string();
  write_acquisition_json(path, n);
  auto back = read_acquisition_json(path);
  REQUIRE(back.csv_name == "x.csv");
  REQUIRE(back.channel_map.size() == n.channel_map.size());
}
