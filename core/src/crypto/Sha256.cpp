#include "ads1292/crypto/Sha256.h"
#include "picosha2.h"

namespace ads1292 {
std::string sha256_hex(const std::string& data) {
  return picosha2::hash256_hex_string(data);
}
std::string sha256_hex(const uint8_t* data, std::size_t len) {
  return picosha2::hash256_hex_string(data, data + len);
}
}  // namespace ads1292
