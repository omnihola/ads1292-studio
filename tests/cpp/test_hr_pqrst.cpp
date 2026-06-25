// tests/cpp/test_hr_pqrst.cpp
// HR summary and PQRST review tests with golden fixtures.

#include "catch.hpp"
#include "ads1292/dsp/EcgReview.h"
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
}  // namespace

TEST_CASE("heart_rate_summary matches the golden", "[review]") {
    auto f = rv("hr_summary_clean_72bpm");
    auto peaks = f.at("input").at("peaks").get<std::vector<int>>();
    auto got = heart_rate_summary(peaks, 500.0);
    auto o = f.at("output");
    REQUIRE(got.median_bpm == Approx(o.at("median_bpm").get<double>()).margin(1e-9));
    REQUIRE(got.min_bpm == Approx(o.at("min_bpm").get<double>()).margin(1e-9));
    REQUIRE(got.max_bpm == Approx(o.at("max_bpm").get<double>()).margin(1e-9));
    REQUIRE(got.valid_rr_count == o.at("valid_rr_count").get<int>());
}

TEST_CASE("pqrst_review matches the golden", "[review]") {
    auto f = rv("pqrst_clean_72bpm");
    auto sig = f.at("input").at("signal").get<std::vector<double>>();
    auto peaks = f.at("input").at("peaks").get<std::vector<int>>();
    auto got = pqrst_review(sig, peaks, 500.0);
    auto o = f.at("output");
    REQUIRE(got.qrs_clear == o.at("qrs_clear").get<bool>());
    REQUIRE(got.p_tentative == o.at("p_tentative").get<bool>());
    REQUIRE(got.t_tentative == o.at("t_tentative").get<bool>());
    REQUIRE(got.beats_used == o.at("beats_used").get<int>());
    auto eb = o.at("average_beat").get<std::vector<double>>();
    REQUIRE(got.average_beat.size() == eb.size());
    for (size_t i = 0; i < eb.size(); ++i)
        REQUIRE(got.average_beat[i] == Approx(eb[i]).margin(1e-6));
    auto tm = o.at("time_ms").get<std::vector<double>>();
    REQUIRE(got.time_ms.size() == tm.size());
    for (size_t i = 0; i < tm.size(); ++i)
        REQUIRE(got.time_ms[i] == Approx(tm[i]).margin(1e-9));
}
