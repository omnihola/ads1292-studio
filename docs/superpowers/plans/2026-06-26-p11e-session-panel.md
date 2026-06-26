# P11 Phase 3: Session Metadata Input Panel

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** A session-metadata input panel (Session ID, Subject, Electrode, Montage, Operator, Notes) whose values are collected at finalize and written into the recording bundle. Today the GUI writes `SessionMetadata{}` (blank defaults) — annotations from the user never reach the bundle.

**Architecture:** A new `SessionPanel : QWidget` holds 6 labeled `QLineEdit`s and exposes `ads1292::SessionMetadata metadata() const`. It's placed in the MainWindow layout (a left pane of the splitter, or a dedicated area). `buildFinalizeOptions()` sets `opt.metadata = sessionPanel_->metadata()` so the bundle records the user's session info.

**Tech Stack:** C++17, CMake, Catch2, Qt. Oracle: `ui_qt/sidebar_forms.py` (the Session tab → SessionMetadata).

## Global Constraints

- **C++17**; Qt GUI. Branch `c++`; never touch `main`. `build/` gitignored. Reconfigure after adding files.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **`ads1292::SessionMetadata`** (core/model/SessionMetadata.h): fields `session_id` (default ""), `subject_id` ("anonymous"), `electrode` (""), `montage` ("RA/LA/RL torso"), `operator_` ("" — JSON key "operator"), `notes` (""), `acquisition_mode` ("live_stream"). Has `normalized()`.
- **Panel pattern:** follow `StatusPanel` (a `QWidget` with labeled rows; gui/include/ads1292/gui/StatusPanel.h). Use a `QFormLayout` or labeled `QHBoxLayout` rows.
- **The acquisition_mode** in the bundle metadata is set from the recording mode (recordingMode_), NOT a panel field — leave it default/let finalize set it; the panel only collects the 6 user fields.

## File Structure

```
gui/include/ads1292/gui/SessionPanel.h + gui/src/SessionPanel.cpp   # NEW
gui/CMakeLists.txt                                                    # add SessionPanel.cpp
gui/src/MainWindow.cpp + .h                                           # instantiate + place + wire into buildFinalizeOptions
tests/cpp/test_gui_smoke.cpp                                          # SessionPanel.metadata() + metadata-into-bundle
```

---

### Task 1: SessionPanel widget

**Files:** Create `gui/include/ads1292/gui/SessionPanel.h` + `gui/src/SessionPanel.cpp`; add to gui CMake; extend `tests/cpp/test_gui_smoke.cpp`.

**Interfaces (namespace `ads1292::gui`):**
```cpp
class SessionPanel : public QWidget {
public:
  explicit SessionPanel(QWidget* parent = nullptr);
  ads1292::SessionMetadata metadata() const;   // reads the 6 line edits
  void setMetadata(const ads1292::SessionMetadata& m);  // populate (for load/restore)
private:
  QLineEdit* sessionId_ = nullptr; QLineEdit* subject_ = nullptr; QLineEdit* electrode_ = nullptr;
  QLineEdit* montage_ = nullptr; QLineEdit* operator_ = nullptr; QLineEdit* notes_ = nullptr;
};
```
- ctor: a `QFormLayout` (or labeled rows) with 6 `QLineEdit`s labeled "Session ID", "Subject", "Electrode", "Montage", "Operator", "Notes". Pre-fill the defaults that match SessionMetadata's defaults (subject_ = "anonymous", montage_ = "RA/LA/RL torso"; the rest empty) so an unedited panel yields the same defaults as `SessionMetadata{}`.
- `metadata()`: build a `SessionMetadata` from the line edits — `m.session_id = sessionId_->text().toStdString();` … `m.operator_ = operator_->text().toStdString();` `m.notes = notes_->text().toStdString();`. Leave `acquisition_mode` at its default. Return it (do NOT normalize here — let finalize/write normalize, matching the bundle pipeline).
- `setMetadata(m)`: set each line edit from the struct.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`, offscreen, ensureApp): construct a `SessionPanel`; `setMetadata` a known struct (session_id="S-42", subject_id="subjX", electrode="MOTAC") OR set the line edits via a test path; assert `metadata().session_id == "S-42"` etc. Also assert an unedited panel's `metadata()` matches the SessionMetadata defaults (subject_id "anonymous", montage "RA/LA/RL torso").
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** SessionPanel (6 line edits + metadata()/setMetadata()).
- [ ] **Step 4: Wire CMake, build, offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 SessionPanel (session metadata input widget)"`

---

### Task 2: integrate SessionPanel + wire into finalize

**Files:** Modify `gui/src/MainWindow.cpp` + `.h`; extend `tests/cpp/test_gui_smoke.cpp`.

- Member: `SessionPanel* sessionPanel_ = nullptr;` (include SessionPanel.h).
- Place it in the layout: add it to the MainWindow's splitter/layout as a left pane (or wrap the central `tabs_` + `sessionPanel_` in a `QSplitter`). Keep the existing tabs_ + StatusPanel placement working. (A reasonable layout: `QSplitter[ sessionPanel_ | tabs_ | statusPanel_ ]` or sessionPanel_ above/left. Pick a clean integration that doesn't break the existing review/live tabs.)
- In `buildFinalizeOptions()`: `opt.metadata = sessionPanel_->metadata();` (replace the `SessionMetadata{}`). (acquisition_mode is already handled separately via recordingMode_ → opt.acquisition_mode; leave the panel's metadata.acquisition_mode default — finalize uses opt.acquisition_mode for the provenance, and opt.metadata.acquisition_mode for the metadata section, which Python also derives — set `opt.metadata.acquisition_mode` from recordingMode_ too if it matters for parity: "raw_adc_24bit"/"live_stream".)
- Test seam: `SessionPanel* sessionPanelForTest() { return sessionPanel_; }`.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`): construct MainWindow; `mw.sessionPanelForTest()->setMetadata(<session_id="bundle-sess", electrode="MOTAC">);` then run the finalize seam (the Phase-1 `finalizeForTest` which authors a CSV + finalizes); read the produced bundle (`read_recording_bundle` → `metadata_from_bundle`) → assert `session_id == "bundle-sess"` and `electrode == "MOTAC"`. Before the wiring, `opt.metadata` was `SessionMetadata{}` → session_id empty → test fails.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the panel placement + `opt.metadata = sessionPanel_->metadata()` + the seam.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 wire SessionPanel metadata into the recording bundle"`

---

## Self-Review

**Coverage:** the input widget = Task 1; the layout integration + finalize wiring = Task 2. QualityGate/Protocol inputs are a SEPARATE later phase (Phase 5) that extends this panel into tabs. The acquisition_mode is sourced from recordingMode_ (not the panel).

**Type consistency:** `SessionPanel::metadata()` (Task 1) → `opt.metadata` in buildFinalizeOptions (Task 2); reuses `ads1292::SessionMetadata` + the Phase-1 finalize seam + the P10 read API (test).

**Risk notes:** keep the existing tabs_/StatusPanel layout working when adding sessionPanel_ (don't break the live/review tabs). Pre-fill the panel defaults to match SessionMetadata{} so an unedited panel is parity-neutral. metadata() reads the line edits on the GUI thread (buildFinalizeOptions is GUI-thread).
