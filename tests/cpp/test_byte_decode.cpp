// tests/cpp/test_byte_decode.cpp
#include "catch.hpp"
#include "ads1292/device/ByteDecode.h"

using ads1292::int16_le;
using ads1292::int24_be;

TEST_CASE("int16_le decodes signed little-endian", "[decode]") {
  REQUIRE(int16_le(0x64, 0x00) == 100);      // 0x0064
  REQUIRE(int16_le(0x38, 0xFF) == -200);     // 0xFF38 -> -200
  REQUIRE(int16_le(0x00, 0x80) == -32768);   // most-negative
  REQUIRE(int16_le(0xFF, 0x7F) == 32767);    // most-positive
}

TEST_CASE("int24_be decodes signed big-endian", "[decode]") {
  REQUIRE(int24_be(0x00, 0x03, 0xE8) == 1000);     // 0x0003E8
  REQUIRE(int24_be(0xFF, 0xF8, 0x30) == -2000);    // 0xFFF830 -> -2000
  REQUIRE(int24_be(0x80, 0x00, 0x00) == -8388608); // most-negative
  REQUIRE(int24_be(0x7F, 0xFF, 0xFF) == 8388607);  // most-positive
}
