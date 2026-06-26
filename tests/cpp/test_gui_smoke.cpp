// tests/cpp/test_gui_smoke.cpp
// Offscreen smoke test for the QCustomPlotWaveform backend.
// Run with: QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure

#include "catch.hpp"
#include "ads1292/gui/QCustomPlotWaveform.h"
#include <QApplication>
#include <fstream>
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

#include "ads1292/gui/QCustomPlotXY.h"

TEST_CASE("QCustomPlotXY line + bars render offscreen", "[gui]") {
  ensureApp();
  ads1292::gui::QCustomPlotXY plot;
  plot.setLine({0,1,2,3}, {0,1,4,9});
  plot.setBars({0.5,1.5,2.5}, {2,5,3}, 1.0);
  plot.setTitle("test"); plot.setAutoscale(true); plot.replotNow();
  REQUIRE(plot.widget() != nullptr);
}

#include "ads1292/gui/PqrstPanel.h"
#include "ads1292/gui/SpectrumPanel.h"
#include "ads1292/gui/QualityInfoPanel.h"
#include "ads1292/gui/ReviewEventLogPanel.h"
#include "ads1292/view/ReviewRender.h"
#include "ads1292/dsp/Spectrum.h"

TEST_CASE("review panels render a frame offscreen", "[gui]") {
  ensureApp();
  std::vector<ads1292::StreamSample> samples;
  for (int i=0;i<3000;++i){ ads1292::StreamSample s; s.ch2=(i%417<5)?300:0; s.ch1=0; s.status_byte=0; samples.push_back(s); }
  auto f = ads1292::view::build_review_render_frame(samples, {}, {}, "Auto", 500.0, 5, 5000, false, 50.0, 50.0);
  auto spec = ads1292::dsp::build_spectrum_analysis(samples, "CH2", 500.0, 60.0, 48);
  ads1292::gui::PqrstPanel pq; pq.showFrame(f);
  ads1292::gui::SpectrumPanel sp; sp.showSpectrum(spec);
  ads1292::gui::QualityInfoPanel qi; qi.showMetrics(f.metrics);
  ads1292::gui::ReviewEventLogPanel ev; ev.appendLine("loaded");
  REQUIRE(pq.isWidgetType()); REQUIRE(sp.isWidgetType()); REQUIRE(qi.isWidgetType()); REQUIRE(ev.isWidgetType());
}

#include "ads1292/io/CsvIo.h"
#include <filesystem>
#include <memory>

TEST_CASE("MainWindow loads a recording into the review panels", "[gui]") {
  ensureApp();
  // Author a small recording via the io writer
  std::string path = (std::filesystem::temp_directory_path() / "p6_review.csv").string();
  std::vector<ads1292::StreamSample> rec;
  for (int i=0;i<1500;++i){ ads1292::StreamSample s; double t=i/500.0, v=0.0;
    for(double bt=0.2; bt<3.0; bt+=60.0/72.0){ double d=t-bt; v+=200.0*std::exp(-(d*d)/(2*0.01*0.01)); }
    s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s); }
  ads1292::io::write_recording_csv(path, rec);
  ads1292::gui::MainWindow win;
  REQUIRE(win.runSimulatorToCompletion(4) == 56);   // P4/P5d regression intact
  win.loadRecordingForTest(path);
  REQUIRE(win.reviewLoadedForTest());
}

TEST_CASE("QCustomPlotWaveform + QCustomPlotXY savePng write files offscreen", "[gui]") {
  ensureApp();
  auto wf = std::make_unique<ads1292::gui::QCustomPlotWaveform>();
  wf->setData(0, {0,1,2,3}, {0,1,4,9}); wf->setAutoscale(true);
  auto wpath = (std::filesystem::temp_directory_path()/"p7c_wave.png").string();
  REQUIRE(wf->savePng(wpath, 800, 300));
  REQUIRE(std::filesystem::file_size(wpath) > 200);
  ads1292::gui::QCustomPlotXY xy;
  xy.setLine({0,1,2,3},{1,2,1,2}); xy.setAutoscale(true);
  auto xpath = (std::filesystem::temp_directory_path()/"p7c_xy.png").string();
  REQUIRE(xy.savePng(xpath, 800, 300));
  REQUIRE(std::filesystem::file_size(xpath) > 200);
}

#include "ads1292/gui/ReportExport.h"
#include <cmath>

TEST_CASE("export_review_report writes HTML + 3 PNGs offscreen", "[gui]") {
  ensureApp();
  std::vector<ads1292::StreamSample> rec;
  for (int i=0;i<3000;++i){ ads1292::StreamSample s; double t=i/500.0,v=0.0; for(double bt=0.2;bt<6.0;bt+=60.0/72.0){double d=t-bt; v+=200.0*std::exp(-(d*d)/(2*0.01*0.01));} s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s);}
  auto out = (std::filesystem::temp_directory_path()/"p7c_report").string();
  auto r = ads1292::gui::export_review_report(rec, out, "Smoke");
  REQUIRE(std::filesystem::exists(r.html_path));
  REQUIRE(std::filesystem::exists(r.ecg_png_path));
  REQUIRE(std::filesystem::exists(r.pqrst_png_path));
  REQUIRE(std::filesystem::exists(r.spectrum_png_path));
  REQUIRE(std::filesystem::file_size(r.ecg_png_path) > 200);
}

TEST_CASE("export_review_report throws when out_dir cannot be created (B5 regression)", "[gui]") {
  // B5: before the fix, failures were silently swallowed; after the fix each failure throws.
  // Strategy: block directory creation by placing a regular file where the dir would be.
  ensureApp();

  // Create a regular file to occupy the slot where we want a directory
  auto block_path = std::filesystem::temp_directory_path() / "b5_block_file";
  { std::ofstream f(block_path.string()); f << "x"; }

  // Trying to use block_path/subdir as out_dir causes create_directories to throw
  // (or the savePng to fail) — either way export_review_report must propagate
  std::string bad_dir = (block_path / "subdir").string();

  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 10; ++i) {
      ads1292::StreamSample s; s.ch1 = i; s.ch2 = 0; s.timestamp = i / 500.0;
      samples.push_back(s);
  }

  REQUIRE_THROWS(ads1292::gui::export_review_report(samples, bad_dir, "b5test"));

  std::filesystem::remove(block_path);
}

TEST_CASE("export_review_report throws when PNG path is a directory (B5 savePng check)", "[gui]") {
  // Force savePng failure: create the out_dir, then create a DIRECTORY where
  // the first PNG would go (slug "b5slug" → "b5slug-ecg.png").
  // After B5 fix, the bool check throws instead of silently returning.
  ensureApp();

  auto out_dir = std::filesystem::temp_directory_path() / "b5_png_dir_test";
  std::filesystem::create_directories(out_dir);

  // Pre-create the ECG png slot as a directory so savePng cannot write a file there
  auto ecg_blocker = out_dir / "b5slug-ecg.png";
  std::filesystem::create_directories(ecg_blocker);

  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 100; ++i) {
      ads1292::StreamSample s; s.ch2 = (i % 50 < 5) ? 300 : 0; s.ch1 = 0; s.timestamp = i / 500.0;
      samples.push_back(s);
  }

  REQUIRE_THROWS(ads1292::gui::export_review_report(samples, out_dir.string(), "B5Slug"));

  std::filesystem::remove_all(out_dir);
}
