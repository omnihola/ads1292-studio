# P11 Phase 6: Load CSV / H5 File Dialog

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** A "Load" toolbar button opens a file dialog, reads the selected recording (CSV or H5), populates all review panels, and switches to the Review tab. Today loading is only a test helper (`loadRecordingForTest`, CSV-only, no UI).

**Architecture:** Refactor the existing `loadRecordingForTest` body into a shared `loadRecording(path)` that handles BOTH `.csv` (read_recording_csv + sidecar-bundle events) and `.h5` (read_recording_h5 → samples + embedded bundle_json → events_from_bundle). A "Load" button triggers `QFileDialog::getOpenFileName` → `loadRecording(path)` → switch to the Review tab.

**Tech Stack:** C++17, CMake, Catch2, Qt. Oracle: `controller.py` `_on_load_csv` / `load_csv` (read → populate review → switch tab).

## Global Constraints

- **C++17**; Qt GUI + io. Branch `c++`; never touch `main`. `build/` gitignored. Reconfigure after adding files.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **Reuse:** `io/CsvIo.h read_recording_csv`; `io/H5Io.h read_recording_h5(path) -> H5Recording{ std::vector<StreamSample> samples; std::string bundle_json; ... }`; `io/RecordingBundle.h` events_from_bundle (parse a json — for H5, parse bundle_json string via nlohmann::json::parse then events_from_bundle); `recording_bundle_path`/`is_recording_bundle_path` (CSV sidecar path); the review panels (reviewWaveform_/pqrstPanel_/spectrumPanel_/qualityInfoPanel_/reviewEventLogPanel_); `tabs_` (QTabWidget). `build_review_render_frame` + `build_spectrum_analysis` (already used in loadRecordingForTest).
- **The review-panel population logic already exists** in `loadRecordingForTest` — extract it, don't rewrite it.
- **H5 guarded by `ADS1292_BUILD_HDF5`** — the .h5 branch + its test must compile-guard on HDF5 being built.

## File Structure

```
gui/include/ads1292/gui/MainWindow.h + gui/src/MainWindow.cpp   # loadRecording(path) shared + Load button + dialog + tab switch
tests/cpp/test_gui_smoke.cpp                                     # H5 load + the shared path
```

---

### Task 1: unified `loadRecording(path)` — CSV + H5

**Files:** Modify `gui/include/ads1292/gui/MainWindow.h` + `gui/src/MainWindow.cpp`; extend `tests/cpp/test_gui_smoke.cpp`.

**Interfaces:**
- `bool MainWindow::loadRecording(const std::string& path);` — returns true if loaded. Detects `.h5` (case-insensitive ext) vs CSV. Keep `loadRecordingForTest(csvPath)` as a thin wrapper calling `loadRecording(csvPath)` (so existing tests still pass).

**Implementation:**
- Refactor the body of the current `loadRecordingForTest` into `loadRecording(path)`:
  - Determine samples + events by source:
    - **`.h5`** (only if `ADS1292_BUILD_HDF5`): `auto h5 = ads1292::io::read_recording_h5(path); auto samples = h5.samples; std::vector<EventMarker> events; if (!h5.bundle_json.empty()) { auto j = nlohmann::json::parse(h5.bundle_json, nullptr, false); if (!j.is_discarded() && j.value("schema","")=="ads1292-recording-bundle-v1") events = ads1292::io::events_from_bundle(j); }`.
    - **CSV** (else): `auto samples = ads1292::io::read_recording_csv(path);` + the existing sidecar-bundle event read (`recording_bundle_path` / `is_recording_bundle_path` / `events_from_bundle`).
  - if `samples.empty()` → `review_loaded_ = false; return false;`.
  - Run the SHARED review-panel population (build_review_render_frame + build_spectrum_analysis + setData/setMarkers/showFrame/showSpectrum/showMetrics + `reviewEventLogPanel_->setEvents(events)` + `loadedEvents_ = events;` + `review_loaded_ = true;`). (Exactly the existing logic — just sourced from either reader.)
  - return true.
