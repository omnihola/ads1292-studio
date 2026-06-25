#pragma once
#include <vector>
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/RawSample.h"

namespace ads1292 { namespace acq {

enum class AcquisitionMode { Live, Raw };

class IDeviceSource {
 public:
  virtual ~IDeviceSource() = default;
  virtual void start_stream() = 0;
  virtual void stop_stream() = 0;
  virtual std::vector<ads1292::StreamSample> read_stream_batch() = 0;
  virtual std::vector<ads1292::RawSample> acquire_raw(int count) = 0;
};

}}  // namespace ads1292::acq
