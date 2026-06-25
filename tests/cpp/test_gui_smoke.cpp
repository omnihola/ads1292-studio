// tests/cpp/test_gui_smoke.cpp
// Offscreen smoke test for the QCustomPlotWaveform backend.
// Run with: QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure

#include "catch.hpp"
#include "ads1292/gui/QCustomPlotWaveform.h"
#include <QApplication>
#include <vector>

// Guard: ensures a single QApplication exists for the process lifetime.
// New test cases must call ensureApp() instead of constructing their own QApplication.
static QApplication* ensureApp() {
    static int   argc   = 0;
    static char* argv[] = {nullptr};
    if (!qApp) {
        static QApplication app(argc, argv);
    }
    return qApp;
}

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

#include "ads1292/gui/StatusPanel.h"
#include "ads1292/gui/EventConsole.h"

TEST_CASE("StatusPanel updates from state without crashing", "[gui]") {
  ensureApp();
  ads1292::gui::StatusPanel panel;
  ads1292::gui::GuiState st;
  st.connection     = "Connected";
  st.recordingState = "streaming";
  st.eventCount     = 3;
  panel.updateFromState(st);
  REQUIRE(true);
}

TEST_CASE("EventConsole adds a point event at the live clock", "[gui]") {
  ensureApp();
  ads1292::gui::EventConsole console;
  console.setSampleClock(2.5);
  console.addPointEventForTest("touch", "n");
  REQUIRE(console.log().events().size() == 1);
  REQUIRE(console.log().events()[0].timestamp_seconds == Approx(2.5));
}

#include "ads1292/gui/MainWindow.h"

TEST_CASE("MainWindow drives the simulator into the scope headlessly", "[gui]") {
  ensureApp();
  ads1292::gui::MainWindow win;
  int shown = win.runSimulatorToCompletion(/*streamBatches=*/4);
  REQUIRE(shown == 56);    // 4 * 14 samples drained into the scope
}

TEST_CASE("LiveScope renders a filtered frame with R-peak markers", "[gui]") {
  ensureApp();
  ads1292::gui::LiveScope scope;
  for (int i=0;i<3000;++i){ ads1292::StreamSample s; s.ch2=(i%417<5)?300:0; s.ch1=0; s.status_byte=0; scope.pushStreamSample(s); }
  ads1292::dsp::SoftwareFilterSettings fs; fs.bandpass_enabled=true;
  scope.setFilterSettings(fs);
  scope.refresh();
  REQUIRE(scope.lastFrame().valid);
}

TEST_CASE("MainWindow filter toggles + SNR strip update without crash", "[gui]") {
  ensureApp();
  ads1292::gui::MainWindow win;
  int shown = win.runSimulatorToCompletion(8);   // P4 helper
  REQUIRE(shown == 112);                          // 8*14 regression (P4 path intact)
  win.setDisplayFilterForTest(/*qrs=*/true);
  REQUIRE(win.liveSnrDbForTest() == win.liveSnrDbForTest());  // not NaN (self-equal)
}
