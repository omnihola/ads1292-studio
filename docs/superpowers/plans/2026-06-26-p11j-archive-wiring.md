# P11 Phase 10: Wire ReportExport + Archive Actions

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Wire the existing (but unwired) `export_review_report` into an "Export Report" toolbar button, and add a "Session Index" archive action — both operating on a loaded recording / a chosen directory. The io/gui functions all exist; this phase connects them to the UI.

**Architecture:** `loadRecording` already builds the review from a recording's samples but discards them; store them in `loadedSamples_` + the loaded metadata. "Export Report" → a directory dialog → `export_review_report(loadedSamples_, outDir, title, sr, source, metadata, events, calibration)` (produces HTML + 3 PNGs). "Session Index" → a directory dialog → `scan_recording_directory(dir)` + `write_session_index_json(dir/index.json, rows, summary)`. The modal dialogs are exercised via testable seams (offscreen can't drive a modal).

**Tech Stack:** C++17, CMake, Catch2, Qt. Oracle: `controller.py` (export report / session index actions).

## Global Constraints

- **C++17**; Qt GUI + io. Branch `c++`; never touch `main`. `build/` gitignored. Reconfigure after adding files.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **Reuse:** `gui/ReportExport.h` `export_review_report(samples, out_dir, title, sample_rate_hz, source, metadata, events, calibration) -> ReportExportResult{html_path, ecg_png_path, pqrst_png_path, spectrum_png_path}` (READ the exact signature). `io/SessionIndexScan.h` `scan_recording_directory(root)` + `summarize_rows(rows)` + `write_session_index_json(path, rows, summary)` (READ the exact signatures). `loadRecording` (Phase 6) has the samples locally.
- **Modal dialogs are NOT driven in tests** — use seams (the Load dialog precedent from Phase 6).

## File Structure

```
gui/src/MainWindow.cpp + .h   # loadedSamples_/loadedMetadata_ members; Export Report button + seam; Session Index button + seam
tests/cpp/test_gui_smoke.cpp  # exportReportForTest produces HTML+PNGs; sessionIndexForTest produces index.json
```

---

### Task 1: Export Report button

**Files:** Modify `gui/src/MainWindow.cpp` + `.h`; extend `tests/cpp/test_gui_smoke.cpp`.

- **Members**: `std::vector<ads1292::StreamSample> loadedSamples_;` `ads1292::SessionMetadata loadedMetadata_;` (the loaded recording's data — Phase 6 `loadRecording` currently discards the samples; store them).
- In `loadRecording(path)`: after reading samples, `loadedSamples_ = samples;` (store a copy before `std::move` if needed — reorder so the samples are stored). If the recording has a bundle, also read its metadata via `metadata_from_bundle` (CSV: `read_metadata_json` of the sidecar if present, else default) → `loadedMetadata_`. (Best-effort; default SessionMetadata{} if none.)
- **Export Report button**: add `QPushButton* exportReportBtn_ = nullptr;` "Export Report" to the toolbar. Clicked → if `!review_loaded_ || loadedSamples_.empty()` → log "load a recording first" + return; else `QString dir = QFileDialog::getExistingDirectory(this, "Export report to folder"); if (dir.isEmpty()) return; exportReportTo(dir.toStdString());`.
- **Seam `ReportExportResult exportReportTo(const std::string& outDir)`** (so the test bypasses the modal dialog): `return ads1292::gui::export_review_report(loadedSamples_, outDir, "ADS1292 Studio Review", 500.0, "Auto", loadedMetadata_, loadedEvents_, ads1292::Calibration{});` (match the export_review_report signature). The button's clicked lambda calls the dialog then this seam.
- **refreshControls**: gate `exportReportBtn_` enabled when `review_loaded_` (a recording is loaded) — i.e. `if (exportReportBtn_) exportReportBtn_->setEnabled(review_loaded_ && !streaming_);`.
- **Test accessor**: `bool exportReportButtonPresentForTest() const { return exportReportBtn_ != nullptr; }`.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`, offscreen, ensureApp): construct MainWindow; assert `exportReportButtonPresentForTest()`. Author a recording CSV (+ optionally a bundle); `mw.loadRecording(csvPath);` then `auto r = mw.exportReportTo(outDir);` → `REQUIRE(std::filesystem::exists(r.html_path)); REQUIRE(std::filesystem::exists(r.ecg_png_path));` (the report's HTML + ECG PNG were produced from the loaded recording). (export_review_report is GPL-isolated + offscreen-capable from P7c.)
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the members + store samples/metadata in loadRecording + the button + exportReportTo seam + refreshControls gating + the accessor.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 Export Report button (HTML + PNGs from the loaded recording)"`

---

### Task 2: Session Index action

**Files:** Modify `gui/src/MainWindow.cpp` + `.h`; extend `tests/cpp/test_gui_smoke.cpp`.

- **Session Index button**: add `QPushButton* sessionIndexBtn_ = nullptr;` "Session Index" to the toolbar. Clicked → `QString dir = QFileDialog::getExistingDirectory(this, "Scan recordings directory"); if (dir.isEmpty()) return; sessionIndexFor(dir.toStdString());`.
- **Seam `std::string sessionIndexFor(const std::string& dir)`** (returns the index.json path): `auto rows = ads1292::io::scan_recording_directory(dir); auto summary = ads1292::io::summarize_rows(rows); auto out = (std::filesystem::path(dir) / "index.json").string(); ads1292::io::write_session_index_json(out, rows, summary); return out;` (match the exact signatures of scan_recording_directory / summarize_rows / write_session_index_json — READ SessionIndexScan.h). Log the path + the row count.
- **Test accessor**: `bool sessionIndexButtonPresentForTest() const { return sessionIndexBtn_ != nullptr; }`.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`): construct MainWindow; assert `sessionIndexButtonPresentForTest()`. Build a temp dir with a recording (rec.csv + optionally a bundle); `auto idx = mw.sessionIndexFor(dirPath);` → `REQUIRE(std::filesystem::exists(idx));` (index.json written) + parse it (nlohmann) → it has a `rows`/`recordings` array (READ what write_session_index_json emits) with the recording. (Reuse the existing SessionIndexScan test pattern for the dir setup.)
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the button + sessionIndexFor seam + the accessor.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 Session Index action (scan directory + write index.json)"`

---

## Self-Review

**Coverage:** Export Report (Task 1) + Session Index (Task 2). The Batch action + other archive exports (Export Package etc.) are deferred (the core report + index are the high-value ones; Batch can be a follow-up). The modal QFileDialogs are tested via the seams (exportReportTo / sessionIndexFor), per the Phase-6 precedent.

**Type consistency:** `loadedSamples_`/`loadedMetadata_`/`loadedEvents_` (from loadRecording) → `exportReportTo` → `export_review_report` (Task 1); `sessionIndexFor` → scan/summarize/write (Task 2). Reuses the existing export + index io/gui functions.

**Risk notes:** store the loaded samples (loadRecording currently discards them — reorder so loadedSamples_ is set before any std::move). The modal dialogs are NOT driven offscreen — use the seams. export_review_report is GPL-isolated + offscreen-capable (P7c). Match the exact signatures of export_review_report / scan_recording_directory / summarize_rows / write_session_index_json (read the headers). Gate the buttons (review_loaded_ for Export Report).
