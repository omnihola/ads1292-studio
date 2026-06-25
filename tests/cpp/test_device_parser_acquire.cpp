// tests/cpp/test_device_parser_acquire.cpp
#include "catch.hpp"
#include "ads1292/device/AdsParser.h"
#include "FixtureLoader.h"

using ads1292::parse_acquire_payload;
using ads1292test::load_device_fixture;

TEST_CASE("parse_acquire_payload reproduces the nominal acquire fixture", "[parser]") {
  auto fx = load_device_fixture("device_parser/acquire_payload_nominal.json");
  auto got = parse_acquire_payload(fx.payload, fx.start_timestamp,
                                   fx.sample_rate_hz, fx.start_index);
  REQUIRE(got.size() == fx.expected_samples.size());  // 8 raw samples
  for (size_t i = 0; i < got.size(); ++i) {
    const auto& exp = fx.expected_samples[i];
    INFO("raw sample " << i);
    CHECK(got[i].ch1_raw24 == exp.at("ch1_raw24").get<int>());
    CHECK(got[i].ch2_raw24 == exp.at("ch2_raw24").get<int>());
    CHECK(got[i].status_byte == exp.at("status_byte").get<int>());
    CHECK(got[i].lead_off_bits() == exp.at("lead_off_bits").get<int>());
    CHECK(got[i].sample_index == exp.at("sample_index").get<int>());
    CHECK(got[i].timestamp == Approx(exp.at("timestamp").get<double>()).margin(1e-9));
  }
}

TEST_CASE("parse_acquire_payload throws on a bad trailer", "[parser]") {
  auto fx = load_device_fixture("device_parser/acquire_bad_trailer.json");
  REQUIRE(fx.expects_error);
  REQUIRE_THROWS_WITH(
      parse_acquire_payload(fx.payload, fx.start_timestamp, fx.sample_rate_hz, fx.start_index),
      Catch::Contains(fx.error_message_contains));
}
