// tests/cpp/test_review_render.cpp
// Unit tests for the portable review core: robust_ylim, quality_label,
// display_mode_label, and build_review_render_frame.
// Pure C++17, Catch2.

#include "catch.hpp"
#include "ads1292/view/ReviewRender.h"
#include "ads1292/view/PlotStats.h"
#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/model/StreamSample.h"
#include <cmath>

using namespace ads1292;
using namespace ads1292::view;
using namespace ads1292::dsp;

TEST_CASE("robust_ylim: empty -> (-1,1); flat -> padded", "[review]") {
    REQUIRE(robust_ylim({}, 0.0) == std::pair<double,double>{-1.0, 1.0});
    // <=50 samples, all 5.0: min==max==5 -> lo=4, hi=6 -> pad=max(1,0.15*2)=1 -> (3,7)
    auto [lo, hi] = robust_ylim(std::vector<double>(10, 5.0), 0.0);
    REQUIRE(lo == Approx(3.0));
    REQUIRE(hi == Approx(7.0));
}

TEST_CASE("quality_label thresholds", "[review]") {
    QualityMetrics m{};
    m.contact_ok_percent = 100; m.qrs_clear = true; m.r_peaks = 6; m.hr_median_bpm = 72;
    REQUIRE(quality_label(m) == "Good ECG/QRS");
    m.contact_ok_percent = 96;
    REQUIRE(quality_label(m) == "Usable ECG/QRS");
    m.qrs_clear = false;
    REQUIRE(quality_label(m) == "Needs review");
    m.qrs_clear = true; m.contact_ok_percent = 100; m.r_peaks = 3;
    REQUIRE(quality_label(m) == "Insufficient ECG");
}

TEST_CASE("display_mode_label QRS + raw", "[review]") {
    EcgDisplaySettings ds;  // defaults: 8s, 1x, 25 mm/s (already normalized)
    SoftwareFilterSettings qrs;
    qrs.bandpass_enabled = true;
    REQUIRE(display_mode_label(ds, qrs) == "QRS | 1x | 8s | 25 mm/s");
    REQUIRE(display_mode_label(ds, SoftwareFilterSettings{}) == "raw | 1x | 8s | 25 mm/s");
}

TEST_CASE("build_review_render_frame on a synthetic recording", "[review]") {
    std::vector<StreamSample> samples;
    for (int i = 0; i < 3000; ++i) {
        StreamSample s;
        double t = i / 500.0;
        double v = 0.0;
        for (double bt = 0.2; bt < 6.0; bt += 60.0 / 72.0) {
            double d = t - bt;
            v += 200.0 * std::exp(-(d * d) / (2 * 0.01 * 0.01));
        }
        s.ch2 = static_cast<int>(v);
        s.ch1 = 0;
        s.status_byte = 0;
        samples.push_back(s);
    }
    auto f = build_review_render_frame(
        samples,
        EcgDisplaySettings{},
        SoftwareFilterSettings{},
        "Auto",
        500.0,
        5,
        5000,
        false,
        50.0,
        50.0);
    REQUIRE(f.sample_count == 3000);
    REQUIRE(f.duration_seconds == Approx(6.0));  // count/sr = 3000/500
    REQUIRE(f.review_peaks.size() >= 5);
    REQUIRE(f.metrics.r_peaks == static_cast<int>(f.review_peaks.size()));
    REQUIRE(f.pqrst.average_beat.size() > 0);
    REQUIRE(f.ecg_ylim.second > f.ecg_ylim.first);
}
