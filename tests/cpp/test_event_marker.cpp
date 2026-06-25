// tests/cpp/test_event_marker.cpp
#include "catch.hpp"
#include "ads1292/model/EventMarker.h"

using ads1292::EventMarker;

TEST_CASE("EventMarker normalizes negatives, trims, and defaults label", "[model]") {
  EventMarker e{-1.0, "  ", "  hi  ", -2.0};
  EventMarker n = e.normalized();
  REQUIRE(n.timestamp_seconds == Approx(0.0));
  REQUIRE(n.duration_seconds == Approx(0.0));
  REQUIRE(n.label == "event");   // empty/whitespace label -> "event"
  REQUIRE(n.notes == "hi");      // notes trimmed
}

TEST_CASE("EventMarker end_seconds and is_interval", "[model]") {
  EventMarker point{2.0, "touch", "", 0.0};
  REQUIRE(point.end_seconds() == Approx(2.0));
  REQUIRE_FALSE(point.is_interval());

  EventMarker range{2.0, "motion", "", 0.5};
  REQUIRE(range.end_seconds() == Approx(2.5));
  REQUIRE(range.is_interval());
}
