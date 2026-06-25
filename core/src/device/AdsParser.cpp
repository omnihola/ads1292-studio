// core/src/device/AdsParser.cpp
#include "ads1292/device/AdsParser.h"
#include <cmath>
#include "ads1292/device/ByteDecode.h"

namespace ads1292 {
namespace {
constexpr uint8_t kEnd = 0x03;
constexpr uint8_t kStreamTrailerLf = 0x0A;

// round-half-to-even-ish at 6 decimals; matches Python round(x, 6) for the
// exact decimal timestamps produced here (no halfway cases at 1e-6).
double round6(double x) { return std::round(x * 1e6) / 1e6; }
}  // namespace

std::vector<StreamSample> parse_stream_payload(const std::vector<uint8_t>& payload,
                                               double start_timestamp,
                                               double sample_rate_hz,
                                               int start_index) {
  if (payload.size() < 61) {
    throw AdsParseError("stream payload too short: " + std::to_string(payload.size()) +
                        " bytes");
  }
  uint8_t t0 = payload[payload.size() - 2];
  uint8_t t1 = payload[payload.size() - 1];
  bool trailer_ok = (t0 == kEnd && t1 == kEnd) || (t0 == kEnd && t1 == kStreamTrailerLf);
  if (!trailer_ok) {
    throw AdsParseError("bad stream trailer");
  }
  const int board_heart_rate = payload[0];
  const int board_respiration_rate = payload[1];
  const int status_byte = payload[2];

  std::vector<StreamSample> samples;
  samples.reserve(14);
  for (int i = 0; i < 14; ++i) {
    const size_t base = 3 + static_cast<size_t>(i) * 4;
    StreamSample s;
    s.timestamp = round6(start_timestamp +
                         static_cast<double>(start_index + i) / sample_rate_hz);
    s.ch1 = int16_le(payload[base], payload[base + 1]);
    s.ch2 = int16_le(payload[base + 2], payload[base + 3]);
    s.board_heart_rate = board_heart_rate;
    s.board_respiration_rate = board_respiration_rate;
    s.status_byte = status_byte;
    // sample_index intentionally left unset (matches Python stream parser)
    samples.push_back(s);
  }
  return samples;
}

std::vector<RawSample> parse_acquire_payload(const std::vector<uint8_t>& /*payload*/,
                                             double /*start_timestamp*/,
                                             double /*sample_rate_hz*/,
                                             int /*start_index*/) {
  // Implemented in Task 7.
  throw AdsParseError("parse_acquire_payload not implemented");
}

}  // namespace ads1292
