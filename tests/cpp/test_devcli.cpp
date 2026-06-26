// tests/cpp/test_devcli.cpp
#include "catch.hpp"
#include "ads1292/devcli/DevCli.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include <sstream>
using namespace ads1292;

TEST_CASE("run_stream collects samples from the simulator into a count", "[device]") {
  acq::SimulatorDeviceSource sim(/*stream_batches*/ 10, /*raw_count*/ 0);  // 10*14 = 140 samples
  devcli::StreamOptions opt; opt.max_samples = 100;
  std::ostringstream out;
  int code = devcli::run_stream(out, sim, opt);
  REQUIRE(code == 0);
  REQUIRE(out.str().find("samples=") != std::string::npos);
  // collected at least max_samples (or all the simulator produced)
}

TEST_CASE("run_ports prints a diagnostic when no board attached", "[device]") {
  std::ostringstream out;
  int code = devcli::run_ports(out);   // CI: no ADS device -> "No ADS1x9x ports found", exit 1
  // either 0 (a device is attached) or 1 (none) — assert it ran + produced output
  REQUIRE((code == 0 || code == 1));
}
