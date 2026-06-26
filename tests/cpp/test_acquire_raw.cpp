// tests/cpp/test_acquire_raw.cpp
// Regression tests for B2 (wall-clock timestamp) and B3 (variable-length ACK read).
//
// Oracle: device.py acquire_raw_samples
//   - start_timestamp = time.time() captured BEFORE write_cmd (B2)
//   - ACK read via _read_frame_until_end_by — variable length, not fixed 51 bytes (B3)
//
// Wire format under test (count=8):
//   ACK frame:  {0x02, 0x94, 0x00, 0x08, 0x03}          (5 bytes total)
//   Data frame: {0x02, 0x94} + 51-byte acquire payload   (53 bytes total)
//
// OLD code (read_frame for ACK) consumes the ACK + start of the data frame in
// one 51-byte read, desynchronising the stream → throws "acquire underrun".
// NEW code (read_frame_until_end for ACK) reads exactly {0x00,0x08}, then
// read_frame reads the 51-byte data payload correctly.
#include "catch.hpp"
#include "ads1292/acq/AdsProtocolDevice.h"
#include "ads1292/acq/AdsFraming.h"
#include "ads1292/acq/SimulatorByteTransport.h"
#include <ctime>
#include <vector>

using namespace ads1292::acq;
using namespace ads1292;

namespace {

// Build the 51-byte acquire payload for 8 samples:
//   [0..1]  status word = 0x0000
//   [2..49] 8 * 6 bytes: ch1 = {0x00,0x00,0x01}, ch2 = {0x00,0x00,0x02}
//   [50]    END = 0x03
std::vector<uint8_t> acquire_payload_8() {
  std::vector<uint8_t> p;
  p.reserve(51);
  p.push_back(0x00); p.push_back(0x00);  // status
  for (int i = 0; i < 8; ++i) {
    p.push_back(0x00); p.push_back(0x00); p.push_back(0x01);  // ch1 = 1
    p.push_back(0x00); p.push_back(0x00); p.push_back(0x02);  // ch2 = 2
  }
  p.push_back(0x03);  // END trailer
  return p;
}

// Build complete wire bytes: short ACK + one 51-byte data frame
std::vector<uint8_t> build_wire_8() {
  std::vector<uint8_t> wire;
  // Short ACK (variable-length): START + 0x94 + count_hi + count_lo + END
  wire.push_back(0x02);  // kStart
  wire.push_back(0x94);  // type = CMD_ACQUIRE_DATA
  wire.push_back(0x00);  // count hi
  wire.push_back(0x08);  // count lo (= 8)
  wire.push_back(0x03);  // kEnd
  // Data frame: START + type + 51-byte payload
  wire.push_back(0x02);  // kStart
  wire.push_back(0x94);  // type
  auto payload = acquire_payload_8();
  wire.insert(wire.end(), payload.begin(), payload.end());
  return wire;
}

}  // namespace

TEST_CASE("acquire_raw: short-ACK + wall-clock timestamp (B2/B3)", "[acq]") {
  auto wire = build_wire_8();
  // Total wire: 5 (ACK) + 2 (data frame header) + 51 (payload) = 58 bytes
  REQUIRE(wire.size() == 58);

  SimulatorByteTransport t(wire);
  AdsProtocolDevice dev(t, 500.0);

  // With OLD code: read_frame reads 51 bytes as the ACK payload, desynchronises
  // the transport, and the data-frame read fails → throws AdsParseError.
  // With NEW code: read_frame_until_end reads the 5-byte ACK cleanly; then
  // read_frame reads the 53-byte data frame correctly.
  auto samples = dev.acquire_raw(8);

  REQUIRE(samples.size() == 8);

  // B2: timestamp must be wall-clock (> 0), not the hard-coded 0.0.
  REQUIRE(samples[0].timestamp > 0.0);

  // Spot-check the parsed channel values.
  REQUIRE(samples[0].ch1_raw24 == 1);
  REQUIRE(samples[0].ch2_raw24 == 2);
}

TEST_CASE("read_frame_until_end: variable-length payload without END byte", "[acq]") {
  // Transport contains: START + type + two payload bytes + END
  std::vector<uint8_t> raw = {0x02, 0x94, 0xAB, 0xCD, 0x03};
  SimulatorByteTransport t(raw);
  Frame f = read_frame_until_end(t);
  REQUIRE(f.ok);
  REQUIRE(f.type == 0x94);
  REQUIRE(f.payload.size() == 2);
  REQUIRE(f.payload[0] == 0xAB);
  REQUIRE(f.payload[1] == 0xCD);
}

TEST_CASE("read_frame_until_end: returns ok=false on end of input before END", "[acq]") {
  // Transport ends before END byte — simulate truncated stream
  std::vector<uint8_t> raw = {0x02, 0x94, 0xAB};  // no END
  SimulatorByteTransport t(raw);
  Frame f = read_frame_until_end(t);
  REQUIRE_FALSE(f.ok);
}
