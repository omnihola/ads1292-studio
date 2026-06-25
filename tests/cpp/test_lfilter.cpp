// tests/cpp/test_lfilter.cpp
#include "catch.hpp"
#include "ads1292/dsp/Iir.h"
using namespace ads1292::dsp;

TEST_CASE("lfilter of a step with a simple IIR", "[dsp]") {
  // y[n] = x[n] (b={1}, a={1}) is identity
  Coeffs id{{1.0}, {1.0}};
  auto y = lfilter(id, {1, 2, 3}, {});
  REQUIRE(y == std::vector<double>{1, 2, 3});
}

TEST_CASE("lfilter_zi makes a step response start at steady state", "[dsp]") {
  // For a lowpass-ish filter, lfilter(b,a, ones, zi*ones[0]) stays ~1.0 (no startup transient)
  Coeffs c = butter_lowpass(500.0, 40.0);
  auto zi = lfilter_zi(c);
  std::vector<double> ones(50, 1.0);
  std::vector<double> z0; for (double v : zi) z0.push_back(v * ones[0]);
  auto y = lfilter(c, ones, z0);
  REQUIRE(y.front() == Approx(1.0).margin(1e-9));   // no transient at the start
  REQUIRE(y.back() == Approx(1.0).margin(1e-9));
}
