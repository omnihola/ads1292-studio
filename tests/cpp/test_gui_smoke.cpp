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

// ── P11 Task 2: recording path helper + synchronous finalize seam ─────────────

#include "ads1292/gui/RecordingPaths.h"
#include "ads1292/io/LiveRecordingFinalize.h"
#include "ads1292/io/RecordingBundle.h"

TEST_CASE("timestamped_recording_csv_path returns path under base_dir ending in -ads1292-studio.csv", "[gui][recording]") {
  ensureApp();
  auto tmp = std::filesystem::temp_directory_path() / "p11_rp_test";
  std::filesystem::create_directories(tmp);

  auto path = ads1292::gui::timestamped_recording_csv_path("live", tmp.string());

  // Must be rooted under tmp
  REQUIRE(path.substr(0, tmp.string().size()) == tmp.string());

  // Must end with -ads1292-studio.csv
  const std::string suffix = "-ads1292-studio.csv";
  REQUIRE(path.size() > suffix.size());
  REQUIRE(path.substr(path.size() - suffix.size()) == suffix);

  // The filename portion must contain a date-like prefix (YYYY-MM-DD-)
  auto fname = std::filesystem::path(path).filename().string();
  REQUIRE(fname.size() > 10);
  // Check date separators at positions 4 and 7 (YYYY-MM-...)
  REQUIRE(fname[4] == '-');
  REQUIRE(fname[7] == '-');

  std::filesystem::remove_all(tmp);
}

TEST_CASE("MainWindow finalizeForTest writes bundle from pre-authored CSV (synchronous seam)", "[gui][recording]") {
  // Strategy: synchronous test seam to avoid event-loop + detached-thread timing.
  // We pre-write a CSV using write_recording_csv (same as the engine would write),
  // inject the path via setRecordingCsvPathForTest, and call finalizeForTest()
  // which runs finalize_live_recording synchronously and returns the result.
  // The bundle .json path is then checked for existence and validity.
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11_mw_finalize";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-120000-ads1292-studio.csv").string();

  // Author a small recording (50 samples)
  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 50; ++i) {
    ads1292::StreamSample s;
    s.ch2 = (i % 10 < 2) ? 300 : 0;
    s.ch1 = 0;
    s.timestamp = i / 500.0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);

  // Construct MainWindow and inject test state
  ads1292::gui::MainWindow win;
  win.setRecordingsDirForTest(tmp.string());
  win.setRecordingCsvPathForTest(csv_path);

  // Run finalize synchronously via the seam
  auto r = win.finalizeForTest();

  REQUIRE(r.wrote == true);
  REQUIRE(r.sample_count == static_cast<int>(samples.size()));
  REQUIRE(std::filesystem::exists(r.bundle_path));
  REQUIRE(ads1292::io::is_recording_bundle_path(r.bundle_path));

  // Verify the bundle round-trips the schema
  auto bundle = ads1292::io::read_recording_bundle(r.bundle_path);
  REQUIRE(bundle.contains("schema"));
  REQUIRE(bundle["schema"].get<std::string>() == "ads1292-recording-bundle-v1");

  std::filesystem::remove_all(tmp);
}

// ── P11 Task 1: EventConsole::clear() + events round-trip into bundle ──────────

TEST_CASE("EventConsole::clear() empties the event log and resets status", "[gui][events]") {
  ensureApp();
  ads1292::gui::EventConsole console;
  console.setSampleClock(1.0);
  console.addPointEventForTest("rest", "baseline");
  REQUIRE(console.log().events().size() == 1);

  console.clear();

  REQUIRE(console.log().events().empty());
  // Pending range state should also be reset
  REQUIRE_FALSE(console.log().pending_range_start().has_value());
}

