#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "nlohmann/json.hpp"

namespace ads1292test {

std::vector<uint8_t> hex_to_bytes(const std::string& hex);

struct DeviceFixture {
  std::string name;
  std::vector<uint8_t> payload;
  double start_timestamp = 0.0;
  double sample_rate_hz = 0.0;
  int start_index = 0;
  bool expects_error = false;
  std::string error_message_contains;
  nlohmann::json expected_samples;  // JSON array; empty when expects_error
};

// relpath is relative to FIXTURE_DIR, e.g. "device_parser/stream_payload_nominal.json".
DeviceFixture load_device_fixture(const std::string& relpath);

}  // namespace ads1292test
