// tests/cpp/test_iir_coeffs.cpp
// Coefficient parity tests: butter bandpass/highpass/lowpass vs golden fixtures (abs 1e-12).

#include "catch.hpp"
#include "ads1292/dsp/Iir.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;
using namespace ads1292::dsp;

namespace {

json fx(const std::string& name) {
    std::ifstream in(std::string(FIXTURE_DIR) + "/dsp/" + name + ".json");
    json j;
    in >> j;
    return j;
}

void check(const Coeffs& got, const json& f) {
    auto eb = f.at("output").at("b");
    auto ea = f.at("output").at("a");
    REQUIRE(got.b.size() == eb.size());
    REQUIRE(got.a.size() == ea.size());
    for (std::size_t i = 0; i < eb.size(); ++i)
        REQUIRE(got.b[i] == Approx(eb[i].get<double>()).margin(1e-12));
    for (std::size_t i = 0; i < ea.size(); ++i)
        REQUIRE(got.a[i] == Approx(ea[i].get<double>()).margin(1e-12));
}

} // namespace

TEST_CASE("butter bandpass matches the golden coefficients", "[dsp]") {
    check(butter_bandpass(500.0, 0.7, 35.0), fx("coeffs_bandpass_500hz"));
}

TEST_CASE("butter highpass matches", "[dsp]") {
    check(butter_highpass(500.0, 0.5), fx("coeffs_highpass_500hz"));
}

TEST_CASE("butter lowpass matches", "[dsp]") {
    check(butter_lowpass(500.0, 40.0), fx("coeffs_lowpass_500hz"));
}
