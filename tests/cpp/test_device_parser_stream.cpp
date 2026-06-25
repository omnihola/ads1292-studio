// tests/cpp/test_device_parser_stream.cpp
#include "catch.hpp"
#include "ads1292/device/AdsParser.h"
#include "FixtureLoader.h"

using ads1292::parse_stream_payload;
using ads1292::AdsParseError;
using ads1292test::load_device_fixture;

namespace {
void check_stream_against_fixture(const std::string& relpath) {
  auto fx = load_device_fixture(relpath);
  auto got = parse_stream_payload(fx.payload, fx.start_timestamp,
                                  fx.sample_rate_hz, fx.start_index);
  REQUIRE(got.size() == fx.expected_samples.size());
  for (size_t i = 0; i < got.size(); ++i) {
    const auto& exp = fx.expected_samples[i];
    INFO("sample " << i << " in " << relpath);
    CHECK(got[i].ch1 == exp.at("ch1").get<int>());
    CHECK(got[i].ch2 == exp.at("ch2").get<int>());
    CHECK(got[i].board_heart_rate == exp.at("board_heart_rate").get<int>());
    CHECK(got[i].board_respiration_rate == exp.at("board_respiration_rate").get<int>());
    CHECK(got[i].status_byte == exp.at("status_byte").get<int>());
    CHECK(got[i].lead_off_bits() == exp.at("lead_off_bits").get<int>());
    CHECK(got[i].timestamp == Approx(exp.at("timestamp").get<double>()).margin(1e-9));
    CHECK(exp.at("sample_index").is_null());
    CHECK_FALSE(got[i].sample_index.has_value());
  }
}
}  // namespace

TEST_CASE("parse_stream_payload reproduces the nominal stream fixture", "[parser]") {
  check_stream_against_fixture("device_parser/stream_payload_nominal.json");
}

TEST_CASE("parse_stream_payload throws on a bad trailer", "[parser]") {
  auto fx = load_device_fixture("device_parser/stream_bad_trailer.json");
  REQUIRE(fx.expects_error);
  REQUIRE_THROWS_WITH(
      parse_stream_payload(fx.payload, fx.start_timestamp, fx.sample_rate_hz, fx.start_index),
      Catch::Contains(fx.error_message_contains));
}

TEST_CASE("parse_stream_payload throws on a too-short payload", "[parser]") {
  auto fx = load_device_fixture("device_parser/stream_too_short.json");
  REQUIRE(fx.expects_error);
  REQUIRE_THROWS_WITH(
      parse_stream_payload(fx.payload, fx.start_timestamp, fx.sample_rate_hz, fx.start_index),
      Catch::Contains(fx.error_message_contains));
}
