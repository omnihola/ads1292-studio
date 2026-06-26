// tests/cpp/test_sidecar_repair.cpp
// Task 1+2 tests: sidecar completion plan, quality_gate JSON,
//                 template bundle, and apply script.
#include "catch.hpp"
#include "ads1292/io/SidecarRepair.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/io/CalibrationIo.h"
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

// --- Task 2: template bundle + apply script ---

TEST_CASE("write_sidecar_template_bundle writes parseable template sidecars", "[repair]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b_bundle";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  index::SessionIndexRow row;
  row.path = (dir / "rec1.csv").string();
  row.relative_path = "rec1.csv";
  row.session_id = "run-1";
  row.subject_id = "subjA";
  row.missing_sidecars = "metadata;calibration;quality_gate;processing;protocol;events;acquisition";
  auto written = io::write_sidecar_template_bundle((dir / "templates").string(), {row});
  REQUIRE(written.size() == 7);
  // the metadata template carries the row's session_id + the review note
  auto meta = ads1292::io::read_metadata_json((dir / "templates" / "rec1.json").string());
  REQUIRE(meta.session_id == "run-1");
  // the calibration template parses to defaults
  auto cal = ads1292::io::read_calibration_json((dir / "templates" / "rec1.calibration.json").string());
  REQUIRE(cal.label == "ADS1292 default");
}

TEST_CASE("write_sidecar_apply_script emits a cp -n script", "[repair]") {
  index::SessionIndexRow row;
  row.path = "/data/rec1.csv";
  row.relative_path = "rec1.csv";
  row.missing_sidecars = "calibration";
  auto plan = io::build_sidecar_completion_plan({row}, "/tmp/templates");
  auto sp = (std::filesystem::temp_directory_path() / "p7b_apply.sh").string();
  io::write_sidecar_apply_script(sp, plan);
  std::ifstream f(sp); std::string s((std::istreambuf_iterator<char>(f)), {});
  REQUIRE(s.rfind("#!/bin/sh", 0) == 0);
  REQUIRE(s.find("set -eu") != std::string::npos);
  REQUIRE(s.find("cp -n") != std::string::npos);
  REQUIRE(s.find("rec1.csv: calibration") != std::string::npos);
}

TEST_CASE("write_sidecar_apply_script with no missing prints the echo", "[repair]") {
  auto sp = (std::filesystem::temp_directory_path() / "p7b_apply_empty.sh").string();
  io::write_sidecar_apply_script(sp, {});
  std::ifstream f(sp); std::string s((std::istreambuf_iterator<char>(f)), {});
  REQUIRE(s.find("No missing sidecars to apply.") != std::string::npos);
}
