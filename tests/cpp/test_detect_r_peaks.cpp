// tests/cpp/test_detect_r_peaks.cpp
// Parity tests for detect_r_peaks vs the P-1 golden rpeak fixtures.
// Exact peak-index match required (REQUIRE, not Approx).
#include "catch.hpp"
#include "ads1292/dsp/EcgReview.h"
#include "ads1292/dsp/Filtfilt.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;
using namespace ads1292::dsp;

namespace {
json fx(const std::string& n) {
    std::ifstream in(std::string(FIXTURE_DIR) + "/rpeak/" + n + ".json");
    json j;
    in >> j;
    return j;
}
} // namespace

TEST_CASE("detect_r_peaks reproduces the clean 72bpm peaks exactly", "[rpeak]") {
    auto f   = fx("rpeak_chain_clean_72bpm");
    auto sig = f.at("input").at("signal").get<std::vector<double>>();
    auto got = detect_r_peaks(sig, 500.0);
    auto exp = f.at("output").at("peaks").get<std::vector<int>>();
    REQUIRE(got == exp); // EXACT index match
}

TEST_CASE("detect_r_peaks fast 110bpm exact", "[rpeak]") {
    auto f   = fx("rpeak_chain_fast_110bpm");
    auto sig = f.at("input").at("signal").get<std::vector<double>>();
    REQUIRE(detect_r_peaks(sig, 500.0) == f.at("output").at("peaks").get<std::vector<int>>());
}

TEST_CASE("detect_r_peaks short-below-sr returns empty", "[rpeak]") {
    auto f   = fx("rpeak_chain_short_below_sr");
    auto sig = f.at("input").at("signal").get<std::vector<double>>();
    REQUIRE(detect_r_peaks(sig, 500.0).empty());
}