TEST_CASE("events injected before finalizeForTest are round-tripped through the bundle", "[gui][events]") {
  // Verify that buildFinalizeOptions snapshots eventConsole_->log().events()
  // (not the old {}) so annotations are persisted into the recording bundle.
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11b_events_roundtrip";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-120000-ads1292-studio.csv").string();

  // Author a small recording
  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 50; ++i) {
    ads1292::StreamSample s;
    s.ch2 = (i % 10 < 2) ? 300 : 0;
    s.ch1 = 0;
    s.timestamp = i / 500.0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);

  // Construct MainWindow and configure
  ads1292::gui::MainWindow win;
  win.setRecordingsDirForTest(tmp.string());
  win.setRecordingCsvPathForTest(csv_path);

  // Inject two events via the EventConsole test seam
  auto* ec = win.eventConsoleForTest();
  REQUIRE(ec != nullptr);
  ec->setSampleClock(0.1);
  ec->addPointEventForTest("rest", "baseline");
  ec->setSampleClock(0.2);
  ec->addPointEventForTest("exercise", "peak effort");

  REQUIRE(ec->log().events().size() == 2);

  // Run finalize synchronously; events should be captured into opt.events
  auto r = win.finalizeForTest();
  REQUIRE(r.wrote == true);
  REQUIRE(std::filesystem::exists(r.bundle_path));

  // Read back the bundle and verify both events are present
  auto bundle = ads1292::io::read_recording_bundle(r.bundle_path);
  auto events = ads1292::io::events_from_bundle(bundle);

  REQUIRE(events.size() == 2);
  // Check at least one event has the expected label
  bool found_rest = false;
  for (const auto& ev : events) {
    if (ev.label == "rest") { found_rest = true; }
  }
  REQUIRE(found_rest);

  std::filesystem::remove_all(tmp);
}

// ── P11 Task 2: loadRecordingForTest populates review event panel ──────────────

#include "ads1292/io/Bundle.h"
#include "ads1292/io/ProtocolIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/RecordingProcessingSettings.h"
#include "ads1292/model/SessionMetadata.h"

TEST_CASE("P11 Task 2: loadRecordingForTest reads events from bundle into review panel", "[gui][events]") {
  // Build a recording directory with a CSV + a bundle that has 2 known events.
  // After loadRecordingForTest, reviewEventCountForTest() must return 2.
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11_task2_load_events";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-120000-ads1292-studio.csv").string();

  // Author a small recording (enough samples for the review render)
  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 1500; ++i) {
    ads1292::StreamSample s;
    double t = i / 500.0;
    double v = 0.0;
    for (double bt = 0.2; bt < 3.0; bt += 60.0 / 72.0) {
      double d = t - bt;
      v += 200.0 * std::exp(-(d * d) / (2 * 0.01 * 0.01));
    }
    s.ch2 = static_cast<int>(v); s.ch1 = 0; s.status_byte = 0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);

  // Build 2 known EventMarkers
  std::vector<ads1292::EventMarker> events;
  {
    ads1292::EventMarker e1;
    e1.timestamp_seconds = 0.1;
    e1.label = "rest";
    e1.notes = "baseline";
    events.push_back(e1);

    ads1292::EventMarker e2;
    e2.timestamp_seconds = 0.5;
    e2.label = "motion";
    e2.notes = "arm movement";
    events.push_back(e2);
  }

  // Write the bundle sidecar alongside the CSV
  ads1292::io::write_recording_bundle(
    csv_path,
    ads1292::SessionMetadata{},
    events,
    ads1292::Calibration{},
    ads1292::io::AcquisitionProvenance{},
    ads1292::io::protocol_template(),
    ads1292::io::quality_gate_template(),
    ads1292::RecordingProcessingSettings{},
    500.0,
    "");

  // Load the recording via MainWindow; events should be set on the review panel
  ads1292::gui::MainWindow win;
  win.loadRecordingForTest(csv_path);

  REQUIRE(win.reviewLoadedForTest());
  REQUIRE(win.reviewEventCountForTest() == 2);

  std::filesystem::remove_all(tmp);
}

TEST_CASE("P11 Task 2: loadRecordingForTest with no bundle returns 0 events (no regression)", "[gui][events]") {
  // A CSV with no .json bundle sidecar must load without crash and report 0 events.
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11_task2_no_bundle";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-130000-ads1292-studio.csv").string();

  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 1500; ++i) {
    ads1292::StreamSample s;
    double t = i / 500.0;
    double v = 0.0;
    for (double bt = 0.2; bt < 3.0; bt += 60.0 / 72.0) {
      double d = t - bt;
      v += 200.0 * std::exp(-(d * d) / (2 * 0.01 * 0.01));
    }
    s.ch2 = static_cast<int>(v); s.ch1 = 0; s.status_byte = 0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);

  // Confirm no bundle sidecar exists
  REQUIRE_FALSE(ads1292::io::is_recording_bundle_path(
    ads1292::io::recording_bundle_path(csv_path)));

  ads1292::gui::MainWindow win;
  win.loadRecordingForTest(csv_path);

  REQUIRE(win.reviewLoadedForTest());
  REQUIRE(win.reviewEventCountForTest() == 0);

  std::filesystem::remove_all(tmp);
}

