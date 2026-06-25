// gui/include/ads1292/gui/MainWindow.h
#pragma once
#include <QMainWindow>
#include <QTimer>
#include <memory>
#include "ads1292/gui/LiveScope.h"
#include "ads1292/gui/StatusPanel.h"
#include "ads1292/gui/EventConsole.h"
#include "ads1292/gui/GuiState.h"
#include "ads1292/qt/AcquisitionWorker.h"
#include "ads1292/acq/IDeviceSource.h"
#include "ads1292/dsp/Display.h"

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

private:
    void onTick();
    void updateLiveReadout();

    // Widgets
    LiveScope*    scope_        = nullptr;
    StatusPanel*  statusPanel_  = nullptr;
    EventConsole* eventConsole_ = nullptr;

    // Worker
    ads1292::qt::AcquisitionWorker worker_;

    // Active device source (owned per-press by Start button)
    std::unique_ptr<ads1292::acq::IDeviceSource> activeSource_;

    // Tick timer
    QTimer timer_;

    // State
    GuiState state_;
    int      lastCount_ = 0;

    // Display filter settings (live — driven by toolbar checkboxes)
    ads1292::dsp::SoftwareFilterSettings filter_;
};

} // namespace ads1292::gui
