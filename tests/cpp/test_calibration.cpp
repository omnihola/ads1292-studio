// tests/cpp/test_calibration.cpp
#include "catch.hpp"
#include "ads1292/model/Calibration.h"

using ads1292::Calibration;

TEST_CASE("default Calibration microvolts_per_count matches the oracle", "[model]") {
  Calibration c;
  // 2420*1000 / (6 * 2^23) = 0.04808108..., printed %.9f -> 0.048081080
  REQUIRE(c.microvolts_per_count() == Approx(0.048081080).margin(1e-9));
}

TEST_CASE("Calibration normalized clamps invalid values", "[model]") {
  Calibration bad{-1.0, 0.0, 1, "   "};
  Calibration n = bad.normalized();
  REQUIRE(n.vref_mv == Approx(2420.0));
  REQUIRE(n.pga_gain == Approx(6.0));
  REQUIRE(n.adc_bits == 24);
  REQUIRE(n.label == "ADS1292 default");
}
