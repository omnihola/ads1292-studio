// tests/cpp/test_h5_write.cpp
#include "catch.hpp"
#include "ads1292/io/H5Io.h"
#include "ads1292/crypto/Sha256.h"
#include "nlohmann/json.hpp"
#include <cstdio>
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

TEST_CASE("write_recording_h5 round-trips to a structurally-golden file", "[h5]") {
  const std::string src = std::string(FIXTURE_DIR) + "/files/recording.h5";
  const std::string out = std::string(FIXTURE_DIR) + "/files/_rt.h5";

  io::H5Recording rec = io::read_recording_h5(src);
  io::write_recording_h5(out, rec.samples, rec.bundle_json, rec.attrs);

  // the written file verifies (native-dtype integrity hashes recomputed & matched)
  io::H5Verification v = io::verify_recording_h5(out);
  REQUIRE(v.ok);
  REQUIRE(v.failures.empty());

  // its structure (re-read float64 dataset hashes) matches the golden sidecar
  io::H5Recording rt = io::read_recording_h5(out);
  json sc = sidecar();
  std::vector<double> ts;
  for (const auto& s : rt.samples) ts.push_back(s.timestamp);
  REQUIRE(io::dataset_float64_sha256(ts) ==
          sc.at("datasets").at("samples/timestamp").at("sha256").get<std::string>());
  REQUIRE(rt.attrs.csv_name == "live_recording.csv");
  REQUIRE(rt.bundle_json == rec.bundle_json);  // bundle_json written back verbatim

  std::remove(out.c_str());
}

TEST_CASE("verify_recording_h5 validates the committed golden file", "[h5]") {
  const std::string golden = std::string(FIXTURE_DIR) + "/files/recording.h5";
  io::H5Verification v = io::verify_recording_h5(golden);
  // All failures are shown if any
  for (const auto& f : v.failures) {
    WARN("Integrity failure: " << f);
  }
  REQUIRE(v.ok == true);
  REQUIRE(v.checked == 6);
}
