// tests/cpp/test_display_filters.cpp
#include "catch.hpp"
#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/Filtfilt.h"
using namespace ads1292::dsp;
TEST_CASE("apply_software_filters: bandpass_enabled returns the QRS bandpass", "[live]") {
  std::vector<double> v(600); for (size_t i=0;i<v.size();++i) v[i] = std::sin(0.1*i)*30.0;
  SoftwareFilterSettings s; s.bandpass_enabled = true;
  REQUIRE(apply_software_filters(v, 500.0, s) == bandpass(v, 500.0));   // exact same vector
}
TEST_CASE("apply_software_filters: none enabled returns input unchanged", "[live]") {
  std::vector<double> v = {1,2,3,4,5};
  REQUIRE(apply_software_filters(v, 500.0, SoftwareFilterSettings{}) == v);
}
TEST_CASE("apply_software_filters: hp+notch composes highpass then notch", "[live]") {
  std::vector<double> v(600); for (size_t i=0;i<v.size();++i) v[i]=i%7;
  SoftwareFilterSettings s; s.highpass_enabled=true; s.notch_enabled=true;
  auto expect = notch(highpass(v, 500.0, 0.5), 500.0, 60.0);
  REQUIRE(apply_software_filters(v, 500.0, s) == expect);
}
