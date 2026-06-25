#pragma once
#include <vector>
#include "ads1292/acq/IDeviceSource.h"
#include "ads1292/acq/IByteTransport.h"

namespace ads1292 { namespace acq {

class AdsProtocolDevice : public IDeviceSource {
 public:
  explicit AdsProtocolDevice(IByteTransport& transport, double sample_rate_hz);

  void start_stream() override;
  void stop_stream() override;
  std::vector<ads1292::StreamSample> read_stream_batch() override;
  std::vector<ads1292::RawSample> acquire_raw(int count) override;

 private:
  IByteTransport& t_;
  double sample_rate_hz_;
  bool streaming_ = false;
  int stream_index_ = 0;
  double t0_ = 0.0;
};

}}  // namespace ads1292::acq
