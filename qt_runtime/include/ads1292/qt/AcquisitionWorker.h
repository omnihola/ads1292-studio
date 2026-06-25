#pragma once
#include <QObject>
#include <atomic>
#include <string>
#include <thread>
#include "ads1292/acq/IDeviceSource.h"
#include "ads1292/acq/SampleQueue.h"
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/RawSample.h"

namespace ads1292 { namespace qt {

/// Runs the portable AcquisitionEngine on a worker thread.
///
/// Synchronous path (headless / test use):
///   run_to_completion() spawns a std::thread, blocks until it joins,
///   and returns the engine's sample_count.  No Qt event loop needed.
///
/// Async path (GUI use):
///   start() posts the work onto an internal thread; stop() signals the
///   stop flag and joins.  Emits finished(int sampleCount) when done.
class AcquisitionWorker : public QObject {
  Q_OBJECT

 public:
  explicit AcquisitionWorker(QObject* parent = nullptr);
  ~AcquisitionWorker() override;

  // --- synchronous helper for smoke test / headless use ---

  /// Run the engine to completion on a worker std::thread, join, return
  /// the sample count.  Resets stop_ before starting.
  int run_to_completion(ads1292::acq::IDeviceSource* dev,
                        ads1292::acq::AcquisitionMode mode,
                        const std::string& csv_path);

  // --- async API for GUI use ---

  void start(ads1292::acq::IDeviceSource* dev,
             ads1292::acq::AcquisitionMode mode,
             const std::string& csv_path);
  void requestStop();

  // --- queue accessors the GUI drains ---

  ads1292::acq::SampleQueue<ads1292::StreamSample>& live_queue() {
    return live_queue_;
  }
  ads1292::acq::SampleQueue<ads1292::RawSample>& raw_queue() {
    return raw_queue_;
  }

 signals:
  void finished(int sample_count);

 private:
  void run_engine(ads1292::acq::IDeviceSource* dev,
                  ads1292::acq::AcquisitionMode mode,
                  const std::string& csv_path);

  ads1292::acq::SampleQueue<ads1292::StreamSample> live_queue_;
  ads1292::acq::SampleQueue<ads1292::RawSample>    raw_queue_;
  std::atomic<bool> stop_{false};
  std::thread worker_thread_;

  static constexpr int kDefaultRawTotal = 256;
  static constexpr int kDefaultRawChunk = 8;
};

}}  // namespace ads1292::qt
