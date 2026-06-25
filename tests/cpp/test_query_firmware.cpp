#include "catch.hpp"
#include "ads1292/acq/AdsProtocolDevice.h"
#include "ads1292/acq/SimulatorByteTransport.h"
#include "ads1292/acq/AdsFraming.h"

using namespace ads1292::acq;

// payload_len(0x99) == 5 (AdsFraming.cpp: case 0x92: case 0x99: return 5;)
// Wire format: kStart(0x02), type(0x99), 5 payload bytes
// Canned frame with payload {1, 12, 0, 0, 0} => "1.12"
TEST_CASE("query_firmware reads a 0x99 frame -> major.minor", "[device]") {
    std::vector<uint8_t> inbound = {0x02, 0x99, 1, 12, 0, 0, 0};
    SimulatorByteTransport t(inbound);
    AdsProtocolDevice dev(t, 500.0);
    REQUIRE(dev.query_firmware() == "1.12");
    REQUIRE(t.last_written() == build_cmd(0x99, 0, 0));
}

TEST_CASE("query_firmware with no response returns the fallback", "[device]") {
    SimulatorByteTransport t({});  // empty inbound -> read_frame yields no 0x99
    AdsProtocolDevice dev(t, 500.0);
    REQUIRE(dev.query_firmware().rfind("no firmware response", 0) == 0);
}
