#include "ads1292/acq/SimulatorDeviceSource.h"
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/RawSample.h"

namespace ads1292 { namespace acq {

SimulatorDeviceSource::SimulatorDeviceSource(int stream_batches, int raw_count)
    : stream_batches_(stream_batches), raw_count_(raw_count) {}

void SimulatorDeviceSource::start_stream() {
  streaming_ = true;
}

void SimulatorDeviceSource::stop_stream() {
  streaming_ = false;
}

std::vector<ads1292::StreamSample> SimulatorDeviceSource::read_stream_batch() {
  if (emitted_batches_ >= stream_batches_) {
    return {};
  }
  const int k = emitted_batches_;
  ++emitted_batches_;

  std::vector<ads1292::StreamSample> batch;
  batch.reserve(14);
  for (int i = 0; i < 14; ++i) {
    ads1292::StreamSample s;
    s.timestamp = (14 * k + i) / 500.0;
    s.ch1 = 100 + 14 * k + i;
    s.ch2 = -(14 * k + i);
    s.board_heart_rate = 72;
    s.board_respiration_rate = 18;
    s.status_byte = (14 * k + i) % 16;
    // sample_index intentionally left unset — the engine assigns it
    batch.push_back(s);
  }
  return batch;
}

bool SimulatorDeviceSource::stream_done() const {
  return emitted_batches_ >= stream_batches_;
}

std::vector<ads1292::RawSample> SimulatorDeviceSource::acquire_raw(int count) {
  std::vector<ads1292::RawSample> result;
  result.reserve(static_cast<std::size_t>(count));
  for (int i = 0; i < count; ++i) {
    ads1292::RawSample s;
    s.sample_index = i;
    s.timestamp = i / 500.0;
    s.ch1_raw24 = 1000 + i;
    s.ch2_raw24 = -2000 - i;
    s.status_byte = i % 16;
    result.push_back(s);
  }
  return result;
}

}}  // namespace ads1292::acq
