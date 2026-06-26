// test_bundle_events.cpp
// Verifies events_to_json reproduces the golden events section of the bundle.

#include "catch.hpp"
#include "ads1292/io/EventsIo.h"
#include "ads1292/model/EventMarker.h"
#include <nlohmann/json.hpp>
#include <fstream>
#include <vector>

namespace {

nlohmann::json load_golden() {
    std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
    nlohmann::json j;
    in >> j;
    return j;
}

}  // namespace

TEST_CASE("events_to_json reproduces the golden events section", "[bundle]") {
    std::vector<ads1292::EventMarker> events = {
        {0.02, "touch", "n1", 0.0}, {0.04, "motion", "n2", 0.03}};

    // Convert ordered_json → json for value comparison with the alphabetically-sorted golden.
    nlohmann::json got = ads1292::io::events_to_json(events, 500.0);
    REQUIRE(got == load_golden().at("events"));
}
