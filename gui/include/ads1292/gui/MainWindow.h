// gui/include/ads1292/gui/MainWindow.h
#pragma once
#include <QCloseEvent>
#include <QMainWindow>
#include <QTimer>
#include <QString>
#include <memory>
#include <string>
#include <thread>

#include "ads1292/gui/Preferences.h"

#include "ads1292/gui/LiveScope.h"
#include "ads1292/gui/StatusPanel.h"
#include "ads1292/gui/EventConsole.h"
#include "ads1292/gui/GuiState.h"
#include "ads1292/gui/PqrstPanel.h"
#include "ads1292/gui/SpectrumPanel.h"
#include "ads1292/gui/QualityInfoPanel.h"
#include "ads1292/gui/ReviewEventLogPanel.h"
#include "ads1292/gui/SessionPanel.h"
#include "ads1292/qt/AcquisitionWorker.h"
#include "ads1292/qt/QSerialByteTransport.h"
#include "ads1292/acq/IDeviceSource.h"
#include "ads1292/acq/AdsProtocolDevice.h"
#include "ads1292/dsp/Display.h"
#include "ads1292/io/LiveRecordingFinalize.h"
#include "ads1292/dsp/LiveCalibration.h"
#include "ads1292/gui/ReportExport.h"

// Forward-declare IWaveformPlot so we don't pull in the backend header here.
namespace ads1292::gui { class IWaveformPlot; }

#include <optional>
#include <QCheckBox>
#include <QComboBox>
#include <QPushButton>
class QTabWidget;

namespace ads1292::gui {

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow() override;

protected:
    /// Saves preferences to QSettings when the window is closed (real app close only;
    /// test objects destroyed via dtor do NOT trigger this and do NOT pollute QSettings).
    void closeEvent(QCloseEvent* event) override;

public:
    /// Synchronous smoke/test helper: run simulator for streamBatches batches,
    /// drain the live queue into the scope, return the count drained.
    int runSimulatorToCompletion(int streamBatches);

    /// Test hook: toggle the QRS (bandpass) filter + refresh + update SNR/HR labels.
    void setDisplayFilterForTest(bool qrs);

    /// Test hook: return the last SNR dB from the live frame (0.0 when invalid).
    double liveSnrDbForTest() const;

    /// Load a recording (CSV or H5) into the review panels.
    /// Detects the format by file extension (case-insensitive: .h5 vs anything else).
    /// Returns true on success (non-empty samples), false on failure.
    /// H5 events are read from the embedded bundle_json; CSV events from the sidecar bundle.
    bool loadRecording(const std::string& path);

    /// Load a CSV recording into the review panels. Safe to call from tests.
    /// Guards against empty/invalid files. Sets reviewLoaded_ = true on success.
    /// Also reads events from the recording bundle (if present) and populates
    /// the review event log panel.
    /// Thin wrapper around loadRecording(csvPath).
    void loadRecordingForTest(const std::string& csvPath);

    /// Load a recording and switch to the Review tab on success.
    /// This is the testable seam that the Load button's clicked lambda calls
    /// after the QFileDialog returns a path. Calling this directly in tests avoids
    /// driving the modal QFileDialog (which cannot be driven offscreen).
    void loadAndShowReview(const std::string& path);

    // ── Preferences persistence seams (P11 Phase 12 Task 2) ──────────────────

    /// Read the current widget states into a Preferences struct.
    /// Public seam: tests can call applyPreferences(p) then currentPreferences()
    /// to round-trip widget state without touching the global QSettings store.
    Preferences currentPreferences() const;

    /// Apply a Preferences struct to the widgets (save checkboxes, mode/window
    /// combos, port combo). Calls refreshControls() after applying.
    void applyPreferences(const Preferences& p);

    /// Returns true if a recording has been successfully loaded into the review panels.
    bool reviewLoadedForTest() const { return review_loaded_; }

    /// Returns the number of events loaded from the recording bundle on the last
    /// successful loadRecordingForTest call (0 if no bundle or no events).
    int reviewEventCountForTest() const { return static_cast<int>(loadedEvents_.size()); }

    /// Returns true if the Load button member is non-null (i.e., button was created).
    bool loadButtonPresentForTest() const { return loadBtn_ != nullptr; }

    // ── Control-gating test seams (P11 Phase 7 Task 1) ───────────────────────

    /// True iff startBtn_ is present and enabled.
    bool startEnabledForTest() const { return startBtn_ && startBtn_->isEnabled(); }

    /// True iff stopBtn_ is present and enabled.
    bool stopEnabledForTest() const { return stopBtn_ && stopBtn_->isEnabled(); }

