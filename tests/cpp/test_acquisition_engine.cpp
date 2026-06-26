// tests/cpp/test_acquisition_engine.cpp
#include "catch.hpp"
#include "ads1292/io/AcquisitionEngine.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include "ads1292/acq/SampleQueue.h"
#include "ads1292/acq/IDeviceSource.h"
#include <cstdio>
#include <cstdlib>
#include <filesystem>

using namespace ads1292;

TEST_CASE("run_live drains the simulator into the queue + CSV journal", "[engine]") {
  acq::SimulatorDeviceSource sim(/*stream_batches=*/5, /*raw_count=*/0);
  acq::SampleQueue<StreamSample> q;
  const std::string csv = std::string(FIXTURE_DIR) + "/files/_acq_live.csv";
  // should_continue must eventually return false: the engine now does `continue`
  // on empty (not break), so a lambda that always returns true would loop forever
  // once the simulator is exhausted.  Allow enough iterations to drain all 5
  // batches plus a couple of empty reads before stopping.
  int iter = 0;
  auto res = io::run_live(sim, q, csv, [&iter] { return ++iter <= 8; });

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

// B1 regression test: run_live must NOT stop on an empty batch (continue, not break).
// Oracle: device.py iter_stream_samples does `continue` on empty batch.
TEST_CASE("run_live continues past an empty batch (B1)", "[engine]") {
  // FakeDeviceSource: call 1 → 14 samples, call 2 → empty, call 3 → 14 samples, rest → empty
  struct FakeDeviceSource : ads1292::acq::IDeviceSource {
    int call_count = 0;
    void start_stream() override {}
    void stop_stream() override {}
    std::vector<ads1292::StreamSample> read_stream_batch() override {
      ++call_count;
      if (call_count == 1 || call_count == 3) {
        std::vector<ads1292::StreamSample> batch;
        batch.reserve(14);
        for (int i = 0; i < 14; ++i) {
          ads1292::StreamSample s;
          s.timestamp = (call_count == 1 ? i : 14 + i) / 500.0;
          s.ch1 = 100 + i; s.ch2 = -(100 + i);
          s.board_heart_rate = 72; s.board_respiration_rate = 18; s.status_byte = 0;
          batch.push_back(s);
        }
        return batch;
      }
      return {};  // empty on call 2, and calls 4+
    }
    std::vector<ads1292::RawSample> acquire_raw(int) override { return {}; }
  };

  FakeDeviceSource fake;
  ads1292::acq::SampleQueue<ads1292::StreamSample> q;

  // should_continue: returns true for calls 1–5, then false on call 6
  int continue_count = 0;
  auto should_continue = [&]() -> bool { return ++continue_count <= 5; };

  const std::string csv = (std::filesystem::temp_directory_path() / "_acq_live_b1.csv").string();
  auto res = ads1292::io::run_live(fake, q, csv, should_continue);

  // With the bug (break on empty), only 14 samples from call 1 are collected.
  // With the fix (continue on empty), 28 samples (calls 1 + 3) are collected.
  REQUIRE(res.sample_count >= 28);
  std::remove(csv.c_str());
}

TEST_CASE("run_raw caps the queue + CSV at total_samples when chunk overshoots", "[engine]") {
  acq::SimulatorDeviceSource sim(/*stream_batches=*/0, /*raw_count=*/0);
  acq::SampleQueue<RawSample> q;
  const std::string csv = std::string(FIXTURE_DIR) + "/files/_acq_raw.csv";
  auto res = io::run_raw(sim, q, csv, /*total_samples=*/20, /*chunk=*/8);
  REQUIRE(res.sample_count == 20);
  REQUIRE(q.size() == 20);                                   // NOT 24
  auto reread = io::read_raw_recording_csv(csv);
  REQUIRE(reread.size() == 20);
  RawSample s; int i = 0;
  while (q.try_pop(s)) { REQUIRE(s.sample_index == i); ++i; }
  std::remove(csv.c_str());
}
