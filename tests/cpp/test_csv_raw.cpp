// tests/cpp/test_csv_raw.cpp
#include "catch.hpp"
#include "ads1292/io/CsvIo.h"
#include "ads1292/model/Calibration.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {
std::string read_file(const std::string& path) {
  std::ifstream in(path, std::ios::binary);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}
const std::string kRawCsv = std::string(FIXTURE_DIR) + "/files/raw_recording.csv";
}  // namespace

TEST_CASE("read_raw_recording_csv parses the golden raw CSV", "[csv]") {
  auto samples = ads1292::io::read_raw_recording_csv(kRawCsv);
  REQUIRE(samples.size() == 50);
  REQUIRE(samples[0].sample_index == 0);
  REQUIRE(samples[0].ch1_uv.has_value());
}

TEST_CASE("raw CSV round-trips to byte-identical output", "[csv]") {
  auto samples = ads1292::io::read_raw_recording_csv(kRawCsv);
  const std::string out = std::string(FIXTURE_DIR) + "/files/_rt_raw.csv";
  ads1292::io::write_raw_recording_csv(out, samples, ads1292::Calibration());
  REQUIRE(read_file(out) == read_file(kRawCsv));
  std::remove(out.c_str());
}
