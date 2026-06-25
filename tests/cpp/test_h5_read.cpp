// tests/cpp/test_h5_read.cpp
#include "catch.hpp"
#include "ads1292/io/H5Io.h"
#include "ads1292/crypto/Sha256.h"
#include "nlohmann/json.hpp"
#include <fstream>
#include <vector>

using nlohmann::json;
using namespace ads1292;

namespace {
json sidecar() {
  std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_h5_sidecar.json");
  json j; in >> j; return j;
}
}  // namespace

TEST_CASE("read_recording_h5 matches the golden sidecar", "[h5]") {
  const std::string h5 = std::string(FIXTURE_DIR) + "/files/recording.h5";
  io::H5Recording rec = io::read_recording_h5(h5);
  json sc = sidecar();

  // attrs
  REQUIRE(rec.attrs.schema == sc.at("attrs").at("schema").get<std::string>());
  REQUIRE(rec.attrs.csv_name == sc.at("attrs").at("csv_name").get<std::string>());
  REQUIRE(rec.attrs.sample_count == sc.at("attrs").at("sample_count").get<std::string>());

  // sample count matches the attr
  REQUIRE(rec.samples.size() == 50);

  // float64-canonical hash of the timestamp dataset matches the sidecar
  std::vector<double> ts;
  for (const auto& s : rec.samples) ts.push_back(s.timestamp);
  REQUIRE(io::dataset_float64_sha256(ts) ==
          sc.at("datasets").at("samples/timestamp").at("sha256").get<std::string>());

  // ch1 dataset (read as int, hashed as float64) matches the sidecar
  std::vector<double> ch1;
  for (const auto& s : rec.samples) ch1.push_back(static_cast<double>(s.ch1));
  REQUIRE(io::dataset_float64_sha256(ch1) ==
          sc.at("datasets").at("samples/ch1").at("sha256").get<std::string>());

  // the bundle_json dataset parses as a valid bundle
  json bundle = json::parse(rec.bundle_json);
  REQUIRE(bundle.contains("schema"));
}
