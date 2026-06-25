// tests/cpp/test_csv_live.cpp
#include "catch.hpp"
#include "ads1292/io/CsvIo.h"
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
const std::string kLiveCsv = std::string(FIXTURE_DIR) + "/files/live_recording.csv";
}  // namespace

TEST_CASE("read_recording_csv parses the golden live CSV", "[csv]") {
  auto samples = ads1292::io::read_recording_csv(kLiveCsv);
  REQUIRE(samples.size() == 50);
  // first data row of the golden file: timestamp 0.000000, sample_index 0
  REQUIRE(samples[0].timestamp == Approx(0.0).margin(1e-9));
  REQUIRE(samples[0].sample_index.has_value());
  REQUIRE(samples[0].sample_index.value() == 0);
}

TEST_CASE("live CSV round-trips to byte-identical output", "[csv]") {
  auto samples = ads1292::io::read_recording_csv(kLiveCsv);
  const std::string out = std::string(FIXTURE_DIR) + "/files/_rt_live.csv";
  ads1292::io::write_recording_csv(out, samples);
  REQUIRE(read_file(out) == read_file(kLiveCsv));
  std::remove(out.c_str());
}
