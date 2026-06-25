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
