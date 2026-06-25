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

// ---- device-level tests (Task 2) ----
#include "ads1292/acq/AdsProtocolDevice.h"
#include "ads1292/acq/SimulatorDeviceSource.h"

TEST_CASE("AdsProtocolDevice reads a stream batch from a transport", "[acq]") {
  std::vector<uint8_t> bytes = {0x02, 0x93};
  // reuse the helper stream_payload() from earlier in this file
  auto pl = stream_payload();
  bytes.insert(bytes.end(), pl.begin(), pl.end());
  SimulatorByteTransport t(bytes);
  AdsProtocolDevice dev(t, 500.0);
  dev.start_stream();
  auto batch = dev.read_stream_batch();
  REQUIRE(batch.size() == 14);
  REQUIRE(batch[0].ch1 == 100);
  // start_stream wrote the streaming command
  REQUIRE(t.last_written() == build_cmd(0x93, 0, 0));
}

TEST_CASE("SimulatorDeviceSource yields deterministic batches", "[acq]") {
  SimulatorDeviceSource sim(/*stream_batches=*/3, /*raw_count=*/16);
  int total = 0;
  for (int i = 0; i < 3; ++i) total += static_cast<int>(sim.read_stream_batch().size());
  REQUIRE(total == 42);                 // 3 * 14
  REQUIRE(sim.read_stream_batch().empty());  // exhausted
  REQUIRE(sim.acquire_raw(16).size() == 16);
}