// ── P11 Task 3: save-format checkboxes + recording-state surfacing ─────────────

// ── P11 Phase 6 Task 1: unified loadRecording (CSV + H5) ─────────────────────

#ifdef ADS1292_HAVE_HDF5
#include "ads1292/io/H5Io.h"
#include "ads1292/io/Bundle.h"
#include "ads1292/io/AcquisitionIo.h"

TEST_CASE("P11 Phase 6 Task 1: loadRecording loads H5 with embedded bundle events", "[gui][h5]") {
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11_t1_load_h5";
  std::filesystem::create_directories(tmp);
  auto h5_path = (tmp / "rec.h5").string();

  // Author a small recording (1500 synthetic ECG samples)
  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 1500; ++i) {
    ads1292::StreamSample s;
    double t = i / 500.0;
    double v = 0.0;
    for (double bt = 0.2; bt < 3.0; bt += 60.0 / 72.0) {
      double d = t - bt;
      v += 200.0 * std::exp(-(d * d) / (2 * 0.01 * 0.01));
    }
    s.ch2 = static_cast<int>(v);
    s.ch1 = 0;
    s.status_byte = 0;
    s.timestamp = t;
    s.sample_index = i;
    samples.push_back(s);
  }

  // Build 2 known EventMarkers
  std::vector<ads1292::EventMarker> events2;
  {
    ads1292::EventMarker e1;
    e1.timestamp_seconds = 0.1;
    e1.label = "rest";
    e1.notes = "baseline";
    events2.push_back(e1);

    ads1292::EventMarker e2;
    e2.timestamp_seconds = 0.5;
    e2.label = "motion";
    e2.notes = "arm movement";
    events2.push_back(e2);
  }

  // Build bundle JSON string and write H5
  auto bundle = ads1292::io::build_recording_bundle(
    "rec.csv",
    ads1292::SessionMetadata{},
    events2,
    ads1292::Calibration{},
    ads1292::io::AcquisitionProvenance{},
    ads1292::io::protocol_template(),
    ads1292::io::quality_gate_template(),
    ads1292::RecordingProcessingSettings{},
    500.0,
    "");
  auto bundle_json = bundle.dump(2);

  ads1292::io::H5Attrs attrs;
  attrs.schema = "ads1292-h5/1";
  attrs.csv_name = "rec.csv";
  attrs.sample_rate_hz = "500.0";
  attrs.sample_count = std::to_string(samples.size());

  ads1292::io::write_recording_h5(h5_path, samples, bundle_json, attrs);

  // Load via the unified loadRecording path
  ads1292::gui::MainWindow mw;
  REQUIRE(mw.loadRecording(h5_path));
  REQUIRE(mw.reviewLoadedForTest());
  REQUIRE(mw.reviewEventCountForTest() == 2);

  std::filesystem::remove_all(tmp);
}
#endif  // ADS1292_HAVE_HDF5

TEST_CASE("P11 Phase 6 Task 1: loadRecording CSV path still works (regression)", "[gui][recording]") {
  // Confirm the existing CSV loadRecordingForTest path works (now routes through loadRecording)
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11_t1_load_csv";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-120000-ads1292-studio.csv").string();

  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 1500; ++i) {
    ads1292::StreamSample s;
    double t = i / 500.0;
    double v = 0.0;
    for (double bt = 0.2; bt < 3.0; bt += 60.0 / 72.0) {
      double d = t - bt;
      v += 200.0 * std::exp(-(d * d) / (2 * 0.01 * 0.01));
    }
    s.ch2 = static_cast<int>(v); s.ch1 = 0; s.status_byte = 0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);

  ads1292::gui::MainWindow win;
  REQUIRE(win.loadRecording(csv_path));
  REQUIRE(win.reviewLoadedForTest());
  REQUIRE(win.reviewEventCountForTest() == 0);  // no bundle sidecar

  std::filesystem::remove_all(tmp);
}

// ── P11 Phase 6 Task 2: Load button + loadAndShowReview seam ─────────────────

TEST_CASE("P11 Phase 6 Task 2: Load button is present after construction", "[gui][load]") {
  // Verify the Load button was created in the ctor. Uses the test accessor
  // rather than traversing the widget tree, so it remains valid even if the
  // toolbar layout changes.
  ensureApp();
  ads1292::gui::MainWindow mw;
  REQUIRE(mw.loadButtonPresentForTest());
}

