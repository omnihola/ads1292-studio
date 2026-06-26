// gui/include/ads1292/gui/MainWindow.h
#pragma once
#include <QMainWindow>
#include <QTimer>
#include <QString>
#include <memory>
#include <string>
#include <thread>

#include "ads1292/gui/LiveScope.h"
#include "ads1292/gui/StatusPanel.h"
#include "ads1292/gui/EventConsole.h"
#include "ads1292/gui/GuiState.h"
#include "ads1292/gui/PqrstPanel.h"
#include "ads1292/gui/SpectrumPanel.h"
#include "ads1292/gui/QualityInfoPanel.h"
#include "ads1292/gui/ReviewEventLogPanel.h"
#include "ads1292/qt/AcquisitionWorker.h"
#include "ads1292/acq/IDeviceSource.h"
#include "ads1292/dsp/Display.h"
#include "ads1292/io/LiveRecordingFinalize.h"

// Forward-declare IWaveformPlot so we don't pull in the backend header here.
namespace ads1292::gui { class IWaveformPlot; }

#include <QCheckBox>
class QTabWidget;

namespace ads1292::gui {

class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow() override;

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

    /// Returns true if a recording has been successfully loaded into the review panels.
    bool reviewLoadedForTest() const { return review_loaded_; }

    /// Returns the number of events loaded from the recording bundle on the last
    /// successful loadRecordingForTest call (0 if no bundle or no events).
    int reviewEventCountForTest() const { return static_cast<int>(loadedEvents_.size()); }

    // ── Save-format checkbox test seams ───────────────────────────────────────

    /// True iff the HDF5 save checkbox is present and checked (default: true).
    bool saveH5EnabledForTest() const { return saveH5Check_ && saveH5Check_->isChecked(); }

    /// True iff both save-format checkboxes were wired (Task 3).
    bool saveCheckboxesPresentForTest() const {
        return saveH5Check_ != nullptr && saveCsvCheck_ != nullptr;
    }

    /// Set the HDF5 save checkbox state; propagates into the next buildFinalizeOptions call.
    void setSaveH5ForTest(bool on) { if (saveH5Check_) saveH5Check_->setChecked(on); }

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

signals:
    /// Emitted (from invokeMethod on the GUI thread) when the background finalize
    /// thread completes. Connected slot appends the line to the event log.
    void finalizeLogged(QString line);

private slots:
    /// Runs on the GUI thread via QueuedConnection from worker_.finished(int).
    void onWorkerFinished(int sampleCount);

private:
    void onTick();
    void updateLiveReadout();
    ads1292::io::FinalizeOptions buildFinalizeOptions() const;

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

    /// Task 3 adds these checkboxes to the toolbar; for Task 2 they are nullptr.
    /// onWorkerFinished treats nullptr saveH5Check_ as write_h5=true.
    QCheckBox* saveCsvCheck_ = nullptr;
    QCheckBox* saveH5Check_  = nullptr;
};

} // namespace ads1292::gui
