// tests/cpp/test_channel_select.cpp
// Verifies that choose_ecg_channel reproduces the golden scores + channel
// from tests/fixtures/golden/review/quality_metrics_clean_72bpm.json.
//
// NOTE: In the fixture, "ch1" is stored as a scalar integer 0 (representing
// a flat all-zeros channel).  nlohmann/json cannot parse a scalar as
// vector<double>, so we expand it manually into a zero-filled vector that
// matches the length of ch2.
#include "catch.hpp"
#include "ads1292/dsp/ChannelSelect.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;
using namespace ads1292::dsp;

namespace {
json rv(const std::string& n) {
    std::ifstream in(std::string(FIXTURE_DIR) + "/review/" + n + ".json");
    json j;
    in >> j;
    return j;
}
} // namespace

TEST_CASE("choose_ecg_channel reproduces the golden scores + channel", "[review]") {
    auto f  = rv("quality_metrics_clean_72bpm");
    auto ch2 = f.at("input").at("ch2").get<std::vector<double>>();

    // ch1 is stored as scalar 0 in the fixture (flat all-zero channel).
    std::vector<double> ch1(ch2.size(), 0.0);

    auto o = f.at("output");
    auto c = choose_ecg_channel(ch1, ch2, 500.0, "Auto");
    REQUIRE(c.score_ch1 == Approx(o.at("score_ch1").get<double>()).margin(1e-9));
    REQUIRE(c.score_ch2 == Approx(o.at("score_ch2").get<double>()).margin(1e-9));
    REQUIRE(c.channel   == o.at("ecg_source").get<std::string>());   // "CH2"
}
