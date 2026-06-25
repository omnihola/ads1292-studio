// gui/include/ads1292/gui/MainWindow.h
#pragma once
#include <QMainWindow>
#include <QTimer>
#include <memory>
#include <string>

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

// Forward-declare IWaveformPlot so we don't pull in the backend header here.
namespace ads1292::gui { class IWaveformPlot; }

class QTabWidget;

namespace ads1292::gui {

class MainWindow : public QMainWindow {
public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow() override = default;

    /// Synchronous smoke/test helper: run simulator for streamBatches batches,
    /// drain the live queue into the scope, return the count drained.
    int runSimulatorToCompletion(int streamBatches);

    /// Test hook: toggle the QRS (bandpass) filter + refresh + update SNR/HR labels.
    void setDisplayFilterForTest(bool qrs);

    /// Test hook: return the last SNR dB from the live frame (0.0 when invalid).
    double liveSnrDbForTest() const;

    /// Load a CSV recording into the review panels. Safe to call from tests.
    /// Guards against empty/invalid files. Sets reviewLoaded_ = true on success.
    void loadRecordingForTest(const std::string& csvPath);

    /// Returns true if a recording has been successfully loaded into the review panels.
    bool reviewLoadedForTest() const { return review_loaded_; }

private:
    void onTick();
    void updateLiveReadout();

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

    // Display filter settings (live — driven by toolbar checkboxes)
    ads1292::dsp::SoftwareFilterSettings filter_;
};

} // namespace ads1292::gui