- `loadRecordingForTest(csvPath)` → `loadRecording(csvPath);` (thin wrapper).

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`, offscreen, guarded by HDF5): write a recording to H5 — build samples + a bundle json (via `build_recording_bundle` with 2 events) + `write_recording_h5(h5_path, samples, bundle_json_str, attrs)`; construct MainWindow; `REQUIRE(mw.loadRecording(h5_path));` + `REQUIRE(mw.reviewEventCountForTest() == 2)` (events came from the H5's embedded bundle) + `REQUIRE(mw.reviewLoadedForTest())` (add the accessor if missing). Also confirm the existing CSV `loadRecordingForTest` path still works (it now routes through loadRecording).
- [ ] **Step 2: Run, verify fail** (loadRecording / the H5 branch don't exist yet).
- [ ] **Step 3: Implement** `loadRecording(path)` (extract + add the H5 branch) + the wrapper + any test accessor (`reviewLoadedForTest`).
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 unified loadRecording (CSV + H5)"`

---

### Task 2: Load toolbar button + file dialog + tab switch

**Files:** Modify `gui/src/MainWindow.cpp` (+ .h); extend `tests/cpp/test_gui_smoke.cpp`.

**Implementation:**
- In the ctor toolbar build: add a `QPushButton* loadBtn = new QPushButton("Load", toolbar); toolbar->addWidget(loadBtn);` (store as `loadBtn_` member if useful).
- Connect `loadBtn->clicked`: a lambda that calls `QString f = QFileDialog::getOpenFileName(this, "Open recording", QString(), "Recordings (*.h5 *.csv);;All files (*)"); if (f.isEmpty()) return; if (loadRecording(f.toStdString())) { tabs_->setCurrentWidget(reviewWaveform_->widget()); /* or the Review tab index */ }` (switch to the Review tab on success; on failure, optionally log). Include `<QFileDialog>` + `<QPushButton>`.
- Add a test seam `void MainWindow::loadAndShowReview(const std::string& path)` that does `if (loadRecording(path)) tabs_->setCurrentWidget(<review tab widget>);` — so the test can exercise the load→tab-switch WITHOUT the modal QFileDialog (which can't be driven offscreen). The button's clicked lambda calls the dialog then this same seam.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`): construct MainWindow; assert a "Load" button exists (findChild<QPushButton*> with text "Load", or a `loadButtonPresentForTest()` accessor). Build a CSV (or H5) recording; `mw.loadAndShowReview(path);` → assert `mw.reviewLoadedForTest()` true AND the current tab is the Review tab (`tabs_->currentWidget() == reviewWaveform_->widget()` via a `currentTabIsReviewForTest()` accessor). Before the change there's no Load button / no tab-switch seam → test fails.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the Load button + dialog + `loadAndShowReview` seam + the tab-switch + the test accessors.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 Load button + file dialog + switch to Review tab"`

---

## Self-Review

**Coverage:** unified load (CSV+H5) = Task 1; the UI button + dialog + tab-switch = Task 2. The QFileDialog itself (modal) is exercised by the button wiring but tested via the non-modal `loadAndShowReview` seam (offscreen can't drive a modal dialog). loadRecordingForTest stays as a wrapper (existing tests unaffected).

**Type consistency:** `loadRecording(path)` (Task 1) called by `loadAndShowReview` + the button lambda (Task 2). H5 events come from parsing `H5Recording::bundle_json` → `events_from_bundle`; CSV events from the sidecar bundle. Both feed the shared population.

**Risk notes:** the H5 branch + its test are `ADS1292_BUILD_HDF5`-guarded. The modal QFileDialog is NOT driven in tests (use the seam). loadRecording must keep the existing CSV behavior byte-for-byte (it's the same code, just extracted). Switch to the Review tab only on successful load.
