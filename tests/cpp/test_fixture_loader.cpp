#include "catch.hpp"
#include "FixtureLoader.h"

using ads1292test::hex_to_bytes;
using ads1292test::load_device_fixture;

TEST_CASE("hex_to_bytes parses byte pairs", "[fixture]") {
  auto b = hex_to_bytes("0293ff");
  REQUIRE(b.size() == 3);
  REQUIRE(b[0] == 0x02);
  REQUIRE(b[1] == 0x93);
  REQUIRE(b[2] == 0xff);
}

TEST_CASE("loads a nominal stream device fixture", "[fixture]") {
  auto fx = load_device_fixture("device_parser/stream_payload_nominal.json");
  REQUIRE(fx.name == "stream_payload_nominal");
  REQUIRE(fx.payload.size() == 61);
  REQUIRE(fx.sample_rate_hz == Approx(500.0));
  REQUIRE(fx.start_index == 0);
  REQUIRE_FALSE(fx.expects_error);
  REQUIRE(fx.expected_samples.size() == 14);
}

TEST_CASE("loads an error device fixture", "[fixture]") {
  auto fx = load_device_fixture("device_parser/stream_bad_trailer.json");
  REQUIRE(fx.expects_error);
  REQUIRE(fx.error_message_contains == "trailer");
}
