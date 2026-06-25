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

    // Additional assertions: HR range, CH2 score, and gate failures
    REQUIRE(html.find("<th>HR range</th><td>71.0-73.0 bpm</td>") != std::string::npos);
    REQUIRE(html.find("<th>CH2 score</th><td>100.39</td>") != std::string::npos);
    REQUIRE(html.find("<th>Failures</th><td>None</td>") != std::string::npos);   // gate passed -> no failures
}

TEST_CASE("build_review_html renders metadata + events + escapes specials", "[report]") {
    io::ReviewHtmlInputs in;
    in.title = "A & B <test>";                      // special chars -> escaped in title

    // Set metrics with qrs_clear=false to test "not reliable" P/T waves
    in.metrics.ecg_source = "CH1";
    in.metrics.sample_count = 1000;
    in.metrics.duration_seconds = 5.0;
    in.metrics.contact_ok_percent = 100.0;
    in.metrics.lead_off_bad_samples = 0;
    in.metrics.r_peaks = 6;
    in.metrics.hr_median_bpm = 70.0;
    in.metrics.hr_min_bpm = 65.0;
    in.metrics.hr_max_bpm = 75.0;
    in.metrics.qrs_clear = false;                   // test False boolean
    in.metrics.p_tentative = false;                 // test "not reliable" P wave
    in.metrics.t_tentative = false;                 // test "not reliable" T wave
    in.metrics.baseline_drift_counts = 0.5;
    in.metrics.noise_rms_counts = 3.0;
    in.metrics.peak_to_peak_counts = 500.0;
    in.metrics.score_ch1 = 95.67;
    in.metrics.score_ch2 = 0.0;

    // Gate failed with a failure message containing special chars
    in.gate.passed = false;
    in.gate.failures = { "duration 5.00s < 8.00s" };   // label()->"Fail"
    in.calibration = Calibration{};

    // Add session metadata with special chars
    ads1292::SessionMetadata meta;
    meta.session_id = "run-1";
    meta.subject_id = "subj <x>";
    meta.electrode = "MOTAC";
    meta.operator_ = "tech & co";
    in.metadata = meta;

    // Add an event marker with special chars in notes
    ads1292::EventMarker ev;
    ev.timestamp_seconds = 5.0;
    ev.duration_seconds = 3.0;
    ev.label = "motion";
    ev.notes = "a & b";
    in.events = { ev };

    in.ecg_png_name = "e.png";
    in.pqrst_png_name = "p.png";
    in.spectrum_png_name = "s.png";

    auto html = io::build_review_html(in);

    // Metadata section rendered
    REQUIRE(html.find("<h2>Session Metadata</h2>") != std::string::npos);
    REQUIRE(html.find("<th>Session ID</th><td>run-1</td>") != std::string::npos);

    // Events section rendered
    REQUIRE(html.find("<h2>Event Markers</h2>") != std::string::npos);
    REQUIRE(html.find("motion") != std::string::npos);

    // P/T wave "not reliable" path
    REQUIRE(html.find("<th>P wave</th><td>not reliable</td>") != std::string::npos);
    REQUIRE(html.find("<th>T wave</th><td>not reliable</td>") != std::string::npos);
    REQUIRE(html.find("<th>QRS clear</th><td>False</td>") != std::string::npos);   // str(bool) capital

    // Gate Fail + failure listed (with escaped <)
    REQUIRE(html.find("<th>Status</th><td>Fail</td>") != std::string::npos);
    REQUIRE(html.find("duration 5.00s &lt; 8.00s") != std::string::npos);          // '<' escaped

    // Escaping: title special chars escaped (no raw '<test>')
    REQUIRE(html.find("A &amp; B &lt;test&gt;") != std::string::npos);

    // Escaping: metadata special chars escaped (no raw 'subj <x>')
    REQUIRE(html.find("subj &lt;x&gt;") != std::string::npos);

    // Escaping: event notes escaped
    REQUIRE(html.find("a &amp; b") != std::string::npos);
}
