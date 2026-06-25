// tests/cpp/test_live_render.cpp
#include "catch.hpp"
#include "ads1292/view/LiveRender.h"
#include <cmath>
using namespace ads1292::view; using namespace ads1292::dsp;
namespace {
// 6 s @ 500 Hz synthetic ECG-ish on ch2 (Gaussian R-peaks ~72 bpm), flat-ish ch1
void make_window(std::vector<int>& idx, std::vector<double>& ch1, std::vector<double>& ch2, std::vector<int>& st) {
  const int n=3000; const double sr=500.0;
  for (int i=0;i<n;++i){ idx.push_back(i); ch1.push_back(0.0); st.push_back(0);
    double t=i/sr, v=0.0; for(double bt=0.2; bt<6.0; bt+=60.0/72.0){ double d=t-bt; v+=200.0*std::exp(-(d*d)/(2*0.01*0.01)); }
    ch2.push_back(v); }
}
}
TEST_CASE("build_live_render_frame: clean window detects peaks + HR + SNR", "[live]") {
  std::vector<int> idx, st; std::vector<double> ch1, ch2; make_window(idx,ch1,ch2,st);
  EcgDisplaySettings ds; SoftwareFilterSettings fs;  // window 8s, no filters
  auto f = build_live_render_frame(idx,ch1,ch2,st,ds,fs,"CH2",500.0,5,2000,false);
  REQUIRE(f.valid);
  REQUIRE(f.peaks.size() >= 5);              // ~7 beats in 6 s
  REQUIRE(f.heart_rate.median_bpm > 40.0);
  REQUIRE(f.snr.valid);
  REQUIRE(f.plot_ecg.size() <= 2000);
}
TEST_CASE("build_live_render_frame: lead-off window detects no peaks", "[live]") {
  std::vector<int> idx, st; std::vector<double> ch1, ch2; make_window(idx,ch1,ch2,st);
  for (auto& s : st) s = 0x0F;               // all lead-off
  auto f = build_live_render_frame(idx,ch1,ch2,st,EcgDisplaySettings{},SoftwareFilterSettings{},"CH2",500.0,5,2000,false);
  REQUIRE(f.valid);
  REQUIRE(f.peaks.empty());                  // contact gate blocks detection
}
TEST_CASE("build_live_render_frame: bad sr returns invalid", "[live]") {
  std::vector<int> idx={0}; std::vector<double> c={0.0}; std::vector<int> st={0};
  auto f = build_live_render_frame(idx,c,c,st,EcgDisplaySettings{},SoftwareFilterSettings{},"CH2",0.0,5,2000,false);
  REQUIRE_FALSE(f.valid);
}
TEST_CASE("build_live_render_frame: gain scales ECG but not respiration", "[live]") {
  std::vector<int> idx, st; std::vector<double> ch1, ch2; make_window(idx,ch1,ch2,st);
  for (size_t i = 0; i < ch1.size(); ++i) ch1[i] = 5.0 * std::sin(0.05 * (double)i);
  EcgDisplaySettings g1; g1.gain = 1.0;
  EcgDisplaySettings g3; g3.gain = 3.0;
  SoftwareFilterSettings fs;
  auto f1 = build_live_render_frame(idx, ch1, ch2, st, g1, fs, "CH2", 500.0, 5, 2000, false);
  auto f3 = build_live_render_frame(idx, ch1, ch2, st, g3, fs, "CH2", 500.0, 5, 2000, false);
  REQUIRE(f1.valid); REQUIRE(f3.valid);
  // resp identical across gains (unity), ECG scaled ~3x:
  REQUIRE(f3.visible_resp_plot == f1.visible_resp_plot);
  REQUIRE(f3.visible_ecg[100] == Approx(3.0 * f1.visible_ecg[100]).margin(1e-9));
}
