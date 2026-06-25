// tests/cpp/test_h5_io.cpp
#include "catch.hpp"
#include "ads1292/io/H5Io.h"
#include <cstdio>
#include <string>

TEST_CASE("hdf5 smoke round-trip", "[h5]") {
  const std::string path = std::string(FIXTURE_DIR) + "/files/_smoke.h5";
  REQUIRE(ads1292::io::h5_smoke_roundtrip(path));
  std::remove(path.c_str());
}
