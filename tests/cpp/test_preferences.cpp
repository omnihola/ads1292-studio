// tests/cpp/test_preferences.cpp
// Unit tests for ads1292::gui::Preferences struct + to_map/from_map.
// No Qt dependency — pure struct + std::map.

#include "catch.hpp"
#include "ads1292/gui/Preferences.h"

using ads1292::gui::Preferences;

TEST_CASE("Preferences defaults", "[preferences]") {
    Preferences p;
    REQUIRE(p.port     == "");
    REQUIRE(p.mode     == "Live Monitor");
    REQUIRE(p.save_csv == true);
    REQUIRE(p.save_h5  == true);
    REQUIRE_FALSE(p.save_xlsx);
    REQUIRE(p.window   == "8 s");
    REQUIRE(p.gain     == "1x");
    REQUIRE(p.speed    == "25 mm/s");
}

TEST_CASE("Preferences round-trip via to_map/from_map", "[preferences]") {
    Preferences a;
    a.port      = "/dev/cu.x";
    a.save_xlsx = true;
    a.window    = "4 s";

    auto m = a.to_map();
    auto b = Preferences::from_map(m);

    REQUIRE(b.port      == "/dev/cu.x");
    REQUIRE(b.save_xlsx == true);
    REQUIRE(b.window    == "4 s");
    REQUIRE(b.save_h5   == true);   // default true survives round-trip
    REQUIRE(b.save_csv  == true);   // default true survives round-trip
    REQUIRE(b.mode      == "Live Monitor");
}

TEST_CASE("Preferences from_map with missing keys keeps defaults", "[preferences]") {
    auto c = Preferences::from_map({{"port", "/dev/y"}});
    REQUIRE(c.port   == "/dev/y");
    REQUIRE(c.mode   == "Live Monitor");
    REQUIRE(c.save_h5 == true);
    REQUIRE_FALSE(c.save_xlsx);
    REQUIRE(c.window == "8 s");
}

TEST_CASE("Preferences from_map bool parsing", "[preferences]") {
    // "true" → true
    REQUIRE(Preferences::from_map({{"save_xlsx", "true"}}).save_xlsx == true);
    // "false" → false
    REQUIRE_FALSE(Preferences::from_map({{"save_h5", "false"}}).save_h5);
    // unknown string → false
    REQUIRE_FALSE(Preferences::from_map({{"save_xlsx", "nonsense"}}).save_xlsx);
    // truthy aliases
    REQUIRE(Preferences::from_map({{"save_xlsx", "1"}}).save_xlsx);
    REQUIRE(Preferences::from_map({{"save_xlsx", "yes"}}).save_xlsx);
    REQUIRE(Preferences::from_map({{"save_xlsx", "on"}}).save_xlsx);
    // case-insensitive
    REQUIRE(Preferences::from_map({{"save_xlsx", "True"}}).save_xlsx);
    REQUIRE(Preferences::from_map({{"save_xlsx", "YES"}}).save_xlsx);
}

TEST_CASE("Preferences to_map has 8 entries and encodes bools as strings", "[preferences]") {
    Preferences a;
    a.port      = "/dev/cu.x";
    a.save_xlsx = true;
    a.window    = "4 s";

    auto m = a.to_map();
    REQUIRE(m.size()              == 8);
    REQUIRE(m.at("save_xlsx")     == "true");
    REQUIRE(m.at("save_h5")      == "true");
    REQUIRE(m.at("save_csv")     == "true");
    REQUIRE(m.at("port")         == "/dev/cu.x");
    REQUIRE(m.at("mode")         == "Live Monitor");
    REQUIRE(m.at("window")       == "4 s");
    REQUIRE(m.at("gain")         == "1x");
    REQUIRE(m.at("speed")        == "25 mm/s");
}
