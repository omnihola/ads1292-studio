// gui/src/MainWindow.cpp
#include "ads1292/gui/MainWindow.h"
#include "ads1292/gui/QCustomPlotWaveform.h"   // concrete review waveform backend
#include "ads1292/gui/RecordingPaths.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include "ads1292/acq/IDeviceSource.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/LiveRecordingFinalize.h"
#include "ads1292/io/ProtocolIo.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/io/RecordingBundle.h"
#ifdef ADS1292_HAVE_HDF5
#include "ads1292/io/H5Io.h"
#include <nlohmann/json.hpp>
#endif
#include "ads1292/view/ReviewRender.h"
#include "ads1292/dsp/Spectrum.h"
#include "ads1292/model/SessionMetadata.h"
#include "ads1292/model/Calibration.h"

#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QDockWidget>
#include <QFileDialog>
#include <QHBoxLayout>
#include <QLabel>
#include <QMetaObject>
#include <QPushButton>
#include <QSplitter>
#include <QTabWidget>
#include <QToolBar>
#include <QVBoxLayout>
#include <QWidget>
#include <QFile>
#include <QString>

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <thread>

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

    // Save-format checkboxes
    toolbar->addSeparator();
    toolbar->addWidget(new QLabel("Save:", toolbar));

    saveCsvCheck_ = new QCheckBox("CSV", toolbar);
    saveCsvCheck_->setChecked(true);
    saveCsvCheck_->setEnabled(false);   // CSV is always written; informational only
    saveCsvCheck_->setToolTip("CSV is always written by the acquisition engine");
    toolbar->addWidget(saveCsvCheck_);

    saveH5Check_ = new QCheckBox("HDF5", toolbar);
    saveH5Check_->setChecked(true);
    saveH5Check_->setToolTip("Write HDF5 bundle alongside the CSV on Stop");
    toolbar->addWidget(saveH5Check_);

    // Load button: opens a file dialog and loads the selected recording
    toolbar->addSeparator();
    loadBtn_ = new QPushButton("Load", toolbar);
    loadBtn_->setToolTip("Open a recording file (CSV or H5) and switch to the Review tab");
    toolbar->addWidget(loadBtn_);

    connect(loadBtn_, &QPushButton::clicked, this, [this]() {
        QString f = QFileDialog::getOpenFileName(
            this,
            "Open recording",
            QString(),
            "Recordings (*.h5 *.csv);;All files (*)");
        if (f.isEmpty()) return;
        loadAndShowReview(f.toStdString());
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

    connect(startBtn, &QPushButton::clicked, this,
            [this, startBtn, stopBtn, modeCombo]() {
        startBtn->setEnabled(false);
        stopBtn->setEnabled(true);

        auto mode = (modeCombo->currentIndex() == 0)
                    ? ads1292::acq::AcquisitionMode::Live
                    : ads1292::acq::AcquisitionMode::Raw;
        const std::string modeStr =
            (mode == ads1292::acq::AcquisitionMode::Live) ? "live" : "raw";

        // Store the recording mode for use in onWorkerFinished/buildFinalizeOptions.
        recordingMode_ = modeStr;

        // Generate a timestamped CSV path and create its parent directory.
        recordingCsvPath_ = ads1292::gui::timestamped_recording_csv_path(
            modeStr, recordingsDir_);
        std::filesystem::create_directories(
            std::filesystem::path(recordingCsvPath_).parent_path());

        // Capture ISO-8601 start time for provenance.
        recordingStartedAt_ = ads1292::gui::current_iso8601_string();

        // Clear the event log so each recording starts with a fresh annotation slate.
        eventConsole_->clear();

        activeSource_ = std::make_unique<ads1292::acq::SimulatorDeviceSource>(200, 0);
        worker_.start(activeSource_.get(), mode, recordingCsvPath_);

        state_.recordingState = "recording";
        statusPanel_->updateFromState(state_);

        // Disable save-format checkboxes while recording is in progress
        // so the user cannot toggle them mid-acquisition.
        if (saveH5Check_) saveH5Check_->setEnabled(false);
    });

    connect(stopBtn, &QPushButton::clicked, this, [this, startBtn, stopBtn]() {
        worker_.requestStop();
        startBtn->setEnabled(true);
        stopBtn->setEnabled(false);
    });

    // ── Worker finished → onWorkerFinished (GUI thread, queued) ──────────────
    connect(&worker_, &ads1292::qt::AcquisitionWorker::finished,
            this, &MainWindow::onWorkerFinished, Qt::QueuedConnection);

    // ── finalizeLogged signal → append to event log + reset state ─────────────
    connect(this, &MainWindow::finalizeLogged, this, [this](QString l) {
        reviewEventLogPanel_->appendLine(l.toStdString());
        statusPanel_->updateFromState(state_);
        // Re-enable save-format checkboxes now that we are idle.
        if (saveH5Check_) saveH5Check_->setEnabled(true);
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

MainWindow::~MainWindow() {
    // Join finalize thread (if any) before QObject base is torn down.
    // This prevents the in-flight finalize thread from calling QMetaObject::invokeMethod
    // on a destroyed object (UAF fix).
    if (finalizeThread_.joinable()) {
        finalizeThread_.join();
    }
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

// ── Recording persistence ─────────────────────────────────────────────────────

ads1292::io::FinalizeOptions MainWindow::buildFinalizeOptions() const {
    ads1292::io::FinalizeOptions opt;
    opt.metadata        = ads1292::SessionMetadata{};
    // Snapshot the current event log on the GUI thread (safe: called from
    // onWorkerFinished / finalizeForTest — both on the GUI thread).
    opt.events          = eventConsole_->log().events();
    opt.calibration     = ads1292::Calibration{};
    opt.protocol        = ads1292::io::protocol_template();
    opt.quality_gate    = ads1292::io::quality_gate_template();
    opt.started_at      = recordingStartedAt_;
    opt.sample_rate_hz  = 500.0;
    // Set acquisition_mode based on the actual mode at Start time.
    opt.acquisition_mode = (recordingMode_ == "raw") ? "raw_adc_24bit" : "live_stream";
    // Task 3 will wire saveH5Check_; for now nullptr → write_h5 = true.
    opt.write_h5        = (saveH5Check_ ? saveH5Check_->isChecked() : true);
    return opt;
}

void MainWindow::onWorkerFinished(int sampleCount) {
    // Runs on the GUI thread via QueuedConnection.

    if (sampleCount <= 0) {
        reviewEventLogPanel_->appendLine("empty capture — nothing saved");
        state_.recordingState = "idle";
        statusPanel_->updateFromState(state_);
        // Re-enable save-format checkboxes: nothing was recorded, back to idle.
        if (saveH5Check_) saveH5Check_->setEnabled(true);
        return;
    }

    // Join any previously-spawned finalize thread before starting a new one.
    // This guards against double-fire of finished(int) and ensures orderly cleanup.
    if (finalizeThread_.joinable()) {
        finalizeThread_.join();
    }

    // Snapshot all finalize inputs on the GUI thread before spawning the thread.
    const ads1292::io::FinalizeOptions opt = buildFinalizeOptions();
    const std::string csv = recordingCsvPath_;

    state_.recordingState = "finalizing";
    statusPanel_->updateFromState(state_);

    // Spawn background thread: only calls the Qt-free io function.
    // Results are posted back to the GUI thread via invokeMethod (QueuedConnection).
    // Captures csv + opt by value; this by pointer (QObject lifetime handled by storing
    // the thread and joining in the destructor before QObject base is torn down).
    finalizeThread_ = std::thread([this, csv, opt]() {
        auto r = ads1292::io::finalize_live_recording(csv, opt);
        QString line = r.wrote
            ? QString("Saved: %1").arg(QString::fromStdString(r.bundle_path))
            : QString("empty capture — nothing saved");
        QMetaObject::invokeMethod(this, [this, line]() {
            // Runs on GUI thread — safe to update state and emit signal.
            state_.recordingState = "idle";
            emit finalizeLogged(line);
        }, Qt::QueuedConnection);
    });
}

ads1292::io::FinalizeResult MainWindow::finalizeForTest() {
    // Synchronous test seam: builds the same options as onWorkerFinished and
    // calls finalize_live_recording directly, avoiding event-loop + thread timing.
    return ads1292::io::finalize_live_recording(recordingCsvPath_,
                                                 buildFinalizeOptions());
}

// ── Test hooks (unchanged) ────────────────────────────────────────────────────

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

bool MainWindow::loadRecording(const std::string& path) {
    // Detect file format by extension (case-insensitive)
    std::string ext = std::filesystem::path(path).extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });

    std::vector<ads1292::StreamSample> samples;
    std::vector<ads1292::EventMarker>  events;

#ifdef ADS1292_HAVE_HDF5
    if (ext == ".h5") {
        auto h5 = ads1292::io::read_recording_h5(path);
        samples = std::move(h5.samples);
        if (!h5.bundle_json.empty()) {
            auto j = nlohmann::json::parse(h5.bundle_json, nullptr, /*allow_exceptions=*/false);
            if (!j.is_discarded() &&
                j.value("schema", std::string()) == "ads1292-recording-bundle-v1") {
                events = ads1292::io::events_from_bundle(j);
            }
        }
    } else {
#endif
        // CSV branch: read samples + sidecar bundle events
        samples = ads1292::io::read_recording_csv(path);
        auto bp = ads1292::io::recording_bundle_path(path);
        if (ads1292::io::is_recording_bundle_path(bp)) {
            events = ads1292::io::events_from_bundle(ads1292::io::read_recording_bundle(bp));
        }
#ifdef ADS1292_HAVE_HDF5
    }
#endif

    if (samples.empty()) {
        review_loaded_ = false;
        return false;
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
    reviewEventLogPanel_->setEvents(events);
    loadedEvents_ = events;

    review_loaded_ = true;
    return true;
}

void MainWindow::loadRecordingForTest(const std::string& csvPath) {
    loadRecording(csvPath);
}

void MainWindow::loadAndShowReview(const std::string& path) {
    // Testable seam: called by the Load button lambda after the dialog returns
    // a path, and directly by tests (bypassing the modal QFileDialog).
    // Switches to the Review tab only on successful load.
    if (loadRecording(path)) {
        tabs_->setCurrentWidget(reviewWaveform_->widget());
    }
}

} // namespace ads1292::gui