    /// True iff loadBtn_ is present and enabled.
    bool loadEnabledForTest() const { return loadBtn_ && loadBtn_->isEnabled(); }

    /// Set streaming_ and call refreshControls() — drives the gating matrix from a test.
    void setStreamingForTest(bool s) { streaming_ = s; refreshControls(); }

    /// Returns true if the currently visible tab is the Review waveform tab.
    bool currentTabIsReviewForTest() const {
        return tabs_ && reviewWaveform_ &&
               tabs_->currentWidget() == reviewWaveform_->widget();
    }

    // ── Save-format checkbox test seams ───────────────────────────────────────

    // ── Port combo test seams (P11 Phase 4 Task 1) ───────────────────────────

    /// Returns the number of items currently in the port combo (0 when nullptr).
    int portComboCountForTest() const { return portCombo_ ? portCombo_->count() : 0; }

    /// Calls refreshPorts() — exercise the enumeration from a test without clicking the button.
    void refreshPortsForTest() { refreshPorts(); }

    // ── Connect state test seams (P11 Phase 4 Task 2) ────────────────────────

    /// Injects a connect result directly into onConnectResult (GUI thread).
    /// Bypasses the background thread + serial open — lets tests exercise the
    /// connect-state machine without hardware.
    void injectConnectResultForTest(bool ok, const std::string& port,
                                    const std::string& detail) {
        onConnectResult(ok, port, detail);
    }

    /// Returns the raw device path of the currently connected port (empty = disconnected).
    std::string connectedPortForTest() const { return connectedPort_; }

    // ── Start branch-selection test seam (P11 Phase 4 Task 3) ────────────────

    /// Returns true iff a port is connected, meaning the Start lambda will route
    /// acquisition to the real device. Returns false → falls back to the simulator.
    /// The real-serial Start is hardware-only; this tests the branch-selection logic.
    bool startUsesRealDeviceForTest() const { return !connectedPort_.empty(); }

    // ── Save-format checkbox test seams ───────────────────────────────────────

    /// True iff the HDF5 save checkbox is present and checked (default: true).
    bool saveH5EnabledForTest() const { return saveH5Check_ && saveH5Check_->isChecked(); }

    /// True iff both save-format checkboxes were wired (Task 3).
    bool saveCheckboxesPresentForTest() const {
        return saveH5Check_ != nullptr && saveCsvCheck_ != nullptr;
    }

    /// Set the HDF5 save checkbox state; propagates into the next buildFinalizeOptions call.
    void setSaveH5ForTest(bool on) { if (saveH5Check_) saveH5Check_->setChecked(on); }

    /// True iff the XLSX save checkbox is present (i.e. was created in the ctor).
    bool saveXlsxPresentForTest() const { return saveXlsxCheck_ != nullptr; }

    /// True iff the XLSX save checkbox is present and enabled (i.e. not gated while streaming).
    bool saveXlsxEnabledForTest() const { return saveXlsxCheck_ && saveXlsxCheck_->isEnabled(); }

    /// Set the XLSX save checkbox state; propagates into the next buildFinalizeOptions call.
    void setSaveXlsxForTest(bool b) { if (saveXlsxCheck_) saveXlsxCheck_->setChecked(b); }

    // ── Recording persistence test seams ──────────────────────────────────────

    /// Override the recordings directory (used by Start to generate the CSV path).
    void setRecordingsDirForTest(const std::string& dir) { recordingsDir_ = dir; }

    /// Directly set the CSV path (used by tests that pre-author a CSV and want to
    /// invoke the finalize step without running a full acquisition).
    void setRecordingCsvPathForTest(const std::string& path) { recordingCsvPath_ = path; }

    /// Synchronous finalize seam: builds the same FinalizeOptions as onWorkerFinished
    /// and calls finalize_live_recording synchronously, returning its result.
    /// Used by tests to avoid driving the full async event-loop + thread path.
    ads1292::io::FinalizeResult finalizeForTest();

    /// Test seam: direct access to the EventConsole so tests can inject events
    /// via addPointEventForTest before calling finalizeForTest.
    EventConsole* eventConsoleForTest() { return eventConsole_; }

    /// Test seam: direct access to the SessionPanel so tests can set metadata
    /// before calling finalizeForTest and verify the bundle round-trip.
    SessionPanel* sessionPanelForTest() { return sessionPanel_; }

    // ── Calibrate Live test seams (P11 Phase 9 Task 2) ───────────────────────

    /// True iff calibrateBtn_ was created (i.e., the button is present in the toolbar).
    bool calibrateButtonPresentForTest() const { return calibrateBtn_ != nullptr; }

    // ── Export Report test seams (P11 Phase 10 Task 1) ───────────────────────

