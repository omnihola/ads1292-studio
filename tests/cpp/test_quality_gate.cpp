// tests/cpp/test_quality_gate.cpp
#include "catch.hpp"
#include "ads1292/dsp/QualityGate.h"
#include "ads1292/dsp/QualityMetrics.h"
#include <algorithm>
using namespace ads1292::dsp;
namespace {
QualityMetrics good() {
  QualityMetrics m{}; m.duration_seconds=10.0; m.contact_ok_percent=100.0; m.qrs_clear=true;
  m.r_peaks=8; m.hr_median_bpm=72.0; m.baseline_drift_counts=1.0; m.noise_rms_counts=6.0; m.peak_to_peak_counts=700.0;
  return m;
}
}
TEST_CASE("evaluate_quality_gate: clean metrics pass", "[cli]") {
  auto r = evaluate_quality_gate(good(), QualityGate{});
  REQUIRE(r.passed); REQUIRE(r.failures.empty()); REQUIRE(r.label() == "Pass");
}
TEST_CASE("evaluate_quality_gate: short duration fails with exact message", "[cli]") {
  auto m = good(); m.duration_seconds = 5.0;
  auto r = evaluate_quality_gate(m, QualityGate{});
  REQUIRE_FALSE(r.passed); REQUIRE(r.label() == "Fail");
  REQUIRE(std::find(r.failures.begin(), r.failures.end(), std::string("duration 5.00s < 8.00s")) != r.failures.end());
}
TEST_CASE("evaluate_quality_gate: low contact + unclear QRS + few peaks", "[cli]") {
  auto m = good(); m.contact_ok_percent=90.0; m.qrs_clear=false; m.r_peaks=3;
  auto r = evaluate_quality_gate(m, QualityGate{});
  REQUIRE_FALSE(r.passed);
  REQUIRE(std::find(r.failures.begin(),r.failures.end(),std::string("contact 90.00% < 95.00%")) != r.failures.end());
  REQUIRE(std::find(r.failures.begin(),r.failures.end(),std::string("QRS not clear")) != r.failures.end());
  REQUIRE(std::find(r.failures.begin(),r.failures.end(),std::string("R peaks 3 < 5")) != r.failures.end());
}
TEST_CASE("evaluate_quality_gate: HR over max", "[cli]") {
  auto m = good(); m.hr_median_bpm=200.0;
  auto r = evaluate_quality_gate(m, QualityGate{});
  REQUIRE(std::find(r.failures.begin(),r.failures.end(),std::string("median HR 200.0 bpm > 180.0 bpm")) != r.failures.end());
}
TEST_CASE("evaluate_quality_gate: optional caps", "[cli]") {
  auto m = good(); m.noise_rms_counts=50.0;
  QualityGate g{}; g.max_noise_rms_counts = 10.0;
  auto r = evaluate_quality_gate(m, g);
  REQUIRE(std::find(r.failures.begin(),r.failures.end(),std::string("noise RMS 50.0 counts > 10.0 counts")) != r.failures.end());
}
