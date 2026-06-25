#include "FixtureLoader.h"
#include <fstream>
#include <stdexcept>

namespace ads1292test {

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
  if (hex.size() % 2 != 0) {
    throw std::invalid_argument("hex string has odd length");
  }
  std::vector<uint8_t> out;
  out.reserve(hex.size() / 2);
  for (size_t i = 0; i < hex.size(); i += 2) {
    out.push_back(static_cast<uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
  }
  return out;
}

DeviceFixture load_device_fixture(const std::string& relpath) {
  std::string full = std::string(FIXTURE_DIR) + "/" + relpath;
  std::ifstream in(full);
  if (!in) {
    throw std::runtime_error("cannot open fixture: " + full);
  }
  nlohmann::json j;
  in >> j;

  DeviceFixture fx;
  fx.name = j.at("name").get<std::string>();
  const auto& input = j.at("input");
  fx.payload = hex_to_bytes(input.at("payload_hex").get<std::string>());
  fx.start_timestamp = input.at("start_timestamp").get<double>();
  fx.sample_rate_hz = input.at("sample_rate_hz").get<double>();
  fx.start_index = input.at("start_index").get<int>();

  const auto& output = j.at("output");
  if (output.contains("raises")) {
    fx.expects_error = true;
    fx.error_message_contains = output.at("message_contains").get<std::string>();
  } else {
    fx.expects_error = false;
    fx.expected_samples = output.at("samples");
  }
  return fx;
}

}  // namespace ads1292test
