// tests/cpp/test_filtfilt.cpp
// Golden-fixture parity tests for filtfilt + the bandpass/highpass/lowpass/notch wrappers.
// Pure C++17, no Qt.
#include "catch.hpp"
#include "ads1292/dsp/Filtfilt.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;
using namespace ads1292::dsp;

namespace {

json fx(const std::string& n) {
    std::ifstream in(std::string(FIXTURE_DIR) + "/dsp/" + n + ".json");
    json j;
    in >> j;
    return j;
}

std::vector<double> in_signal(const json& f) {
    return f.at("input").at("signal").get<std::vector<double>>();
}

void check_close(const std::vector<double>& got, const json& f, double tol) {
    auto exp = f.at("output").at("filtered").get<std::vector<double>>();
    REQUIRE(got.size() == exp.size());
    for (size_t i = 0; i < exp.size(); ++i)
        REQUIRE(got[i] == Approx(exp[i]).margin(tol));
}

} // namespace

TEST_CASE("filtfilt bandpass long matches golden", "[dsp]") {
    auto f = fx("filtfilt_bandpass_long");
    check_close(bandpass(in_signal(f), 500.0), f, 1e-6);
}

TEST_CASE("filtfilt bandpass short window matches", "[dsp]") {
    auto f = fx("filtfilt_bandpass_short_window");
    check_close(bandpass(in_signal(f), 500.0), f, 1e-6);
}

TEST_CASE("filtfilt bandpass tiny (<16) uses the median fallback", "[dsp]") {
    auto f = fx("filtfilt_bandpass_tiny_fallback");
    check_close(bandpass(in_signal(f), 500.0), f, 1e-9);
}

TEST_CASE("filtfilt notch/highpass/lowpass long match", "[dsp]") {
    check_close(notch(in_signal(fx("filtfilt_notch_long")), 500.0),
                fx("filtfilt_notch_long"), 1e-6);
    check_close(highpass(in_signal(fx("filtfilt_highpass_long")), 500.0),
                fx("filtfilt_highpass_long"), 1e-6);
    check_close(lowpass(in_signal(fx("filtfilt_lowpass_long")), 500.0),
                fx("filtfilt_lowpass_long"), 1e-6);
}
