// tests/cpp/test_devcli.cpp
#include "catch.hpp"
#include "ads1292/devcli/DevCli.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include "ads1292/acq/IDeviceSource.h"
#include <sstream>
#include <stdexcept>
#include <string>
#include <cstdio>
#include <sys/wait.h>
using namespace ads1292;

// ---------------------------------------------------------------------------
// Subprocess helper shared with test_cli.cpp.
// ---------------------------------------------------------------------------
namespace {
std::pair<int, std::string> run_devcli_cmd(const std::string& cmd) {
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

TEST_CASE("run_stream collects samples from the simulator into a count", "[device]") {
  acq::SimulatorDeviceSource sim(/*stream_batches*/ 10, /*raw_count*/ 0);  // 10*14 = 140 samples
  devcli::StreamOptions opt; opt.max_samples = 100;
  std::ostringstream out;
  int code = devcli::run_stream(out, sim, opt);
  REQUIRE(code == 0);
  auto s = out.str();
  auto pos = s.find("samples=");
  REQUIRE(pos != std::string::npos);
  int count = std::stoi(s.substr(pos + 8));   // 8 = strlen("samples=")
  REQUIRE(count >= 100);     // collected at least the max_samples budget
  REQUIRE(count <= 140);     // but no more than the simulator produced (10*14)
}

// B9 regression test: run_stream must call stop_stream() even when read throws.
// Oracle: cli.py cmd_stream uses try/finally: device.stop_stream().
TEST_CASE("run_stream calls stop_stream on exception (B9)", "[device]") {
  struct ThrowingDeviceSource : ads1292::acq::IDeviceSource {
    bool stopped = false;
    int read_count = 0;

    void start_stream() override {}
    void stop_stream() override { stopped = true; }

    std::vector<ads1292::StreamSample> read_stream_batch() override {
      ++read_count;
      if (read_count >= 2) {
        throw std::runtime_error("simulated read failure");
      }
      // First call: return one sample so the loop runs at least once
      ads1292::StreamSample s;
      s.timestamp = 0.0; s.ch1 = 1; s.ch2 = 2;
      s.board_heart_rate = 0; s.board_respiration_rate = 0; s.status_byte = 0;
      return {s};
    }
    std::vector<ads1292::RawSample> acquire_raw(int) override { return {}; }
  };

  ThrowingDeviceSource src;
  devcli::StreamOptions opt;
  opt.max_samples = 100;
  std::ostringstream out;

  // With OLD code: no try/catch → stop_stream never called → src.stopped stays false.
  // With NEW code: catch block calls stop_stream before rethrowing.
  REQUIRE_THROWS(devcli::run_stream(out, src, opt));
  REQUIRE(src.stopped);
}

TEST_CASE("run_ports prints a diagnostic when no board attached", "[device]") {
  std::ostringstream out;
  int code = devcli::run_ports(out);   // CI: no ADS device -> "No ADS1x9x ports found", exit 1
  // either 0 (a device is attached) or 1 (none) — assert it ran + produced output
  REQUIRE((code == 0 || code == 1));
  REQUIRE(!out.str().empty());
}

// ---------------------------------------------------------------------------
// B7 regression (subprocess): --seconds with a non-numeric value must print
// "invalid --seconds value: <val>" to stderr and exit 1.
// Oracle: argparse type=float rejects bad --seconds cleanly; Python raises
// SystemExit with a type-error message.
// With OLD code: std::stod outside try/catch → std::terminate (abort).
// With NEW code: try/catch → clean exit 1.
// ---------------------------------------------------------------------------
#ifdef DEVCLI_BINARY
TEST_CASE("devcli stream --seconds with invalid value exits 1 (B7)", "[device][subprocess]") {
  // QT_QPA_PLATFORM=offscreen to suppress any Qt platform warnings.
  std::string cmd = "QT_QPA_PLATFORM=offscreen "
                    + std::string(DEVCLI_BINARY)
                    + " stream --seconds abc";
  auto [code, out] = run_devcli_cmd(cmd);
  REQUIRE(code == 1);
  REQUIRE(out.find("invalid --seconds value") != std::string::npos);
}
#endif  // DEVCLI_BINARY
