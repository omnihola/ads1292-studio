// tests/cpp/test_acq_worker_smoke.cpp
#include "catch.hpp"
#include "ads1292/qt/AcquisitionWorker.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include <QCoreApplication>

TEST_CASE("AcquisitionWorker runs the simulator to completion headlessly", "[worker]") {
  int argc = 0; char** argv = nullptr;
  QCoreApplication app(argc, argv);
  ads1292::acq::SimulatorDeviceSource sim(/*stream_batches=*/4, /*raw_count=*/0);
  ads1292::qt::AcquisitionWorker worker;
  int produced = worker.run_to_completion(&sim, ads1292::acq::AcquisitionMode::Live, "");
  REQUIRE(produced == 56);  // 4 * 14
}
