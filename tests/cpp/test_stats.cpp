// tests/cpp/test_stats.cpp
// Regression tests for Stats.cpp — B6: percentile empty-input guard.
#include "catch.hpp"
#include "ads1292/dsp/Stats.h"
#include <vector>

using namespace ads1292::dsp;

TEST_CASE("percentile returns 0.0 for empty input (B6 regression)", "[dsp][stats]") {
    // B6: before the fix, xs.size()-1 underflows std::size_t (0-1 wraps to SIZE_MAX)
    // causing out-of-bounds access / UB.  After the fix: returns 0.0 cleanly.
    REQUIRE(percentile({}, 50.0) == 0.0);
    REQUIRE(percentile({}, 0.0)  == 0.0);
    REQUIRE(percentile({}, 100.0) == 0.0);
}

TEST_CASE("percentile scalar input returns that value", "[dsp][stats]") {
    REQUIRE(percentile({42.0}, 50.0) == Approx(42.0));
}

TEST_CASE("percentile interpolates correctly for two-element input", "[dsp][stats]") {
    // p50 of {0, 10} = 5.0
    REQUIRE(percentile({0.0, 10.0}, 50.0) == Approx(5.0));
    // p0 = 0.0, p100 = 10.0
    REQUIRE(percentile({0.0, 10.0}, 0.0)   == Approx(0.0));
    REQUIRE(percentile({0.0, 10.0}, 100.0) == Approx(10.0));
}
