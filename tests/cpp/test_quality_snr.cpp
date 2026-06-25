// tests/cpp/test_quality_snr.cpp
#include "catch.hpp"
#include "ads1292/dsp/Quality.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace { json rv(const std::string& n){ std::ifstream in(std::string(FIXTURE_DIR)+"/review/"+n+".json"); json j; in>>j; return j; } }

TEST_CASE("estimate_realtime_snr matches the golden", "[review]") {
  auto f = rv("realtime_snr_clean_72bpm");
  // Fixture uses "values" key (not "signal")
  auto v = f.at("input").at("values").get<std::vector<double>>();
  auto g = estimate_realtime_snr(v, 500.0);
  auto o = f.at("output");
  REQUIRE(g.snr_db == Approx(o.at("snr_db").get<double>()).margin(1e-9));
  REQUIRE(g.signal_rms_counts == Approx(o.at("signal_rms_counts").get<double>()).margin(1e-9));
  REQUIRE(g.noise_rms_counts == Approx(o.at("noise_rms_counts").get<double>()).margin(1e-9));
  REQUIRE(g.peak_to_peak_counts == Approx(o.at("peak_to_peak_counts").get<double>()).margin(1e-9));
  REQUIRE(g.sample_count == o.at("sample_count").get<int>());
  REQUIRE(g.duration_seconds == Approx(o.at("duration_seconds").get<double>()).margin(1e-9));
  REQUIRE(g.valid == o.at("valid").get<bool>());
}
