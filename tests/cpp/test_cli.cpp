// tests/cpp/test_cli.cpp
#include "catch.hpp"
#include "ads1292/cli/Cli.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/model/StreamSample.h"
#include <sstream>
#include <filesystem>
#include <cmath>
using namespace ads1292;
namespace {
std::string write_clean(const std::string& name) {
  std::vector<StreamSample> rec;
  for (int i=0;i<5000;++i){ StreamSample s; double t=i/500.0, v=0.0;
    for(double bt=0.2; bt<10.0; bt+=60.0/72.0){ double d=t-bt; v+=300.0*std::exp(-(d*d)/(2*0.01*0.01)); }
    s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s); }
  auto p = (std::filesystem::temp_directory_path() / name).string();
  io::write_recording_csv(p, rec); return p;
}
}
TEST_CASE("run_qc on a clean recording passes (exit 0)", "[cli]") {
  cli::QcOptions opt; opt.csv_path = write_clean("p7a_qc_clean.csv");
  std::ostringstream out;
  int code = cli::run_qc(out, opt);
  REQUIRE(code == 0);
  REQUIRE(out.str().find("quality_gate=Pass") != std::string::npos);
  REQUIRE(out.str().find("ecg_source=") != std::string::npos);
}
TEST_CASE("run_qc on a too-short recording fails (exit 2)", "[cli]") {
  std::vector<StreamSample> rec; for (int i=0;i<600;++i){ StreamSample s; s.ch2=0; s.ch1=0; s.status_byte=0; rec.push_back(s);} // ~1.2s flat
  auto p = (std::filesystem::temp_directory_path() / "p7a_qc_short.csv").string();
  io::write_recording_csv(p, rec);
  cli::QcOptions opt; opt.csv_path = p;
  std::ostringstream out;
  int code = cli::run_qc(out, opt);
  REQUIRE(code == 2);
  REQUIRE(out.str().find("quality_gate=Fail") != std::string::npos);
  REQUIRE(out.str().find("failure=") != std::string::npos);
}
