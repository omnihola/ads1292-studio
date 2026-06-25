// tests/cpp/test_sha1.cpp
#include "catch.hpp"
#include "ads1292/crypto/Sha1.h"

using ads1292::sha1_hex;

TEST_CASE("sha1 standard test vectors", "[crypto]") {
  REQUIRE(sha1_hex("") == "da39a3ee5e6b4b0d3255bfef95601890afd80709");
  REQUIRE(sha1_hex("abc") == "a9993e364706816aba3e25717850c26c9cd0d89d");
}

TEST_CASE("sha1 reproduces the event fingerprint digests", "[crypto]") {
  REQUIRE(sha1_hex("10|10|point|touch|n1").substr(0, 8) == "c545bb80");
  REQUIRE(sha1_hex("20|35|interval|motion|n2").substr(0, 8) == "b06d78b7");
}
