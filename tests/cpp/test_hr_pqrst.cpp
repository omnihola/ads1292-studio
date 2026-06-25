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
