// tests/cpp/test_live_calibration.cpp
// Tests for LiveStreamCalibration model + statistics.

#include "catch.hpp"
#include "ads1292/dsp/LiveCalibration.h"
#include "ads1292/dsp/Stats.h"

#include <cmath>
#include <vector>

using ads1292::LiveStreamCalibration;
using ads1292::dsp::live_stream_peak_to_peak_counts;
using ads1292::dsp::summarize_live_stream_calibration;
using ads1292::dsp::percentile;

// ---------------------------------------------------------------------------
// LiveStreamCalibration::normalized()
// ---------------------------------------------------------------------------

TEST_CASE("normalized() clamps negative fields and fills defaults", "[model][live_calibration]") {
    LiveStreamCalibration c;
    c.std_uv_per_count  = -1.0;
    c.runs              = -2;
    c.cv_percent        = -5.0;
    c.test_signal_pp_uv = 0.0;
    c.scale_type        = "  ";

    auto n = c.normalized();

    REQUIRE(n.std_uv_per_count   == 0.0);
    REQUIRE(n.runs               == 0);
    REQUIRE(n.cv_percent         == 0.0);
    REQUIRE(n.test_signal_pp_uv  == Approx(2016.6666666667));
    REQUIRE(n.scale_type         == "live_processed");
}

TEST_CASE("normalized() passes through valid values unchanged", "[model][live_calibration]") {
    LiveStreamCalibration c;
    c.mean_uv_per_count  = 20.0;
    c.std_uv_per_count   = 1.5;
    c.cv_percent         = 7.5;
    c.runs               = 3;
    c.test_signal_pp_uv  = 2000.0;
    c.scale_type         = "live_processed";

    auto n = c.normalized();

    REQUIRE(n.mean_uv_per_count  == Approx(20.0));
    REQUIRE(n.std_uv_per_count   == Approx(1.5));
    REQUIRE(n.cv_percent         == Approx(7.5));
    REQUIRE(n.runs               == 3);
    REQUIRE(n.test_signal_pp_uv  == Approx(2000.0));
    REQUIRE(n.scale_type         == "live_processed");
}

TEST_CASE("normalized() strips whitespace from scale_type", "[model][live_calibration]") {
    LiveStreamCalibration c;
    c.scale_type        = "  custom  ";
    c.test_signal_pp_uv = 100.0;
    auto n = c.normalized();
    REQUIRE(n.scale_type == "custom");
}

// ---------------------------------------------------------------------------
// summarize_live_stream_calibration()
// ---------------------------------------------------------------------------

TEST_CASE("summarize: two equal counts produce mean=20, std=0, cv=0, runs=2",
          "[dsp][live_calibration]") {
    // scales = {2000/100, 2000/100} = {20, 20}
    auto cal = summarize_live_stream_calibration({100.0, 100.0}, 2000.0);
    REQUIRE(cal.mean_uv_per_count == Approx(20.0));
    REQUIRE(cal.std_uv_per_count  == Approx(0.0));
    REQUIRE(cal.cv_percent        == Approx(0.0));
    REQUIRE(cal.runs              == 2);
}

TEST_CASE("summarize: two differing counts produce correct sample-std and cv",
          "[dsp][live_calibration]") {
    // scales = {2000/100, 2000/200} = {20, 10}
    // mean = 15; sample-std = sqrt(((20-15)^2 + (10-15)^2) / 1) = sqrt(50)
    // cv = sqrt(50)/15*100
    auto cal = summarize_live_stream_calibration({100.0, 200.0}, 2000.0);
    const double expected_std = std::sqrt(50.0);
    const double expected_cv  = expected_std / 15.0 * 100.0;

    REQUIRE(cal.mean_uv_per_count == Approx(15.0));
    REQUIRE(cal.std_uv_per_count  == Approx(expected_std));
    REQUIRE(cal.cv_percent        == Approx(expected_cv));
    REQUIRE(cal.runs              == 2);
}

TEST_CASE("summarize: single run has std=0 and cv=0", "[dsp][live_calibration]") {
    auto cal = summarize_live_stream_calibration({200.0}, 2000.0);
    REQUIRE(cal.mean_uv_per_count == Approx(10.0));
    REQUIRE(cal.std_uv_per_count  == Approx(0.0));
    REQUIRE(cal.cv_percent        == Approx(0.0));
    REQUIRE(cal.runs              == 1);
}

