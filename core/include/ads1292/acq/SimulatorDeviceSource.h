#pragma once
#include <vector>
#include "ads1292/acq/IDeviceSource.h"

namespace ads1292 { namespace acq {

class SimulatorDeviceSource : public IDeviceSource {
 public:
  SimulatorDeviceSource(int stream_batches, int raw_count);

  void start_stream() override;
  void stop_stream() override;
  std::vector<ads1292::StreamSample> read_stream_batch() override;
  std::vector<ads1292::RawSample> acquire_raw(int count) override;
  bool stream_done() const override;

 private:
  int stream_batches_;
  int raw_count_;
  int emitted_batches_ = 0;
  bool streaming_ = false;
};

}}  // namespace ads1292::acq
