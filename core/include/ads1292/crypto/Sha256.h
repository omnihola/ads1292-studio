#pragma once
#include <cstddef>
#include <cstdint>
#include <string>

namespace ads1292 {
std::string sha256_hex(const std::string& data);
std::string sha256_hex(const uint8_t* data, std::size_t len);
}  // namespace ads1292
