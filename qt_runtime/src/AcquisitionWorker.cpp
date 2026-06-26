// qt_runtime/src/AcquisitionWorker.cpp
#include "ads1292/qt/AcquisitionWorker.h"
#include "ads1292/io/AcquisitionEngine.h"

namespace ads1292 { namespace qt {

AcquisitionWorker::AcquisitionWorker(QObject* parent)
    : QObject(parent) {}

AcquisitionWorker::~AcquisitionWorker() {
  // If an async thread is running, signal it to stop and join.
  stop_.store(true);
  if (worker_thread_.joinable()) {
    worker_thread_.join();
  }
}

// ---------------------------------------------------------------------------
// Synchronous helper — for headless / smoke-test use
// ---------------------------------------------------------------------------

int AcquisitionWorker::run_to_completion(ads1292::acq::IDeviceSource* dev,
                                         ads1292::acq::AcquisitionMode mode,
                                         const std::string& csv_path) {
  stop_.store(false);

  int sample_count = 0;

  std::thread t([&] {
    if (mode == ads1292::acq::AcquisitionMode::Live) {
      // Also stop when dev->stream_done() is true: finite simulators signal
      // exhaustion this way so run_live's continue-on-empty loop can terminate.
      // Real hardware always returns stream_done()==false (default IDeviceSource).
      auto result = ads1292::io::run_live(
          *dev, live_queue_, csv_path,
          [this, dev] { return !stop_.load() && !dev->stream_done(); });
      sample_count = result.sample_count;
    } else {
      auto result = ads1292::io::run_raw(
          *dev, raw_queue_, csv_path,
          kDefaultRawTotal, kDefaultRawChunk);
      sample_count = result.sample_count;
    }
  });
  t.join();

  return sample_count;
}

// ---------------------------------------------------------------------------
// Async API — for GUI use
// ---------------------------------------------------------------------------

void AcquisitionWorker::start(ads1292::acq::IDeviceSource* dev,
                               ads1292::acq::AcquisitionMode mode,
                               const std::string& csv_path) {
  // Join any previous thread before starting a new one.
  if (worker_thread_.joinable()) {
    worker_thread_.join();
  }
  stop_.store(false);

  worker_thread_ = std::thread([this, dev, mode, csv_path] {
    run_engine(dev, mode, csv_path);
  });
}

void AcquisitionWorker::requestStop() {
  stop_.store(true);
}

// ---------------------------------------------------------------------------
// Private helper shared by async path
// ---------------------------------------------------------------------------

void AcquisitionWorker::run_engine(ads1292::acq::IDeviceSource* dev,
                                    ads1292::acq::AcquisitionMode mode,
                                    const std::string& csv_path) {
  int sample_count = 0;
  if (mode == ads1292::acq::AcquisitionMode::Live) {
    auto result = ads1292::io::run_live(
        *dev, live_queue_, csv_path,
        [this] { return !stop_.load(); });
    sample_count = result.sample_count;
  } else {
    auto result = ads1292::io::run_raw(
        *dev, raw_queue_, csv_path,
        kDefaultRawTotal, kDefaultRawChunk);
    sample_count = result.sample_count;
  }
  emit finished(sample_count);
}

}}  // namespace ads1292::qt
