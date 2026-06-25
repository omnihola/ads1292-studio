// core/include/ads1292/crypto/Sha1.h
#pragma once
#include <string>

namespace ads1292 {
// Lowercase 40-hex-char SHA-1 of the input bytes. Pure C++17, no external deps.
std::string sha1_hex(const std::string& data);
}  // namespace ads1292