    /// True iff exportReportBtn_ was created (i.e., the button is present in the toolbar).
    bool exportReportButtonPresentForTest() const { return exportReportBtn_ != nullptr; }

    /// Testable seam: produce a report from the loaded recording to outDir.
    /// Called by the Export Report button lambda after the QFileDialog returns a path.
    /// Calling this directly in tests avoids driving the modal dialog.
    ReportExportResult exportReportTo(const std::string& outDir);

    // ── Session Index test seams (P11 Phase 10 Task 2) ───────────────────────

    /// True iff sessionIndexBtn_ was created (i.e., the button is present in the toolbar).
    bool sessionIndexButtonPresentForTest() const { return sessionIndexBtn_ != nullptr; }

    /// Testable seam: scan dir and write index.json; returns the index.json path.
    /// Called by the Session Index button lambda after the QFileDialog returns a path.
    /// Calling this directly in tests avoids driving the modal dialog.
    std::string sessionIndexFor(const std::string& dir);

    /// Inject a successful calibration result directly into onCalibrateResult (GUI thread).
    /// Bypasses the hardware-only device measurement thread — lets tests exercise the
    /// result-state machine without physical hardware.
    void injectCalibrateResultForTest(const ads1292::LiveStreamCalibration& cal) {
        onCalibrateResult(true, cal, "");
    }

    /// Returns true iff a live calibration result has been stored (liveCalibration_ has a value).
    bool hasLiveCalibrationForTest() const { return liveCalibration_.has_value(); }

signals:
    /// Emitted (from invokeMethod on the GUI thread) when the background finalize
    /// thread completes. Connected slot appends the line to the event log.
    void finalizeLogged(QString line);

private slots:
    /// Runs on the GUI thread via QueuedConnection from worker_.finished(int).
    void onWorkerFinished(int sampleCount);

    /// Runs on the GUI thread (posted via QMetaObject::invokeMethod from the
    /// background connect thread). Updates connection state and re-enables the UI.
    void onConnectResult(bool ok, const std::string& port, const std::string& detail);

    /// Runs on the GUI thread (posted via QMetaObject::invokeMethod from the
    /// background calibrate thread, or called directly by injectCalibrateResultForTest).
    /// On success: stores the normalized calibration and updates the status line.
    /// On failure: logs the detail message to the event log.
    void onCalibrateResult(bool ok, const ads1292::LiveStreamCalibration& cal,
                           const std::string& detail);

private:
    void onTick();
    void updateLiveReadout();
    ads1292::io::FinalizeOptions buildFinalizeOptions() const;

    /// Enumerates ADS1x9x serial ports and repopulates portCombo_.
    /// Falls back to a single "(no port)" item when no device is detected.
    void refreshPorts();

    /// Applies the enable/disable matrix from the current streaming_/connecting_ state.
    /// Call at every state transition and once at the end of the ctor for the idle initial state.
    void refreshControls();

    // ── Toolbar port controls (P11 Phase 4) ───────────────────────────────────
    QComboBox*   portCombo_   = nullptr;  ///< Port selection combo
    QPushButton* refreshBtn_  = nullptr;  ///< Refresh button
    QPushButton* connectBtn_  = nullptr;  ///< Connect button

    // ── Toolbar mode/window combos (P11 Phase 12 Task 2: promoted from locals) ─
    QComboBox*   modeCombo_   = nullptr;  ///< Acquisition mode combo (Live/Raw)
    QComboBox*   winCombo_    = nullptr;  ///< Display window combo (4 s/8 s/…)

    // ── Connect state (P11 Phase 4 Task 2) ────────────────────────────────────
    std::string  connectedPort_;          ///< Device path of connected port (empty = disconnected)
    bool         connecting_ = false;     ///< True while background connect thread is running
    std::thread  connectThread_;          ///< Background connect thread; joined in dtor + before respawn

    // ── Session metadata panel (left pane of the central splitter) ────────────
    SessionPanel* sessionPanel_ = nullptr;

    // ── Live tab widgets ───────────────────────────────────────────────────────
    LiveScope*    scope_        = nullptr;
    StatusPanel*  statusPanel_  = nullptr;
    EventConsole* eventConsole_ = nullptr;

    // ── Review tab widgets ─────────────────────────────────────────────────────
    // IWaveformPlot for the review waveform (ECG + resp + R-peak markers).
    // Owned via unique_ptr; the underlying widget is embedded in the tab.
    std::unique_ptr<IWaveformPlot> reviewWaveform_;

    PqrstPanel*          pqrstPanel_          = nullptr;
    SpectrumPanel*        spectrumPanel_       = nullptr;
    QualityInfoPanel*     qualityInfoPanel_    = nullptr;
    ReviewEventLogPanel*  reviewEventLogPanel_ = nullptr;

