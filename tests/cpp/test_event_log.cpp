// tests/cpp/test_event_log.cpp
#include "catch.hpp"
#include "ads1292/view/EventLog.h"

using ads1292::view::EventLog;

TEST_CASE("add_point creates a zero-duration marker", "[events]") {
  EventLog log;
  log.add_point(1.5, "touch", "n");
  REQUIRE(log.events().size() == 1);
  REQUIRE(log.events()[0].timestamp_seconds == Approx(1.5));
  REQUIRE(log.events()[0].duration_seconds == Approx(0.0));
  REQUIRE_FALSE(log.events()[0].is_interval());
}

TEST_CASE("start_range + end_range creates an interval", "[events]") {
  EventLog log;
  log.start_range(2.0);
  REQUIRE(log.pending_range_start().has_value());
  REQUIRE(log.end_range(2.5, "motion", ""));
  REQUIRE(log.events().size() == 1);
  REQUIRE(log.events()[0].duration_seconds == Approx(0.5));
  REQUIRE(log.events()[0].is_interval());
  REQUIRE_FALSE(log.pending_range_start().has_value());   // cleared
}

TEST_CASE("end_range without a start fails", "[events]") {
  EventLog log;
  REQUIRE_FALSE(log.end_range(1.0, "x", ""));
}

TEST_CASE("remove_last and remove_at", "[events]") {
  EventLog log;
  log.add_point(1.0, "a", "");
  log.add_point(2.0, "b", "");
  REQUIRE(log.remove_at(0));
  REQUIRE(log.events().size() == 1);
  REQUIRE(log.events()[0].label == "b");
  REQUIRE(log.remove_last());
  REQUIRE(log.events().empty());
  REQUIRE_FALSE(log.remove_last());        // empty
  REQUIRE_FALSE(log.remove_at(5));         // out of range
}
