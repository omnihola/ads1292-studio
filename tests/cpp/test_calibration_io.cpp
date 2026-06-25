// tests/cpp/test_calibration_io.cpp
#include "catch.hpp"
#include "ads1292/io/CalibrationIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }

TEST_CASE("read golden calibration.json (defaults)", "[sidecar]") {
  auto c = io::read_calibration_json(fx("calibration.json"));
  REQUIRE(c.vref_mv == Approx(2420.0)); REQUIRE(c.pga_gain == Approx(6.0));
  REQUIRE(c.adc_bits == 24); REQUIRE(c.label == "ADS1292 default");
}
TEST_CASE("read golden calibration_custom.json", "[sidecar]") {
  auto c = io::read_calibration_json(fx("calibration_custom.json"));
  REQUIRE(c.vref_mv == Approx(2400.0)); REQUIRE(c.pga_gain == Approx(12.0)); REQUIRE(c.label == "custom");
}
TEST_CASE("microvolts_per_count matches the datasheet formula", "[sidecar]") {
  Calibration c;  // defaults: 2420 mV, gain 6, 24 bits
  // vref_mv*1000 / (gain * 2^23) = 2420000 / (6 * 8388608)
  REQUIRE(c.microvolts_per_count() == Approx(2420.0*1000.0/(6.0*8388608.0)));
}
TEST_CASE("calibration normalizes invalid values + round-trips", "[sidecar]") {
  Calibration c; c.vref_mv=-1; c.pga_gain=0; c.adc_bits=1; c.label="  ";
  auto n = c.normalized();
  REQUIRE(n.vref_mv == Approx(2420.0)); REQUIRE(n.pga_gain == Approx(6.0)); REQUIRE(n.adc_bits == 24); REQUIRE(n.label == "ADS1292 default");
  auto p = (std::filesystem::temp_directory_path() / "p7b_cal.json").string();
  io::write_calibration_json(p, Calibration{2400.0, 12.0, 24, "x"});
  REQUIRE(io::read_calibration_json(p).label == "x");
}
