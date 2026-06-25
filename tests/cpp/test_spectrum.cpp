// tests/cpp/test_spectrum.cpp
// Golden-fixture parity test for build_spectrum_analysis.
// Verifies: ecg_frequency_hz (abs 1e-9), ecg_power (rel 1e-9),
//           histogram_counts (exact), histogram_bin_edges (abs 1e-9).
#include "catch.hpp"
#include "ads1292/dsp/Spectrum.h"
#include "ads1292/model/StreamSample.h"
#include "nlohmann/json.hpp"
#include <complex>
#include <cmath>
#include <fstream>
using nlohmann::json;
using namespace ads1292::dsp;

namespace {
json sp(const std::string& n) {
    std::ifstream in(std::string(FIXTURE_DIR) + "/spectrum/" + n + ".json");
    json j;
    in >> j;
    return j;
}
} // namespace

TEST_CASE("rfft matches the DFT definition for odd length", "[spectrum]") {
    std::vector<double> x = {1.0, -2.0, 3.5, 0.5, -1.0, 2.0, 4.0};  // n=7 (odd)
    auto got = ads1292::dsp::rfft(x);
    const int n = (int)x.size();
    REQUIRE((int)got.size() == n/2 + 1);                 // 4 bins
    const double PI = std::acos(-1.0);
    for (int k = 0; k < n/2 + 1; ++k) {
        std::complex<double> acc(0.0, 0.0);
        for (int j = 0; j < n; ++j) {
            double ang = -2.0 * PI * k * j / n;
            acc += std::complex<double>(x[j], 0.0) * std::complex<double>(std::cos(ang), std::sin(ang));
        }
        REQUIRE(got[k].real() == Approx(acc.real()).margin(1e-9));
        REQUIRE(got[k].imag() == Approx(acc.imag()).margin(1e-9));
    }
}

TEST_CASE("build_spectrum_analysis matches the golden", "[spectrum]") {
    auto f = sp("spectrum_clean_72bpm_ch2");
    auto ch2 = f.at("input").at("ch2").get<std::vector<int>>();
    std::vector<ads1292::StreamSample> samples;
    for (int v : ch2) {
        ads1292::StreamSample s;
        s.ch2 = v;
        samples.push_back(s);
    }
    auto a = build_spectrum_analysis(samples, "CH2", 500.0, 60.0, 48);
    auto o = f.at("output");
    auto ef = o.at("ecg_frequency_hz").get<std::vector<double>>();
    auto ep = o.at("ecg_power").get<std::vector<double>>();
    auto hc = o.at("histogram_counts").get<std::vector<long>>();
    auto he = o.at("histogram_bin_edges").get<std::vector<double>>();

    REQUIRE(a.ecg_frequency_hz.size() == ef.size());
    for (size_t i = 0; i < ef.size(); ++i)
        REQUIRE(a.ecg_frequency_hz[i] == Approx(ef[i]).margin(1e-9));

    REQUIRE(a.ecg_power.size() == ep.size());
    for (size_t i = 0; i < ep.size(); ++i)
        REQUIRE(a.ecg_power[i] == Approx(ep[i]).epsilon(1e-9));   // REL 1e-9

    REQUIRE(a.histogram_counts == hc);                             // EXACT

    REQUIRE(a.histogram_bin_edges.size() == he.size());
    for (size_t i = 0; i < he.size(); ++i)
        REQUIRE(a.histogram_bin_edges[i] == Approx(he[i]).margin(1e-9));
}
