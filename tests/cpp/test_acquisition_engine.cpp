// tests/cpp/test_acquisition_engine.cpp
#include "catch.hpp"
#include "ads1292/io/AcquisitionEngine.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include "ads1292/acq/SampleQueue.h"
#include <cstdio>

using namespace ads1292;

TEST_CASE("run_live drains the simulator into the queue + CSV journal", "[engine]") {
  acq::SimulatorDeviceSource sim(/*stream_batches=*/5, /*raw_count=*/0);
  acq::SampleQueue<StreamSample> q;
  const std::string csv = std::string(FIXTURE_DIR) + "/files/_acq_live.csv";
  auto res = io::run_live(sim, q, csv, [] { return true; });

  REQUIRE(res.sample_count == 70);          // 5 * 14
  REQUIRE(q.size() == 70);
  // the CSV journal round-trips to 70 samples via the P2a reader
  auto reread = io::read_recording_csv(csv);
  REQUIRE(reread.size() == 70);
  // sample indices are sequential 0..69 in the queue
  StreamSample s; int i = 0;
  while (q.try_pop(s)) { REQUIRE(s.sample_index.value_or(-1) == i); ++i; }
  std::remove(csv.c_str());
}
