#pragma once
#include <functional>
#include <string>
#include "ads1292/acq/IDeviceSource.h"
#include "ads1292/acq/SampleQueue.h"
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/RawSample.h"

namespace ads1292 { namespace io {

struct AcquisitionResult {
  int sample_count;
  std::string csv_path;
};

/// Drives a live streaming session, pushing each StreamSample to queue
/// and (if csv_path non-empty) writing a CSV journal at stop.
/// Loops until should_continue() returns false or the device returns an
/// empty batch.  Assigns sequential sample_index values starting from 0.
AcquisitionResult run_live(acq::IDeviceSource& dev,
                           acq::SampleQueue<StreamSample>& queue,
                           const std::string& csv_path,
                           std::function<bool()> should_continue);

/// Drives a raw acquisition session, pushing each RawSample to queue
/// and (if csv_path non-empty) writing a raw CSV journal at stop.
/// Acquires samples in chunks until total_samples are collected;
/// reindexes sample_index sequentially starting from 0.
AcquisitionResult run_raw(acq::IDeviceSource& dev,
                          acq::SampleQueue<RawSample>& queue,
                          const std::string& csv_path,
                          int total_samples,
                          int chunk);

}}  // namespace ads1292::io
