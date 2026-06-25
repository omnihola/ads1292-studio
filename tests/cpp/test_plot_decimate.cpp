// tests/cpp/test_plot_decimate.cpp
#include "catch.hpp"
#include "ads1292/view/PlotDecimate.h"
using namespace ads1292::view;
TEST_CASE("smooth_for_plot: window<=1 or short returns input", "[live]") {
  std::vector<double> v={1,2,3};
  REQUIRE(smooth_for_plot(v,1)==v);
  REQUIRE(smooth_for_plot(v,5)==v);   // size<window
}
TEST_CASE("smooth_for_plot: moving average preserves length", "[live]") {
  std::vector<double> v={0,0,0,10,0,0,0};
  auto s = smooth_for_plot(v, 3);
  REQUIRE(s.size()==v.size());
  REQUIRE(s[3] == Approx(10.0/3.0));   // centered avg of {0,10,0}
}
TEST_CASE("decimate_extrema_for_plot keeps endpoints + per-bin min/max", "[live]") {
  std::vector<double> x(100), y(100); for (int i=0;i<100;++i){x[i]=i; y[i]=(i==50)?99.0:(double)(i%3);}
  std::vector<double> ox, oy; decimate_extrema_for_plot(x,y,10,ox,oy);
  REQUIRE(ox.front()==0); REQUIRE(ox.back()==99);
  REQUIRE(std::find(oy.begin(),oy.end(),99.0) != oy.end());   // the spike survives
}
TEST_CASE("decimate_for_plot returns input when small", "[live]") {
  std::vector<double> x={0,1,2}, y={3,4,5}, ox, oy; decimate_for_plot(x,y,10,ox,oy);
  REQUIRE(ox==x); REQUIRE(oy==y);
}
