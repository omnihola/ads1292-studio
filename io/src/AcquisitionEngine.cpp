// io/src/AcquisitionEngine.cpp
#include "ads1292/io/AcquisitionEngine.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/model/Calibration.h"
#include <vector>

namespace ads1292 { namespace io {

AcquisitionResult run_live(acq::IDeviceSource& dev,
                           acq::SampleQueue<StreamSample>& queue,
                           const std::string& csv_path,
                           std::function<bool()> should_continue) {
  std::vector<StreamSample> all;
  int running_counter = 0;

  dev.start_stream();

  while (true) {
    if (!should_continue()) break;

    auto batch = dev.read_stream_batch();
    if (batch.empty()) break;

    for (auto& s : batch) {
      s.sample_index = running_counter++;
      queue.push(s);
      all.push_back(s);
    }
  }

  dev.stop_stream();

  // Write-once-at-stop: acceptable for P3's finite simulator.
  // (The Python worker writes incrementally for crash-safety; the
  // portable C++ engine buffers samples and flushes once, which keeps
  // the engine unit-testable without a file-watcher or incremental CSV
  // writer.)
  if (!csv_path.empty()) {
    write_recording_csv(csv_path, all);
  }

  return {static_cast<int>(all.size()), csv_path};
}

AcquisitionResult run_raw(acq::IDeviceSource& dev,
                          acq::SampleQueue<RawSample>& queue,
                          const std::string& csv_path,
                          int total_samples,
                          int chunk) {
  std::vector<RawSample> all;
  int running_counter = 0;

  while (static_cast<int>(all.size()) < total_samples) {
    auto batch = dev.acquire_raw(chunk);

    for (auto& s : batch) {
      s.sample_index = running_counter++;
      queue.push(s);
      all.push_back(s);

      if (static_cast<int>(all.size()) >= total_samples) break;
    }
  }

  // Truncate to exactly total_samples in case the last chunk overshoots.
  if (static_cast<int>(all.size()) > total_samples) {
    all.resize(static_cast<std::size_t>(total_samples));
  }

  if (!csv_path.empty()) {
    write_raw_recording_csv(csv_path, all, Calibration{});
  }

  return {total_samples, csv_path};
}

}}  // namespace ads1292::io
