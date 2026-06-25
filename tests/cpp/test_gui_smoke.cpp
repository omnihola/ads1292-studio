// tests/cpp/test_gui_smoke.cpp
// Offscreen smoke test for the QCustomPlotWaveform backend.
// Run with: QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure

#include "catch.hpp"
#include "ads1292/gui/QCustomPlotWaveform.h"
#include <QApplication>
#include <vector>

TEST_CASE("QCustomPlotWaveform accepts data without crashing", "[gui]") {
    int argc = 0;
    char** argv = nullptr;
    QApplication app(argc, argv);               // offscreen via QT_QPA_PLATFORM
    ads1292::gui::QCustomPlotWaveform plot;
    std::vector<double> x = {0, 1, 2, 3};
    std::vector<double> y = {0, 10, -10, 5};
    plot.setData(0, x, y);
    plot.setAutoscale(true);
    plot.replotNow();
    REQUIRE(plot.widget() != nullptr);
}

#include "ads1292/gui/LiveScope.h"
#include "ads1292/model/StreamSample.h"

TEST_CASE("LiveScope ingests stream samples and refreshes without crashing", "[gui]") {
  int argc = 0; char** argv = nullptr;
  QApplication app(argc, argv);
  ads1292::gui::LiveScope scope;
  for (int i = 0; i < 1000; ++i) {
    ads1292::StreamSample s; s.ch1 = i % 50; s.ch2 = (i % 100) - 50; s.timestamp = i / 500.0;
    scope.pushStreamSample(s);
  }
  scope.refresh();
  scope.setWindowSeconds(8.0);
  scope.setAutoscale(true);
  scope.clear();
  REQUIRE(true);   // no crash offscreen
}
