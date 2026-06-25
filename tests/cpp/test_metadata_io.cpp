// tests/cpp/test_metadata_io.cpp
#include "catch.hpp"
#include "ads1292/io/MetadataIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }

TEST_CASE("read golden metadata.json", "[sidecar]") {
  auto m = io::read_metadata_json(fx("metadata.json"));
  REQUIRE(m.session_id == "YYYYMMDD-run-001");
  REQUIRE(m.subject_id == "anonymous");
  REQUIRE(m.montage == "RA/LA/RL torso");
  REQUIRE(m.operator_ == "unspecified operator");   // template's "" normalized to fallback
  REQUIRE(m.acquisition_mode == "live_stream");
}
TEST_CASE("metadata round-trips", "[sidecar]") {
  SessionMetadata m; m.session_id="s1"; m.subject_id="subj"; m.electrode="e"; m.operator_="op"; m.notes="  n  ";
  auto p = (std::filesystem::temp_directory_path() / "p7b_meta.json").string();
  io::write_metadata_json(p, m);
  auto back = io::read_metadata_json(p);
  REQUIRE(back.session_id == "s1");
  REQUIRE(back.notes == "n");                        // trimmed
  REQUIRE(back.operator_ == "op");
  REQUIRE(back.montage == "RA/LA/RL torso");
}
TEST_CASE("metadata_template normalizes operator", "[sidecar]") {
  auto t = io::metadata_template();
  REQUIRE(io::read_metadata_json([&]{ auto p=(std::filesystem::temp_directory_path()/"p7b_tmpl.json").string(); io::write_metadata_json(p,t); return p; }()).operator_ == "unspecified operator");
}