TEST_CASE("P11 Phase 6 Task 2: loadAndShowReview loads CSV and switches to Review tab", "[gui][load]") {
  // The Load button's clicked lambda calls QFileDialog (modal, cannot be driven
  // offscreen) and then delegates to loadAndShowReview. This test exercises that
  // seam directly: load a CSV and verify that (a) the data is loaded and (b) the
  // current tab switches to the Review waveform tab.
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11_t2_load_tab";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-120000-ads1292-studio.csv").string();

  // Author a small synthetic ECG recording (1500 samples).
  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 1500; ++i) {
    ads1292::StreamSample s;
    double t = i / 500.0;
    double v = 0.0;
    for (double bt = 0.2; bt < 3.0; bt += 60.0 / 72.0) {
      double d = t - bt;
      v += 200.0 * std::exp(-(d * d) / (2 * 0.01 * 0.01));
    }
    s.ch2 = static_cast<int>(v); s.ch1 = 0; s.status_byte = 0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);

  ads1292::gui::MainWindow mw;

  // Before loading, the current tab should NOT be the Review tab (starts on Live ECG).
  REQUIRE_FALSE(mw.currentTabIsReviewForTest());

  // Exercise the seam: load the CSV and switch to the Review tab.
  mw.loadAndShowReview(csv_path);

  // Recording must be loaded successfully.
  REQUIRE(mw.reviewLoadedForTest());

  // The current tab must now be the Review waveform tab.
  REQUIRE(mw.currentTabIsReviewForTest());

  std::filesystem::remove_all(tmp);
}

// ── P11 Phase 4 Task 1: Refresh enumerates ADS ports into the combo ──────────

TEST_CASE("P11D Task 1: refreshPorts populates the port combo (boardless -> no-port placeholder)", "[gui][ports]") {
  ensureApp();
  ads1292::gui::MainWindow mw;
  mw.refreshPortsForTest();
  // On a boardless host list_ads_ports() returns empty -> combo has "(no port)".
  // With a board attached it has real ports. Either way count >= 1 and no crash.
  REQUIRE(mw.portComboCountForTest() >= 1);
}

// ── P11 Phase 4 Task 2: Connect — background firmware query + connection state ─

TEST_CASE("P11D Task 2: onConnectResult sets connectedPort on success, clears on failure", "[gui][connect]") {
  ensureApp();
  ads1292::gui::MainWindow mw;

  // Inject a successful connect result (simulates the background thread returning ok).
  // The real serial open needs hardware; the test drives the result-state machine only.
  mw.injectConnectResultForTest(true, "/dev/cu.usbserial-1", "1.12");
  REQUIRE(mw.connectedPortForTest() == "/dev/cu.usbserial-1");

  // Inject a failure result — the connected port must be cleared.
  mw.injectConnectResultForTest(false, "", "open failed");
  REQUIRE(mw.connectedPortForTest().empty());
}

// ── P11 Phase 4 Task 3: Start branches on real device vs simulator ────────────

TEST_CASE("P11D Task 3: startUsesRealDeviceForTest reflects connectedPort (branch-selection seam)", "[gui][ports]") {
  // The real-serial Start is hardware-only. This test exercises the SELECTION
  // logic: with no connected port the simulator path is selected; after
  // injectConnectResultForTest(ok=true) the real-device path is selected.
  // No serial port is actually opened in this test.
  ensureApp();
  ads1292::gui::MainWindow mw;

  // No port connected yet → simulator path
  REQUIRE_FALSE(mw.startUsesRealDeviceForTest());

  // Inject a successful connect result (simulates background thread returning ok)
  mw.injectConnectResultForTest(true, "/dev/cu.x", "1.12");
  REQUIRE(mw.startUsesRealDeviceForTest());

  // Inject a failure → disconnected → back to simulator path
  mw.injectConnectResultForTest(false, "", "open failed");
  REQUIRE_FALSE(mw.startUsesRealDeviceForTest());
}

