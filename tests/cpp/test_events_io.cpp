// tests/cpp/test_events_io.cpp
#include "catch.hpp"
#include "ads1292/io/EventsIo.h"
#include <filesystem>
#include <fstream>
#include <iterator>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }

TEST_CASE("read golden events.json", "[sidecar]") {
  auto evs = io::read_events_json(fx("events.json"));
  REQUIRE(evs.size() >= 1);
  REQUIRE(evs[0].label == "motion");
  REQUIRE(evs[0].timestamp_seconds == Approx(5.0));
  REQUIRE(evs[0].duration_seconds == Approx(3.0));     // interval 5..8
  REQUIRE(evs[0].notes == "subject moved arm");
}
TEST_CASE("events round-trip preserves markers", "[sidecar]") {
  std::vector<EventMarker> in = { EventMarker{2.0,"a","n1",0.0}, EventMarker{4.0,"b","",1.5} };
  auto p = (std::filesystem::temp_directory_path() / "p7b_events.json").string();
  io::write_events_json(p, in, 500.0);
  auto back = io::read_events_json(p);
  REQUIRE(back.size() == 2);
  REQUIRE(back[0].label == "a"); REQUIRE(back[0].timestamp_seconds == Approx(2.0));
  REQUIRE(back[1].duration_seconds == Approx(1.5));
}
TEST_CASE("written events.json carries the schema + event_id", "[sidecar]") {
  std::vector<EventMarker> in = { EventMarker{5.0,"motion","subject moved arm",3.0} };
  auto p = (std::filesystem::temp_directory_path() / "p7b_events_schema.json").string();
  io::write_events_json(p, in, 500.0);
  std::ifstream f(p); std::string s((std::istreambuf_iterator<char>(f)), {});
  REQUIRE(s.find("ads1292-event-annotations-v1") != std::string::npos);
  REQUIRE(s.find("evt-0002500-0004000-motion-") != std::string::npos);   // event_id prefix from P4 EventId
  REQUIRE(s.find("\"event_type\": \"interval\"") != std::string::npos);
}
