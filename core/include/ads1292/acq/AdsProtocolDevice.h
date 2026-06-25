#pragma once
#include <string>
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

  /// Write CMD 0x99, read frames until a 0x99 response, return "{major}.{minor}".
  /// Uses a frame-count budget (deterministic; no wall clock).
  std::string query_firmware(int max_frames = 64);

 private:
  IByteTransport& t_;
  double sample_rate_hz_;
  bool streaming_ = false;
  int stream_index_ = 0;
  double t0_ = 0.0;
};

}}  // namespace ads1292::acq