TEST_CASE("MainWindow save-format checkboxes: default state and H5 opt propagation", "[gui][recording]") {
  ensureApp();
  ads1292::gui::MainWindow win;

  // Both checkboxes must be wired (Task 3)
  REQUIRE(win.saveCheckboxesPresentForTest());

  // HDF5 is checked by default; CSV is present (always-on / informational)
  REQUIRE(win.saveH5EnabledForTest());

  // Verify H5 opt propagation via the synchronous finalize seam:
  // pre-author a small CSV, inject it, and check that toggling H5 off
  // causes finalize to return an empty h5_path.
  auto tmp = std::filesystem::temp_directory_path() / "p11_t3_h5check";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-120000-ads1292-studio.csv").string();

  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 20; ++i) {
    ads1292::StreamSample s; s.ch2 = 100; s.ch1 = 0; s.timestamp = i / 500.0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);
  win.setRecordingCsvPathForTest(csv_path);

  // With H5 on (default) the bundle must exist
  auto r_on = win.finalizeForTest();
  REQUIRE(r_on.wrote);
  REQUIRE(std::filesystem::exists(r_on.bundle_path));

  // Toggle H5 off: h5_path must be empty (write_h5=false → no HDF5 written)
  win.setSaveH5ForTest(false);
  REQUIRE_FALSE(win.saveH5EnabledForTest());
  auto r_off = win.finalizeForTest();
  REQUIRE(r_off.wrote);
  REQUIRE(r_off.h5_path.empty());

  // Restore default and verify
  win.setSaveH5ForTest(true);
  REQUIRE(win.saveH5EnabledForTest());

  std::filesystem::remove_all(tmp);
}

// ── P11 Phase 3 Task 1: SessionPanel widget ───────────────────────────────────

#include "ads1292/gui/SessionPanel.h"

TEST_CASE("P11P3 Task 1: SessionPanel setMetadata round-trips through metadata()", "[gui][session]") {
  ensureApp();
  ads1292::gui::SessionPanel sp;

  ads1292::SessionMetadata m;
  m.session_id = "S-42";
  m.subject_id = "subjX";
  m.electrode  = "MOTAC";
  sp.setMetadata(m);

  REQUIRE(sp.metadata().session_id == "S-42");
  REQUIRE(sp.metadata().subject_id == "subjX");
  REQUIRE(sp.metadata().electrode  == "MOTAC");
}

TEST_CASE("P11P3 Task 1: unedited SessionPanel defaults match SessionMetadata{}", "[gui][session]") {
  ensureApp();
  ads1292::gui::SessionPanel sp2;

  REQUIRE(sp2.metadata().subject_id  == "anonymous");
  REQUIRE(sp2.metadata().montage     == "RA/LA/RL torso");
  REQUIRE(sp2.metadata().session_id.empty());
}

// ── P11 Phase 3 Task 2: SessionPanel metadata wired into the recording bundle ──

// ── P11 Phase 5 Task 1: SessionPanel Validation + Protocol tabs ──────────────

TEST_CASE("P11P5 Task 1: qualityGate() returns QualityGate{} defaults on unedited panel", "[gui][session][qgate]") {
  ensureApp();
  ads1292::gui::SessionPanel sp;

  auto qg = sp.qualityGate();
  REQUIRE(qg.min_duration_seconds   == Approx(8.0));
  REQUIRE(qg.min_contact_ok_percent == Approx(95.0));
  REQUIRE(qg.min_r_peaks            == 5);
  REQUIRE(qg.min_hr_bpm             == Approx(35.0));
  REQUIRE(qg.max_hr_bpm             == Approx(180.0));
  REQUIRE(qg.require_qrs_clear      == true);
  REQUIRE_FALSE(qg.max_baseline_drift_counts.has_value());
  REQUIRE_FALSE(qg.max_noise_rms_counts.has_value());
  REQUIRE_FALSE(qg.max_peak_to_peak_counts.has_value());
}

TEST_CASE("P11P5 Task 1: protocol() returns TestProtocol{} defaults on unedited panel", "[gui][session][protocol]") {
  ensureApp();
  ads1292::gui::SessionPanel sp;

  auto p = sp.protocol();
  REQUIRE(p.name                  == "ADS1292 validation protocol");
  REQUIRE(p.objective             == "");
  REQUIRE(p.operator_instructions == "Follow the listed protocol steps.");
  REQUIRE(p.acceptance_notes      == "Review quality gate and artifacts before accepting the run.");
  REQUIRE(p.steps.empty());
}

TEST_CASE("P11P5 Task 1: metadata() still works after tab restructure", "[gui][session]") {
  ensureApp();
  ads1292::gui::SessionPanel sp;

  ads1292::SessionMetadata m;
  m.session_id = "S";
  m.subject_id = "test-subject";
  sp.setMetadata(m);

  REQUIRE(sp.metadata().session_id == "S");
  REQUIRE(sp.metadata().subject_id == "test-subject");
}