TEST_CASE("summarize: empty vector throws", "[dsp][live_calibration]") {
    REQUIRE_THROWS_AS(
        summarize_live_stream_calibration({}, 2000.0),
        std::invalid_argument);
}

TEST_CASE("summarize: all-zero counts throw", "[dsp][live_calibration]") {
    REQUIRE_THROWS_AS(
        summarize_live_stream_calibration({0.0, 0.0, 0.0}, 2000.0),
        std::invalid_argument);
}

TEST_CASE("summarize: zero counts are filtered, positive ones used",
          "[dsp][live_calibration]") {
    // {0, 100, 0} -> only 100 is used -> scales={20} -> mean=20, std=0, runs=1
    auto cal = summarize_live_stream_calibration({0.0, 100.0, 0.0}, 2000.0);
    REQUIRE(cal.mean_uv_per_count == Approx(20.0));
    REQUIRE(cal.runs              == 1);
}

// ---------------------------------------------------------------------------
// live_stream_peak_to_peak_counts()
// ---------------------------------------------------------------------------

TEST_CASE("peak_to_peak: fewer than 4 values throws", "[dsp][live_calibration]") {
    REQUIRE_THROWS_AS(
        live_stream_peak_to_peak_counts({1.0, 2.0, 3.0}),
        std::invalid_argument);
    REQUIRE_THROWS_AS(
        live_stream_peak_to_peak_counts({}),
        std::invalid_argument);
}

TEST_CASE("peak_to_peak: all-equal values (pp=0) throws", "[dsp][live_calibration]") {
    REQUIRE_THROWS_AS(
        live_stream_peak_to_peak_counts({5.0, 5.0, 5.0, 5.0, 5.0, 5.0}),
        std::invalid_argument);
}

TEST_CASE("peak_to_peak: ramp {0..100} returns percentile(99)-percentile(1)",
          "[dsp][live_calibration]") {
    // Build {0, 1, 2, ..., 100} (101 elements).
    std::vector<double> v(101);
    for (int i = 0; i <= 100; ++i) v[static_cast<std::size_t>(i)] = static_cast<double>(i);

    // Compute expected using the C++ percentile directly (numpy-faithful).
    // pos(1%)  = 0.01*100 = 1.0 -> xs[1] = 1.0
    // pos(99%) = 0.99*100 = 99.0 -> xs[99] = 99.0  => pp = 98.0
    const double low      = percentile(v, 1.0);
    const double high     = percentile(v, 99.0);
    const double expected = high - low;

    REQUIRE(live_stream_peak_to_peak_counts(v) == Approx(expected));
}

TEST_CASE("peak_to_peak: non-finite values are excluded, valid subset used",
          "[dsp][live_calibration]") {
    // 4 finite values {10, 20, 30, 40} plus 2 non-finite; should not throw.
    const double inf = std::numeric_limits<double>::infinity();
    std::vector<double> v = {10.0, inf, 20.0, -inf, 30.0, 40.0};
    // finite = {10, 20, 30, 40}; p1 and p99 of 4-element sorted array:
    // pos(1%)  = 0.01*3 = 0.03 -> 10 + 0.03*(20-10) = 10.3
    // pos(99%) = 0.99*3 = 2.97 -> 30 + 0.97*(40-30) = 39.7 => pp = 29.4
    std::vector<double> finite_vals = {10.0, 20.0, 30.0, 40.0};
    const double low  = percentile(finite_vals, 1.0);
    const double high = percentile(finite_vals, 99.0);
    REQUIRE(live_stream_peak_to_peak_counts(v) == Approx(high - low));
}

TEST_CASE("peak_to_peak: fewer than 4 finite values throws",
          "[dsp][live_calibration]") {
    const double nan = std::numeric_limits<double>::quiet_NaN();
    // Only 3 finite values, so must throw even though total size >= 4.
    REQUIRE_THROWS_AS(
        live_stream_peak_to_peak_counts({1.0, nan, 2.0, nan, 3.0}),
        std::invalid_argument);
}
