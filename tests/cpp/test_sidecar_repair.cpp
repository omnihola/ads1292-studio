// tests/cpp/test_sidecar_repair.cpp
// Task 1 tests: sidecar completion plan + quality_gate JSON.
#include "catch.hpp"
#include "ads1292/io/SidecarRepair.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/index/SessionIndexRow.h"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iterator>
using namespace ads1292;

TEST_CASE("build_sidecar_completion_plan rows from missing sidecars", "[repair]") {
  index::SessionIndexRow row;
  row.path = "/data/rec1.csv"; row.relative_path = "rec1.csv";
  row.session_id = "run-1"; row.missing_sidecars = "calibration;processing";
  auto plan = io::build_sidecar_completion_plan({row}, "/tmp/templates");
  REQUIRE(plan.size() == 2);
  REQUIRE(plan[0].sidecar == "calibration");
  REQUIRE(plan[0].target_path == "/data/rec1.calibration.json");
  REQUIRE(plan[0].template_path == "/tmp/templates/rec1.calibration.json");
  REQUIRE(plan[0].suggested_action == "Create calibration sidecar");
  REQUIRE(plan[1].sidecar == "processing");
}

TEST_CASE("quality_gate label + processing label use spaces", "[repair]") {
  index::SessionIndexRow row; row.path="/d/r.csv"; row.relative_path="r.csv"; row.missing_sidecars="quality_gate";
  auto plan = io::build_sidecar_completion_plan({row}, "/tmp/t");
  REQUIRE(plan[0].target_path == "/d/r.quality-gate.json");
  REQUIRE(plan[0].suggested_action == "Create quality gate sidecar");   // '_'->' '
}

TEST_CASE("write_quality_gate_json round-trips defaults", "[repair]") {
  auto p = (std::string(SCRATCH_OR_TMP) + "/p7b_qg.json");   // use std::filesystem::temp_directory_path()
  io::write_quality_gate_json(p, io::quality_gate_template());
  std::ifstream f(p); std::string s((std::istreambuf_iterator<char>(f)), {});
  REQUIRE(s.find("\"min_duration_seconds\": 8.0") != std::string::npos);
  REQUIRE(s.find("\"require_qrs_clear\": true") != std::string::npos);
  REQUIRE(s.find("\"max_noise_rms_counts\": null") != std::string::npos);   // unset optional -> null
}