TEST_CASE("P11P5 Task 1: test seams allow value change and round-trip", "[gui][session]") {
  ensureApp();
  ads1292::gui::SessionPanel sp;

  // Change protocol name via seam and verify round-trip
  sp.setProtocolNameForTest("X");
  REQUIRE(sp.protocol().name == "X");

  // Change min duration via seam and verify round-trip
  sp.setMinDurationForTest(15.0);
  REQUIRE(sp.qualityGate().min_duration_seconds == Approx(15.0));
}

// ── P11 Phase 5 Task 2: wire qualityGate + protocol into the bundle ────────────

TEST_CASE("P11P5 Task 2: sessionPanel qualityGate + protocol are written into the bundle", "[gui][session][qgate][protocol]") {
  // Strategy: construct MainWindow; via SessionPanel test seams set a distinctive
  // protocol name and a non-default min_duration_seconds; run the synchronous
  // finalize seam; read the bundle and verify the values round-trip.
  // Before the wiring, opt.quality_gate/opt.protocol were the templates (defaults),
  // so the test would fail.
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11p5_task2_qgate_proto";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-120000-ads1292-studio.csv").string();

  // Author a small recording
  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 50; ++i) {
    ads1292::StreamSample s;
    s.ch2 = (i % 10 < 2) ? 300 : 0;
    s.ch1 = 0;
    s.timestamp = i / 500.0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);

  ads1292::gui::MainWindow mw;
  mw.setRecordingsDirForTest(tmp.string());
  mw.setRecordingCsvPathForTest(csv_path);

  // Set distinctive values via the SessionPanel test seams
  REQUIRE(mw.sessionPanelForTest() != nullptr);
  mw.sessionPanelForTest()->setProtocolNameForTest("MOTAC protocol");
  mw.sessionPanelForTest()->setMinDurationForTest(12.5);

  // Run finalize synchronously
  auto r = mw.finalizeForTest();
  REQUIRE(r.wrote == true);
  REQUIRE(std::filesystem::exists(r.bundle_path));

  // Read back the bundle and verify protocol + quality_gate round-trip
  auto bundle = ads1292::io::read_recording_bundle(r.bundle_path);
  auto p = ads1292::io::protocol_from_bundle(bundle);
  auto g = ads1292::io::quality_gate_from_bundle(bundle);

  REQUIRE(p.name == "MOTAC protocol");
  REQUIRE(g.min_duration_seconds == Approx(12.5));

  std::filesystem::remove_all(tmp);
}

TEST_CASE("P11P3 Task 2: sessionPanelForTest metadata is written into the bundle", "[gui][session]") {
  // Strategy: construct MainWindow, set session metadata on the panel, run the
  // synchronous finalize seam, read the produced bundle, verify metadata fields.
  // Before the wiring, opt.metadata was SessionMetadata{} → session_id empty → fail.
  ensureApp();

  auto tmp = std::filesystem::temp_directory_path() / "p11p3_task2_meta_bundle";
  std::filesystem::create_directories(tmp);
  auto csv_path = (tmp / "2026-01-01-120000-ads1292-studio.csv").string();

  // Author a small recording
  std::vector<ads1292::StreamSample> samples;
  for (int i = 0; i < 50; ++i) {
    ads1292::StreamSample s;
    s.ch2 = (i % 10 < 2) ? 300 : 0;
    s.ch1 = 0;
    s.timestamp = i / 500.0;
    samples.push_back(s);
  }
  ads1292::io::write_recording_csv(csv_path, samples);

  ads1292::gui::MainWindow mw;
  mw.setRecordingsDirForTest(tmp.string());
  mw.setRecordingCsvPathForTest(csv_path);

  // Verify the seam is present and returns non-null
  REQUIRE(mw.sessionPanelForTest() != nullptr);

  // Set known session metadata on the panel
  ads1292::SessionMetadata m;
  m.session_id = "bundle-sess";
  m.electrode  = "MOTAC";
  mw.sessionPanelForTest()->setMetadata(m);

  // Run finalize synchronously
  auto r = mw.finalizeForTest();
  REQUIRE(r.wrote == true);
  REQUIRE(std::filesystem::exists(r.bundle_path));

  // Read back the bundle and verify the session metadata fields
  auto bundle = ads1292::io::read_recording_bundle(r.bundle_path);
  auto md = ads1292::io::metadata_from_bundle(bundle);
  REQUIRE(md.session_id == "bundle-sess");
  REQUIRE(md.electrode  == "MOTAC");

  std::filesystem::remove_all(tmp);
}
