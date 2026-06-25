// core/include/ads1292/device/AdsParser.h
#pragma once
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/RawSample.h"

namespace ads1292 {

// Thrown for malformed frames (mirrors Python's ValueError on bad payloads).
struct AdsParseError : std::invalid_argument {
  explicit AdsParseError(const std::string& msg) : std::invalid_argument(msg) {}
};

std::vector<StreamSample> parse_stream_payload(const std::vector<uint8_t>& payload,
                                               double start_timestamp,
                                               double sample_rate_hz,
                                               int start_index);

std::vector<RawSample> parse_acquire_payload(const std::vector<uint8_t>& payload,
                                             double start_timestamp,
                                             double sample_rate_hz,
                                             int start_index);

}  // namespace ads1292
