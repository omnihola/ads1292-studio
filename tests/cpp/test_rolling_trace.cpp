// tests/cpp/test_rolling_trace.cpp
#include "catch.hpp"
#include "ads1292/view/RollingTrace.h"

using ads1292::view::RollingTrace;

TEST_CASE("RollingTrace keeps only the rolling window", "[trace]") {
  RollingTrace t(500.0, 4.0);              // 4 s window @ 500 Hz = 2000 samples
  for (int i = 0; i < 5000; ++i) t.append(static_cast<double>(i));
  REQUIRE(t.size() == 2000);               // older samples dropped
  auto y = t.y();
  REQUIRE_FALSE(y.empty());
  REQUIRE(y.back() == Approx(4999.0));     // newest sample retained
}

TEST_CASE("RollingTrace decimates wide windows to <= max_points", "[trace]") {
  RollingTrace t(500.0, 60.0);             // 30000 samples
  for (int i = 0; i < 30000; ++i) t.append(static_cast<double>(i % 100));
  auto x = t.x();
  auto y = t.y();
  REQUIRE(x.size() == y.size());
  REQUIRE(x.size() <= 2000);               // decimated
  REQUIRE(x.size() > 0);
}

TEST_CASE("RollingTrace x is relative seconds ending at the latest", "[trace]") {
  RollingTrace t(500.0, 4.0);
  for (int i = 0; i < 2000; ++i) t.append(0.0);
  auto x = t.x();
  REQUIRE(x.front() == Approx(0.0).margin(1e-9));
  REQUIRE(x.back() == Approx((2000 - 1) / 500.0).margin(1e-6));
}
