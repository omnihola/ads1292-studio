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
// Write a ~10 s 72 bpm Gaussian-R-peak synthetic recording to an explicit path.
// Used by P7b-4 index/batch test cases.
void write_clean_recording(const std::string& path) {
  std::vector<StreamSample> rec;
  for (int i=0;i<5000;++i){ StreamSample s; double t=i/500.0, v=0.0;
    for(double bt=0.2; bt<10.0; bt+=60.0/72.0){ double d=t-bt; v+=300.0*std::exp(-(d*d)/(2*0.01*0.01)); }
    s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s); }
  io::write_recording_csv(path, rec);
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
TEST_CASE("run_report prints the metric summary (exit 0)", "[cli]") {
  ads1292::cli::ReportOptions opt; opt.csv_path = write_clean("p7a_report.csv");
  std::ostringstream out;
  REQUIRE(ads1292::cli::run_report(out, opt) == 0);
  REQUIRE(out.str().find("ecg_source=") != std::string::npos);
  REQUIRE(out.str().find("hr_median_bpm=") != std::string::npos);
  REQUIRE(out.str().find("quality=") != std::string::npos);
}
TEST_CASE("run_verify on the golden HDF5 recording is ok (exit 0)", "[cli]") {
  ads1292::cli::VerifyOptions opt; opt.h5_path = std::string(FIXTURE_DIR) + "/files/recording.h5";
  std::ostringstream out;
  REQUIRE(ads1292::cli::run_verify(out, opt) == 0);
  REQUIRE(out.str().find("ok=true") != std::string::npos);
}
TEST_CASE("run_index scans a directory and prints summary counters", "[cli]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b4_index";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  // one clean recording, no sidecars -> incomplete_record / action_complete_sidecars
  write_clean_recording((dir / "rec1.csv").string());
  ads1292::cli::IndexOptions opt; opt.root = dir.string(); opt.out_dir = (dir / "out").string();
  std::ostringstream o;
  int code = ads1292::cli::run_index(o, opt);
  REQUIRE(code == 0);
  REQUIRE(o.str().find("rows=1") != std::string::npos);
  REQUIRE(o.str().find("index_json=") != std::string::npos);
  REQUIRE(o.str().find("incomplete_records=1") != std::string::npos);
  REQUIRE(o.str().find("action_complete_sidecars=1") != std::string::npos);
  REQUIRE(std::filesystem::exists(std::filesystem::path(opt.out_dir) / "index.json"));
}
TEST_CASE("run_index on a non-directory prints the diagnostic", "[cli]") {
  ads1292::cli::IndexOptions opt;
  opt.root    = (std::filesystem::temp_directory_path() / "p7b4_nope_xyz").string();
  opt.out_dir = (std::filesystem::temp_directory_path() / "p7b4_o2").string();
  std::ostringstream o;
  REQUIRE(ads1292::cli::run_index(o, opt) == 0);
  REQUIRE(o.str().find("is not a directory") != std::string::npos);
  REQUIRE(o.str().find("rows=0") != std::string::npos);
}
