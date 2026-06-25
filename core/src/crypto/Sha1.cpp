// core/src/crypto/Sha1.cpp
#include "ads1292/crypto/Sha1.h"
#include <cstdint>
#include <cstdio>
#include <vector>

namespace ads1292 {
namespace {
inline uint32_t rotl(uint32_t v, int n) { return (v << n) | (v >> (32 - n)); }
}  // namespace

std::string sha1_hex(const std::string& data) {
  uint32_t h0 = 0x67452301, h1 = 0xEFCDAB89, h2 = 0x98BADCFE, h3 = 0x10325476, h4 = 0xC3D2E1F0;

  std::vector<uint8_t> msg(data.begin(), data.end());
  const uint64_t bit_len = static_cast<uint64_t>(msg.size()) * 8u;
  msg.push_back(0x80);
  while (msg.size() % 64 != 56) msg.push_back(0x00);
  for (int i = 7; i >= 0; --i) msg.push_back(static_cast<uint8_t>((bit_len >> (i * 8)) & 0xFF));

  for (size_t chunk = 0; chunk < msg.size(); chunk += 64) {
    uint32_t w[80];
    for (int i = 0; i < 16; ++i) {
      w[i] = (static_cast<uint32_t>(msg[chunk + i * 4]) << 24) |
             (static_cast<uint32_t>(msg[chunk + i * 4 + 1]) << 16) |
             (static_cast<uint32_t>(msg[chunk + i * 4 + 2]) << 8) |
             (static_cast<uint32_t>(msg[chunk + i * 4 + 3]));
    }
    for (int i = 16; i < 80; ++i) w[i] = rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);

    uint32_t a = h0, b = h1, c = h2, d = h3, e = h4;
    for (int i = 0; i < 80; ++i) {
      uint32_t f, k;
      if (i < 20) { f = (b & c) | ((~b) & d); k = 0x5A827999; }
      else if (i < 40) { f = b ^ c ^ d; k = 0x6ED9EBA1; }
      else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC; }
      else { f = b ^ c ^ d; k = 0xCA62C1D6; }
      uint32_t tmp = rotl(a, 5) + f + e + k + w[i];
      e = d; d = c; c = rotl(b, 30); b = a; a = tmp;
    }
    h0 += a; h1 += b; h2 += c; h3 += d; h4 += e;
  }

  char out[41];
  std::snprintf(out, sizeof(out), "%08x%08x%08x%08x%08x", h0, h1, h2, h3, h4);
  return std::string(out, 40);
}
}  // namespace ads1292
