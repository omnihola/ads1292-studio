#pragma once
#include <cstdint>

namespace ads1292 {
// Signed 16-bit little-endian from (lo, hi). Mirrors Python device._int16_le.
inline int int16_le(uint8_t lo, uint8_t hi) {
  int value = (static_cast<int>(hi) << 8) | static_cast<int>(lo);
  if (value & 0x8000) value -= 0x10000;
  return value;
}

// Signed 24-bit big-endian from (b0, b1, b2). Mirrors Python device._int24_be.
inline int int24_be(uint8_t b0, uint8_t b1, uint8_t b2) {
  int value = (static_cast<int>(b0) << 16) | (static_cast<int>(b1) << 8) |
              static_cast<int>(b2);
  if (value & 0x800000) value -= 0x1000000;
  return value;
}
}  // namespace ads1292
