// tests/cpp/test_quality_metrics.cpp
// Golden-parity test for compute_quality_metrics.
// NOTE: the fixture's "ch1" field is a scalar 0, not an array.
// Per the task brief, ch1 is built as vector<int>(ch2.size(), 0).
#include "catch.hpp"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/model/StreamSample.h"
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

TEST_CASE("compute_quality_metrics matches the golden", "[review]") {
    auto f = rv("quality_metrics_clean_72bpm");

    // ch1 in the fixture is scalar 0 — build a zero-filled vector to match.
    auto ch2 = f.at("input").at("ch2").get<std::vector<int>>();
    std::vector<int> ch1(ch2.size(), 0);
    int status = f.at("input").at("status_byte").get<int>();

    std::vector<ads1292::StreamSample> samples;
    samples.reserve(ch2.size());
    for (size_t i = 0; i < ch2.size(); ++i) {
        ads1292::StreamSample s;
        s.ch1 = ch1[i];
        s.ch2 = ch2[i];
        s.status_byte = status;
        samples.push_back(s);
    }

    auto m = compute_quality_metrics(samples, 500.0, "Auto");
    auto o = f.at("output");

    REQUIRE(m.sample_count        == o.at("sample_count").get<int>());
    REQUIRE(m.ecg_source          == o.at("ecg_source").get<std::string>());
    REQUIRE(m.contact_ok_percent  == Approx(o.at("contact_ok_percent").get<double>()).margin(1e-9));
    REQUIRE(m.lead_off_bad_samples == o.at("lead_off_bad_samples").get<int>());
    REQUIRE(m.r_peaks             == o.at("r_peaks").get<int>());
    REQUIRE(m.hr_median_bpm       == Approx(o.at("hr_median_bpm").get<double>()).margin(1e-9));
    REQUIRE(m.hr_min_bpm          == Approx(o.at("hr_min_bpm").get<double>()).margin(1e-9));
    REQUIRE(m.hr_max_bpm          == Approx(o.at("hr_max_bpm").get<double>()).margin(1e-9));
    REQUIRE(m.qrs_clear           == o.at("qrs_clear").get<bool>());
    REQUIRE(m.p_tentative         == o.at("p_tentative").get<bool>());
    REQUIRE(m.t_tentative         == o.at("t_tentative").get<bool>());
    REQUIRE(m.score_ch1           == Approx(o.at("score_ch1").get<double>()).margin(1e-9));
    REQUIRE(m.score_ch2           == Approx(o.at("score_ch2").get<double>()).margin(1e-9));
    REQUIRE(m.baseline_drift_counts == Approx(o.at("baseline_drift_counts").get<double>()).margin(1e-9));
    REQUIRE(m.noise_rms_counts    == Approx(o.at("noise_rms_counts").get<double>()).margin(1e-9));
    REQUIRE(m.peak_to_peak_counts == Approx(o.at("peak_to_peak_counts").get<double>()).margin(1e-9));
}
