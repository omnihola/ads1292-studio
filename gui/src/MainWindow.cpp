// gui/src/MainWindow.cpp
#include "ads1292/gui/MainWindow.h"
#include "ads1292/gui/QCustomPlotWaveform.h"   // concrete review waveform backend
#include "ads1292/acq/SimulatorDeviceSource.h"
#include "ads1292/acq/IDeviceSource.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/view/ReviewRender.h"
#include "ads1292/dsp/Spectrum.h"

#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QDockWidget>
#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QSplitter>
#include <QTabWidget>
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

    // ── Toolbar ───────────────────────────────────────────────────────────────
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

    // ── Central tab widget ────────────────────────────────────────────────────
    tabs_ = new QTabWidget(this);
    setCentralWidget(tabs_);

    // ── Tab 0: Live ECG ───────────────────────────────────────────────────────
    {
        auto* liveWidget  = new QWidget(tabs_);
        auto* liveLayout  = new QHBoxLayout(liveWidget);
        liveLayout->setContentsMargins(0, 0, 0, 0);

        // Left side: scope (top) + event console (bottom) in vertical splitter
        auto* leftSplitter = new QSplitter(Qt::Vertical, liveWidget);
        scope_        = new LiveScope(leftSplitter);
        eventConsole_ = new EventConsole(leftSplitter);
        leftSplitter->addWidget(scope_);
        leftSplitter->addWidget(eventConsole_);
        leftSplitter->setStretchFactor(0, 4);
        leftSplitter->setStretchFactor(1, 1);

        // Right side: status panel
        statusPanel_ = new StatusPanel(liveWidget);

        // Combine via horizontal splitter to preserve P4/P5d proportions
        auto* centralSplitter = new QSplitter(Qt::Horizontal, liveWidget);
        centralSplitter->addWidget(leftSplitter);
        centralSplitter->addWidget(statusPanel_);
        centralSplitter->setStretchFactor(0, 4);
        centralSplitter->setStretchFactor(1, 1);

        liveLayout->addWidget(centralSplitter);
        tabs_->addTab(liveWidget, "Live ECG");
    }

    // ── Tab 1: Review waveform ────────────────────────────────────────────────
    {
        auto* reviewWaveformImpl = new QCustomPlotWaveform();
        reviewWaveform_.reset(reviewWaveformImpl);
        // The QCustomPlotWaveform manages its own QWidget lifetime via Qt parent.
        // We embed the widget directly into the tab (no extra container needed).
        tabs_->addTab(reviewWaveform_->widget(), "Review");
    }

    // ── Tab 2: PQRST ──────────────────────────────────────────────────────────
    {
        pqrstPanel_ = new PqrstPanel(tabs_);
        tabs_->addTab(pqrstPanel_, "PQRST");
    }

    // ── Tab 3: Spectrum ───────────────────────────────────────────────────────
    {
        spectrumPanel_ = new SpectrumPanel(tabs_);
        tabs_->addTab(spectrumPanel_, "Spectrum");
    }

    // ── Tab 4: Event Log ──────────────────────────────────────────────────────
    {
        reviewEventLogPanel_ = new ReviewEventLogPanel(tabs_);
        tabs_->addTab(reviewEventLogPanel_, "Event Log");
    }

    // ── Tab 5: Info ───────────────────────────────────────────────────────────
    {
        qualityInfoPanel_ = new QualityInfoPanel(tabs_);
        tabs_->addTab(qualityInfoPanel_, "Info");
    }

    // ── Wire toolbar actions ──────────────────────────────────────────────────
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
        activeSource_ = std::make_unique<ads1292::acq::SimulatorDeviceSource>(200, 0);
        worker_.start(activeSource_.get(), mode, "");
    });

    connect(stopBtn, &QPushButton::clicked, this, [this, startBtn, stopBtn]() {
        worker_.requestStop();
        startBtn->setEnabled(true);
        stopBtn->setEnabled(false);
    });

    // ── Tick timer (live tab only) ────────────────────────────────────────────
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

void MainWindow::loadRecordingForTest(const std::string& csvPath) {
    auto samples = ads1292::io::read_recording_csv(csvPath);
    if (samples.empty()) {
        review_loaded_ = false;
        return;
    }

    // Build the review render frame
    auto frame = ads1292::view::build_review_render_frame(
        samples,
        ads1292::dsp::EcgDisplaySettings{},
        ads1292::dsp::SoftwareFilterSettings{},
        "Auto",
        500.0,
        /*smoothing_window=*/5,
        /*max_points=*/5000,
        /*ecg_inverted=*/false,
        /*min_ecg_span_counts=*/50.0,
        /*min_resp_span_counts=*/50.0);

    // Build the spectrum analysis
    auto spec = ads1292::dsp::build_spectrum_analysis(
        samples,
        "CH2",
        500.0,
        60.0,
        48);

    // Populate the review waveform (ECG = graph 0, resp = graph 1, R-peak markers)
    reviewWaveform_->setData(0, frame.plot_ecg_x, frame.plot_ecg);
    reviewWaveform_->setMarkers(0, frame.peak_x, frame.peak_y);
    reviewWaveform_->setData(1, frame.plot_resp_x, frame.plot_resp);
    reviewWaveform_->replotNow();

    // Populate the review panels
    pqrstPanel_->showFrame(frame);
    spectrumPanel_->showSpectrum(spec);
    qualityInfoPanel_->showMetrics(frame.metrics);
    reviewEventLogPanel_->appendLine("Loaded " + csvPath);

    review_loaded_ = true;
}

} // namespace ads1292::gui