    // ── Tab widget ─────────────────────────────────────────────────────────────
    QTabWidget* tabs_ = nullptr;

    // ── Worker / acquisition ──────────────────────────────────────────────────
    ads1292::qt::AcquisitionWorker worker_;
    std::unique_ptr<ads1292::acq::IDeviceSource> activeSource_;

    // ── Real-device lifetime (P11 Phase 4 Task 3) ─────────────────────────────
    // Created at Start when connectedPort_ is non-empty; reset only after the
    // worker has stopped + finalize has completed (transport must outlive the worker).
    std::unique_ptr<ads1292::qt::QSerialByteTransport> transport_;
    std::unique_ptr<ads1292::acq::AdsProtocolDevice>   realDevice_;

    // ── Tick timer ────────────────────────────────────────────────────────────
    QTimer timer_;

    // ── State ─────────────────────────────────────────────────────────────────
    GuiState state_;
    int      lastCount_    = 0;
    bool     review_loaded_ = false;

    // Events loaded from the recording bundle on the last loadRecordingForTest call.
    // Populated by loadRecordingForTest; empty when no bundle exists.
    std::vector<ads1292::EventMarker> loadedEvents_;

    // Display filter settings (live — driven by toolbar checkboxes)
    ads1292::dsp::SoftwareFilterSettings filter_;

    // ── Recording persistence ─────────────────────────────────────────────────
    std::string recordingCsvPath_;     ///< path generated at Start; passed to worker
    std::string recordingStartedAt_;   ///< ISO-8601 start time set at Start
    std::string recordingsDir_;        ///< base directory override (empty = default)
    std::string recordingMode_;        ///< acquisition mode at Start: "live" or "raw"

    // ── Finalize thread ───────────────────────────────────────────────────────
    std::thread finalizeThread_;       ///< detached → stored, joined in dtor & before respawn

    /// Save-format checkboxes in the toolbar.
    /// saveCsvCheck_: informational (CSV is always written), permanently disabled.
    /// saveH5Check_: HDF5 bundle (on by default); gated while streaming.
    /// saveXlsxCheck_: XLSX convenience export (off by default); gated while streaming.
    QCheckBox* saveCsvCheck_  = nullptr;
    QCheckBox* saveH5Check_   = nullptr;
    QCheckBox* saveXlsxCheck_ = nullptr;

    /// Load button in the toolbar (added in Task 2). Non-null after construction.
    QPushButton* loadBtn_ = nullptr;

    // ── Start / Stop buttons (P11 Phase 7 Task 1: promoted from ctor locals) ──
    QPushButton* startBtn_ = nullptr;
    QPushButton* stopBtn_  = nullptr;

    // ── Streaming state (P11 Phase 7 Task 1) ─────────────────────────────────
    bool streaming_ = false;  ///< True while acquisition worker is running

    // ── Calibrate Live (P11 Phase 9 Task 2) ──────────────────────────────────
    QPushButton* calibrateBtn_ = nullptr; ///< "Calibrate Live" toolbar button

    // ── Export Report (P11 Phase 10 Task 1) ──────────────────────────────────
    QPushButton* exportReportBtn_ = nullptr; ///< "Export Report" toolbar button

    // ── Session Index (P11 Phase 10 Task 2) ──────────────────────────────────
    QPushButton* sessionIndexBtn_ = nullptr; ///< "Session Index" toolbar button

    // ── Loaded recording storage (P11 Phase 10 Task 1) ───────────────────────
    /// Samples loaded by the last successful loadRecording() call.
    /// Stored so exportReportTo() can produce the report without re-reading the file.
    std::vector<ads1292::StreamSample> loadedSamples_;

    /// Session metadata loaded from the bundle sidecar (or H5 embedded bundle)
    /// on the last successful loadRecording() call. Default SessionMetadata{} when absent.
    ads1292::SessionMetadata loadedMetadata_;

    /// Stored result of the most recent successful calibration.
    /// Flows into the bundle's acquisition.live_calibration via buildFinalizeOptions().
    std::optional<ads1292::LiveStreamCalibration> liveCalibration_;

    bool calibrating_ = false; ///< True while the calibrate background thread is running

    /// Background calibrate thread; joined in dtor + before respawn (UAF prevention).
    /// Note: the actual ADS1292 register-level measurement (run_live_stream_calibration
    /// from device.py) is HARDWARE-ONLY — not ported in this C++ build. The thread
    /// reports this as a documented failure via onCalibrateResult(false, ...).
    std::thread calibrateThread_;
};

} // namespace ads1292::gui
