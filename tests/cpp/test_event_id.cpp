// tests/cpp/test_event_id.cpp
#include "catch.hpp"
#include "ads1292/event/EventId.h"
#include "ads1292/model/EventMarker.h"

using namespace ads1292;

TEST_CASE("sample indices round timestamp*rate", "[event]") {
  EventSampleIndices p = event_sample_indices(EventMarker{0.02, "touch", "n1", 0.0}, 500.0);
  REQUIRE(p.start_sample_index == 10);
  REQUIRE(p.end_sample_index == 10);
  REQUIRE(p.duration_samples == 0);
  EventSampleIndices r = event_sample_indices(EventMarker{0.04, "motion", "n2", 0.03}, 500.0);
  REQUIRE(r.start_sample_index == 20);
  REQUIRE(r.end_sample_index == 35);
  REQUIRE(r.duration_samples == 15);
}

TEST_CASE("slug normalizes labels", "[event]") {
  REQUIRE(slug("Touch Electrode!") == "touch-electrode");
  REQUIRE(slug("   ") == "event");
}

TEST_CASE("event_id matches the golden format + digest", "[event]") {
  REQUIRE(event_id(EventMarker{0.02, "touch", "n1", 0.0}, 500.0) ==
          "evt-0000010-0000010-touch-c545bb80");
  REQUIRE(event_id(EventMarker{0.04, "motion", "n2", 0.03}, 500.0) ==
          "evt-0000020-0000035-motion-b06d78b7");
}
