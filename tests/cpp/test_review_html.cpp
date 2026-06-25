// tests/cpp/test_review_html.cpp
#include "catch.hpp"
#include "ads1292/io/ReviewHtml.h"

using namespace ads1292;

TEST_CASE("build_review_html renders the metrics + gate + calibration tables", "[report]") {
    io::ReviewHtmlInputs in;
    in.title = "Test Report";

    // quality_label is a free function: set fields so quality_label(metrics) → "Good ECG/QRS"
    // Algorithm: contact_ok_percent >= 99 && qrs_clear && r_peaks >= 5 && hr_median_bpm > 0
    in.metrics.ecg_source = "CH2";
    in.metrics.sample_count = 2500;
    in.metrics.duration_seconds = 4.998;
    in.metrics.contact_ok_percent = 100.0;
    in.metrics.lead_off_bad_samples = 0;
    in.metrics.r_peaks = 6;
    in.metrics.hr_median_bpm = 72.0;
    in.metrics.hr_min_bpm = 71.0;
    in.metrics.hr_max_bpm = 73.0;
    in.metrics.qrs_clear = true;
    in.metrics.p_tentative = false;
    in.metrics.t_tentative = false;
    in.metrics.baseline_drift_counts = 1.0;
    in.metrics.noise_rms_counts = 6.3;
    in.metrics.peak_to_peak_counts = 715.0;
    in.metrics.score_ch1 = 0.0;
    in.metrics.score_ch2 = 100.39;

    in.gate.passed = true;  // label() → "Pass"
    in.calibration = Calibration{};  // defaults

    in.ecg_png_name = "r-ecg.png";
    in.pqrst_png_name = "r-pqrst.png";
    in.spectrum_png_name = "r-spectrum.png";

    auto html = io::build_review_html(in);

    REQUIRE(html.find("<!doctype html>") != std::string::npos);
    REQUIRE(html.find("<title>Test Report</title>") != std::string::npos);
    REQUIRE(html.find("<th>ECG source</th><td>CH2</td>") != std::string::npos);
    REQUIRE(html.find("<th>R peaks</th><td>6</td>") != std::string::npos);
    REQUIRE(html.find("<th>Median HR</th><td>72.0 bpm</td>") != std::string::npos);
    REQUIRE(html.find("<th>QRS clear</th><td>True</td>") != std::string::npos);  // Python str(True)
    REQUIRE(html.find("<h2>Quality Gate</h2>") != std::string::npos);
    REQUIRE(html.find("<th>Status</th><td>Pass</td>") != std::string::npos);
    REQUIRE(html.find("<h2>Calibration</h2>") != std::string::npos);
    REQUIRE(html.find("r-ecg.png") != std::string::npos);
}
