// tests/cpp/test_find_peaks.cpp
// Unit tests for find_peaks (local maxima + distance + prominence, SciPy order).
// Pure C++17, no Qt. Verified against scipy.signal.find_peaks.
#include "catch.hpp"
#include "ads1292/dsp/Peaks.h"
using ads1292::dsp::find_peaks;

TEST_CASE("find_peaks: distance keeps the taller peak (scipy order)", "[peaks]") {
    std::vector<double> x = {0, 5, 0, 10, 0, 6, 0};   // peaks at 1(5),3(10),5(6)
    REQUIRE(find_peaks(x, /*distance=*/3, /*prominence=*/0.0) == std::vector<int>{3});
    REQUIRE(find_peaks(x, 3, 4.0) == std::vector<int>{3});      // prominence after distance
}

TEST_CASE("find_peaks: plateau midpoint", "[peaks]") {
    std::vector<double> x = {0, 1, 2, 2, 2, 1, 0};    // plateau [2..4] -> midpoint 3
    REQUIRE(find_peaks(x, 1, 0.0) == std::vector<int>{3});
}

TEST_CASE("find_peaks: prominence filters low peaks", "[peaks]") {
    std::vector<double> x = {0, 1, 0, 10, 0};          // peak at 1 (prom 1), 3 (prom 10)
    REQUIRE(find_peaks(x, 1, 5.0) == std::vector<int>{3});
}
