// tests/cpp/test_cli.cpp
#include "catch.hpp"
#include "ads1292/cli/Cli.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/StreamSample.h"
#include <sstream>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <cmath>
#include <cstdio>
#include <string>
#include <sys/wait.h>
using namespace ads1292;

// ---------------------------------------------------------------------------
// Subprocess helper: runs cmd (shell string), merges stderr into stdout,
// returns {exit_code, combined_output}.
// ---------------------------------------------------------------------------
namespace {
std::pair<int, std::string> run_cmd(const std::string& cmd) {
    std::string full = cmd + " 2>&1";
    FILE* pipe = popen(full.c_str(), "r");
    if (!pipe) return {-1, ""};
    std::string out;
    char buf[256];
    while (fgets(buf, sizeof(buf), pipe)) out += buf;
    int status = pclose(pipe);
    int code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
    return {code, out};
}
}
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
TEST_CASE("run_batch aggregates recordings and groups by electrode", "[cli]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b4_batch";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  std::vector<std::string> inputs;
  for (auto stem : {"a","b"}) {
    auto csv = (dir / (std::string(stem)+".csv")).string();
    write_clean_recording(csv);
    ads1292::SessionMetadata m; m.electrode="MOTAC";
    ads1292::io::write_metadata_json((dir/(std::string(stem)+".json")).string(), m);
    inputs.push_back(csv);
  }
  ads1292::cli::BatchOptions opt; opt.inputs = inputs;
  std::ostringstream o;
  int code = ads1292::cli::run_batch(o, opt);
  REQUIRE(code == 0);
  REQUIRE(o.str().find("rows=2") != std::string::npos);
  REQUIRE(o.str().find("groups=1") != std::string::npos);
  REQUIRE(o.str().find("group=MOTAC") != std::string::npos);
}
TEST_CASE("run_batch on a directory input expands to its CSVs", "[cli]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b4_batch_dir";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  write_clean_recording((dir/"x.csv").string());
  ads1292::cli::BatchOptions opt; opt.inputs = { dir.string() };   // directory input
  std::ostringstream o;
  REQUIRE(ads1292::cli::run_batch(o, opt) == 0);
  REQUIRE(o.str().find("rows=1") != std::string::npos);
}

// ---------------------------------------------------------------------------
// C7 regression: run_qc/run_report errors must go to stderr, NOT stdout.
// Oracle: cli.py errors (from _require_recording_csv / SystemExit) → stderr.
// ---------------------------------------------------------------------------
TEST_CASE("run_qc error goes to stderr not stdout (C7)", "[cli]") {
  ads1292::cli::QcOptions opt;
  opt.csv_path = "/tmp/p9_c7_does_not_exist_qc.csv";
  std::ostringstream stdout_buf;
  std::ostringstream stderr_buf;
  // Redirect cerr so we can inspect it.
  auto* old_cerr = std::cerr.rdbuf(stderr_buf.rdbuf());
  int code = ads1292::cli::run_qc(stdout_buf, opt);
  std::cerr.rdbuf(old_cerr);
  REQUIRE(code == 1);
  // Error must NOT appear in stdout.
  REQUIRE(stdout_buf.str().find("error") == std::string::npos);
  // Error must appear in stderr.
  REQUIRE(!stderr_buf.str().empty());
}

TEST_CASE("run_report error goes to stderr not stdout (C7)", "[cli]") {
  ads1292::cli::ReportOptions opt;
  opt.csv_path = "/tmp/p9_c7_does_not_exist_report.csv";
  std::ostringstream stdout_buf;
  std::ostringstream stderr_buf;
  auto* old_cerr = std::cerr.rdbuf(stderr_buf.rdbuf());
  int code = ads1292::cli::run_report(stdout_buf, opt);
  std::cerr.rdbuf(old_cerr);
  REQUIRE(code == 1);
  REQUIRE(stdout_buf.str().find("error") == std::string::npos);
  REQUIRE(!stderr_buf.str().empty());
}

// ---------------------------------------------------------------------------
// C6 regression (subprocess): --source without a value must print
// "--source requires an argument" and exit 1, not "Unknown option: --source".
// Oracle: argparse type=float rejects bad args cleanly; known flags get clear
// messages.
// ---------------------------------------------------------------------------
#ifdef CLI_BINARY
TEST_CASE("cli qc --source missing value exits 1 with clear message (C6)", "[cli][subprocess]") {
  auto [code, out] = run_cmd(std::string(CLI_BINARY) + " qc /tmp/no_such.csv --source");
  REQUIRE(code == 1);
  REQUIRE(out.find("--source requires an argument") != std::string::npos);
  REQUIRE(out.find("Unknown option") == std::string::npos);
}

TEST_CASE("cli index --out missing value exits 1 with clear message (C6)", "[cli][subprocess]") {
  auto [code, out] = run_cmd(std::string(CLI_BINARY) + " index /tmp --out");
  REQUIRE(code == 1);
  REQUIRE(out.find("--out requires an argument") != std::string::npos);
  REQUIRE(out.find("Unknown option") == std::string::npos);
}

// ---------------------------------------------------------------------------
// B8 regression (subprocess): filesystem exception from run_index must
// produce a clean "error: ..." message on stderr and exit 1, not abort.
// Oracle: cli.py main wraps dispatch in except OSError → SystemExit("error: ...")
// We force a filesystem_error by pointing --out at an existing regular file.
// ---------------------------------------------------------------------------
TEST_CASE("cli index with unwritable --out exits 1 with error message (B8)", "[cli][subprocess]") {
  // Create a regular file at the --out path so create_directories throws.
  auto blocker = std::filesystem::temp_directory_path() / "p9_b8_blocker_file";
  { std::ofstream f(blocker.string()); f << "blocker\n"; }
  auto [code, out] = run_cmd(std::string(CLI_BINARY) + " index /tmp --out " + blocker.string());
  std::filesystem::remove(blocker);
  REQUIRE(code == 1);
  REQUIRE(out.find("error:") != std::string::npos);
}
#endif  // CLI_BINARY
