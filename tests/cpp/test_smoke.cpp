// tests/cpp/test_smoke.cpp
#include "catch.hpp"
#include "ads1292/core_version.h"
#include "nlohmann/json.hpp"

TEST_CASE("core links and reports its version", "[smoke]") {
    REQUIRE(std::string(ads1292::core_version()) == "0.1.0");
}

TEST_CASE("nlohmann json is available", "[smoke]") {
    auto j = nlohmann::json::parse("{\"a\":1}");
    REQUIRE(j.at("a").get<int>() == 1);
}
