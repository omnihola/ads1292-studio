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

  /// Returns true when this source has no more samples to produce.
  /// Real hardware always returns false (the stream runs until the caller stops
  /// it via stop_stream() / should_continue).  Finite simulators override to
  /// return true once their pre-set batch count is exhausted, so callers that
  /// use run_to_completion can provide a suitable should_continue predicate.
  virtual bool stream_done() const { return false; }
};

}}  // namespace ads1292::acq
