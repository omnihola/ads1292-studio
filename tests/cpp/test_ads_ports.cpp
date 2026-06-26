#include "catch.hpp"
#include "ads1292/qt/AdsPorts.h"

using namespace ads1292::qt;

TEST_CASE("is_ads_candidate_port matches TI VID + ADS1x9x PID", "[device]") {
    REQUIRE(is_ads_candidate_port(0x2047, 0x0300));
    REQUIRE_FALSE(is_ads_candidate_port(0x2047, 0x0301));
    REQUIRE_FALSE(is_ads_candidate_port(0x1234, 0x0300));
}

TEST_CASE("list_ads_ports runs without a board (likely empty in CI)", "[device]") {
    auto ports = list_ads_ports();   // no crash; empty when no ADS device attached
    REQUIRE(ports.size() >= 0);
    for (const auto& p : ports) { REQUIRE(!p.device.empty()); }
}

// C8 regression test: is_ads_description_match must return true when description
// contains "ADS1x9x" (case-insensitive).
// Oracle: _is_ads_candidate_port checks `"ADS1x9x" in description`.
TEST_CASE("is_ads_description_match: contains ADS1x9x (case-insensitive) (C8)", "[device]") {
    REQUIRE(is_ads_description_match("ADS1x9x EVM Board"));
    REQUIRE(is_ads_description_match("ads1x9x"));          // lower-case
    REQUIRE(is_ads_description_match("USB ADS1X9X Serial"));  // upper-case
    REQUIRE_FALSE(is_ads_description_match(""));
    REQUIRE_FALSE(is_ads_description_match("Some other device"));
    REQUIRE_FALSE(is_ads_description_match("ADS1292 Raw"));  // no "ADS1x9x"
}
