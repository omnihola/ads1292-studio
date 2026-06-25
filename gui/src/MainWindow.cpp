// gui/src/MainWindow.cpp
#include "ads1292/gui/MainWindow.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include "ads1292/acq/IDeviceSource.h"
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QDockWidget>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QSplitter>
#include <QToolBar>
#include <QVBoxLayout>
#include <QWidget>
#include <QFile>
#include <QString>

namespace ads1292::gui {

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
{
    setWindowTitle("ADS1292 Studio");
    resize(1200, 750);

    // --- Toolbar ---
    auto* toolbar = addToolBar("Main");
    toolbar->setObjectName("MainToolBar");
    toolbar->setMovable(false);

    // Port controls
    auto* portCombo = new QComboBox(toolbar);
    portCombo->addItem("(no port)");
    portCombo->setToolTip("Serial port");
    toolbar->addWidget(portCombo);

    auto* refreshBtn = new QPushButton("Refresh", toolbar);
    toolbar->addWidget(refreshBtn);

    auto* connectBtn = new QPushButton("Connect", toolbar);
    toolbar->addWidget(connectBtn);

    toolbar->addSeparator();

    // Mode
    auto* modeCombo = new QComboBox(toolbar);
    modeCombo->addItem("Live");
    modeCombo->addItem("Raw");
    toolbar->addWidget(new QLabel("Mode:", toolbar));
    toolbar->addWidget(modeCombo);

    toolbar->addSeparator();

    // Start / Stop
    auto* startBtn = new QPushButton("Start", toolbar);
    auto* stopBtn  = new QPushButton("Stop", toolbar);
    stopBtn->setEnabled(false);
    toolbar->addWidget(startBtn);
    toolbar->addWidget(stopBtn);

    toolbar->addSeparator();

    // Display controls
    toolbar->addWidget(new QLabel("Window:", toolbar));
    auto* winCombo = new QComboBox(toolbar);
    winCombo->addItems({"4 s", "8 s", "16 s", "30 s"});
    winCombo->setCurrentIndex(1);  // default 8 s
    toolbar->addWidget(winCombo);

    auto* autoscaleBox = new QCheckBox("Autoscale", toolbar);
    autoscaleBox->setChecked(true);
    toolbar->addWidget(autoscaleBox);

    // Display filter checkboxes: HP / Notch / LP / QRS (bandpass)
    toolbar->addSeparator();
    toolbar->addWidget(new QLabel("Filters:", toolbar));

    auto* hpBox    = new QCheckBox("HP",    toolbar);
    auto* notchBox = new QCheckBox("Notch", toolbar);
    auto* lpBox    = new QCheckBox("LP",    toolbar);
    auto* qrsBox   = new QCheckBox("QRS",   toolbar);

    toolbar->addWidget(hpBox);
    toolbar->addWidget(notchBox);
    toolbar->addWidget(lpBox);
    toolbar->addWidget(qrsBox);

    connect(hpBox, &QCheckBox::toggled, this, [this](bool checked) {
        filter_.highpass_enabled = checked;
        scope_->setFilterSettings(filter_);
    });
    connect(notchBox, &QCheckBox::toggled, this, [this](bool checked) {
        filter_.notch_enabled = checked;
        scope_->setFilterSettings(filter_);
    });
    connect(lpBox, &QCheckBox::toggled, this, [this](bool checked) {
        filter_.lowpass_enabled = checked;
        scope_->setFilterSettings(filter_);
    });
    connect(qrsBox, &QCheckBox::toggled, this, [this](bool checked) {
        filter_.bandpass_enabled = checked;
        scope_->setFilterSettings(filter_);
    });

    // --- Central widget: horizontal splitter (scope | status) ---
    auto* centralSplitter = new QSplitter(Qt::Horizontal, this);

    // Vertical splitter: scope top, console bottom
    auto* leftSplitter = new QSplitter(Qt::Vertical, centralSplitter);

    scope_        = new LiveScope(leftSplitter);
    eventConsole_ = new EventConsole(leftSplitter);

    leftSplitter->addWidget(scope_);
    leftSplitter->addWidget(eventConsole_);
    leftSplitter->setStretchFactor(0, 4);
    leftSplitter->setStretchFactor(1, 1);

    statusPanel_ = new StatusPanel(centralSplitter);

    centralSplitter->addWidget(leftSplitter);
    centralSplitter->addWidget(statusPanel_);
    centralSplitter->setStretchFactor(0, 4);
    centralSplitter->setStretchFactor(1, 1);

    setCentralWidget(centralSplitter);

    // --- Wire toolbar actions ---
    connect(winCombo, &QComboBox::currentIndexChanged, this, [this, winCombo](int) {
        QString text = winCombo->currentText();
        double secs = text.split(' ').first().toDouble();
        if (secs > 0.0) scope_->setWindowSeconds(secs);
    });

    connect(autoscaleBox, &QCheckBox::toggled, this, [this](bool on) {
        scope_->setAutoscale(on);
    });

    connect(startBtn, &QPushButton::clicked, this, [this, startBtn, stopBtn, modeCombo]() {
        startBtn->setEnabled(false);
        stopBtn->setEnabled(true);
        auto mode = (modeCombo->currentIndex() == 0)
                    ? ads1292::acq::AcquisitionMode::Live
                    : ads1292::acq::AcquisitionMode::Raw;
        // Create a fresh simulator per button press (not static)
        activeSource_ = std::make_unique<ads1292::acq::SimulatorDeviceSource>(200, 0);
        worker_.start(activeSource_.get(), mode, "");
    });

    connect(stopBtn, &QPushButton::clicked, this, [this, startBtn, stopBtn]() {
        worker_.requestStop();
        startBtn->setEnabled(true);
        stopBtn->setEnabled(false);
    });

    // --- Tick timer ---
    connect(&timer_, &QTimer::timeout, this, [this]() { onTick(); });
    timer_.start(30);

    // Initial status
    state_.nextStep      = "Select port and press Start";
    state_.connection    = "Disconnected";
    state_.channelMap    = "CH1=RESP CH2=ECG";
    state_.recordingState = "idle";
    statusPanel_->updateFromState(state_);
}

void MainWindow::onTick() {
    ads1292::StreamSample s;
    while (worker_.live_queue().try_pop(s)) {
        scope_->pushStreamSample(s);
        eventConsole_->setSampleClock(s.timestamp);
        ++lastCount_;
    }
    scope_->refresh();
    updateLiveReadout();

    state_.eventCount = static_cast<int>(eventConsole_->log().events().size());
    statusPanel_->updateFromState(state_);
}

void MainWindow::updateLiveReadout() {
    const auto& frame = scope_->lastFrame();
    if (frame.valid) {
        statusPanel_->updateLive(
            frame.snr.snr_db,
            frame.snr.valid,
            frame.heart_rate.median_bpm);
    }
}

void MainWindow::setDisplayFilterForTest(bool qrs) {
    filter_.bandpass_enabled = qrs;
    scope_->setFilterSettings(filter_);
    scope_->refresh();
    updateLiveReadout();
}

double MainWindow::liveSnrDbForTest() const {
    const auto& frame = scope_->lastFrame();
    return frame.valid ? frame.snr.snr_db : 0.0;
}

int MainWindow::runSimulatorToCompletion(int streamBatches) {
    ads1292::acq::SimulatorDeviceSource sim(streamBatches, 0);
    worker_.run_to_completion(&sim, ads1292::acq::AcquisitionMode::Live, "");

    // Queue is fully populated — drain it all into the scope
    int count = 0;
    ads1292::StreamSample s;
    while (worker_.live_queue().try_pop(s)) {
        scope_->pushStreamSample(s);
        eventConsole_->setSampleClock(s.timestamp);
        ++count;
    }
    scope_->refresh();
    return count;
}

} // namespace ads1292::gui
