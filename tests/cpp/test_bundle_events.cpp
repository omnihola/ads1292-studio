#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/model/EventMarker.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;

namespace {
json load_golden() {
  std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
  json j; in >> j; return j;
}
}  // namespace

TEST_CASE("events_payload reproduces the golden events section", "[bundle]") {
  std::vector<ads1292::EventMarker> events = {
      {0.02, "touch", "n1", 0.0}, {0.04, "motion", "n2", 0.03}};
  json got = ads1292::io::events_payload(events, 500.0);
  REQUIRE(got == load_golden().at("events"));
}
