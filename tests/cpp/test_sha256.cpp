#include "catch.hpp"
#include "ads1292/crypto/Sha256.h"

using ads1292::sha256_hex;

TEST_CASE("sha256 standard vectors", "[crypto]") {
  REQUIRE(sha256_hex("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
  REQUIRE(sha256_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
}

TEST_CASE("sha256 over a byte buffer", "[crypto]") {
  const uint8_t bytes[] = {0x61, 0x62, 0x63};  // "abc"
  REQUIRE(sha256_hex(bytes, 3) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
}
