// tests/cpp/test_protocol_io.cpp
#include "catch.hpp"
#include "ads1292/io/ProtocolIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }
TEST_CASE("read golden protocol.json", "[sidecar]") {
  auto p = io::read_protocol_json(fx("protocol.json"));
  REQUIRE(p.name == "MOTAC ECG validation");
  REQUIRE(p.steps.size() == 3);
  REQUIRE(p.steps[0].label == "baseline");
  REQUIRE(p.steps[1].start_seconds == Approx(30.0));
  REQUIRE(p.steps[2].label == "recovery");
}
TEST_CASE("protocol round-trips + step normalize", "[sidecar]") {
  TestProtocol p; p.name="  "; p.steps = { ProtocolStep{-1.0, -2.0, "", ""} };
  auto n = p.normalized();
  REQUIRE(n.name == "ADS1292 validation protocol");
  REQUIRE(n.steps[0].start_seconds == Approx(0.0)); REQUIRE(n.steps[0].label == "step");
  auto path = (std::filesystem::temp_directory_path()/"p7b2_proto.json").string();
  io::write_protocol_json(path, io::protocol_template());
  auto back = io::read_protocol_json(path);
  REQUIRE(back.steps.size() >= 1);
}
