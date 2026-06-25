#include "catch.hpp"
#include "ads1292/acq/AdsFraming.h"
#include "ads1292/acq/SimulatorByteTransport.h"
#include "ads1292/device/AdsParser.h"
#include <vector>

using namespace ads1292;
using namespace ads1292::acq;

namespace {
// a valid 61-byte stream payload: 3 header + 14*4 + trailer {0x03,0x03}
std::vector<uint8_t> stream_payload() {
  std::vector<uint8_t> p = {72, 18, 0x05};
  for (int i = 0; i < 14; ++i) { p.push_back(100 + i); p.push_back(0); p.push_back(0x38); p.push_back(0xFF); }
  p.push_back(0x03); p.push_back(0x03);
  return p;
}
}  // namespace

TEST_CASE("build_cmd produces the 7-byte packet", "[acq]") {
  auto pkt = build_cmd(0x93, 0, 0);
  REQUIRE(pkt == std::vector<uint8_t>{0x02, 0x93, 0x00, 0x00, 0x03, 0x03, 0x0A});
}

TEST_CASE("read_frame extracts a stream frame after START", "[acq]") {
  std::vector<uint8_t> bytes = {0xAA, 0x02, 0x93};  // junk, START, type
  auto pl = stream_payload();
  bytes.insert(bytes.end(), pl.begin(), pl.end());
  SimulatorByteTransport t(bytes);
  Frame f = read_frame(t);
  REQUIRE(f.ok);
  REQUIRE(f.type == 0x93);
  REQUIRE(f.payload.size() == 61);
  auto samples = parse_stream_payload(f.payload, 0.0, 500.0, 0);
  REQUIRE(samples.size() == 14);
  REQUIRE(samples[0].ch1 == 100);
}
