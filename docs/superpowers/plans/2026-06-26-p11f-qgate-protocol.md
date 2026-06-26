# P11 Phase 5: QualityGate + Protocol Input Tabs

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Extend the SessionPanel into a tabbed widget — Session / Validation (QualityGate thresholds) / Protocol (TestProtocol fields) — and write the user-entered quality gate + protocol into the recording bundle on finalize. Today `opt.quality_gate`/`opt.protocol` use the templates (defaults); the user can't set thresholds or protocol text.

**Architecture:** Convert `SessionPanel` into a `QTabWidget` host: the existing 6 metadata fields move to a "Session" tab; a "Validation" tab holds the 6 QualityGate numeric/bool fields + 3 optional artifact caps; a "Protocol" tab holds the 4 TestProtocol text fields. Add `qualityGate()` + `protocol()` accessors. `buildFinalizeOptions()` sets `opt.quality_gate = sessionPanel_->qualityGate(); opt.protocol = sessionPanel_->protocol();`.

**Tech Stack:** C++17, CMake, Catch2, Qt. Oracle: `ui_qt/sidebar_forms.py` (Validation + Protocol tabs).

## Global Constraints

- **C++17**; Qt GUI. Branch `c++`; never touch `main`. `build/` gitignored. Reconfigure after adding files.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **`ads1292::dsp::QualityGate`**: `double min_duration_seconds=8.0; double min_contact_ok_percent=95.0; int min_r_peaks=5; double min_hr_bpm=35.0; double max_hr_bpm=180.0; bool require_qrs_clear=true; std::optional<double> max_baseline_drift_counts, max_noise_rms_counts, max_peak_to_peak_counts;`.
- **`ads1292::TestProtocol`**: `std::string name="ADS1292 validation protocol"; std::string objective=""; std::string operator_instructions="Follow the listed protocol steps."; std::vector<ProtocolStep> steps; std::string acceptance_notes="Review quality gate and artifacts before accepting the run.";` (steps NOT user-input here — leave empty).
- **Parity-neutral defaults:** pre-fill every field with the struct default so an unedited panel yields `QualityGate{}` / `TestProtocol{}` (with empty steps). The 3 optional caps: empty field → `std::nullopt` (unchecked).
- Keep `metadata()`/`setMetadata()` (Phase 3) working — the Session tab still drives them.

## File Structure

```
gui/include/ads1292/gui/SessionPanel.h + gui/src/SessionPanel.cpp   # MODIFY: QTabWidget + Validation/Protocol tabs + qualityGate()/protocol()
gui/src/MainWindow.cpp                                               # wire opt.quality_gate + opt.protocol
tests/cpp/test_gui_smoke.cpp                                         # qualityGate()/protocol() + into-bundle
```

---

### Task 1: SessionPanel → tabbed (Session / Validation / Protocol)

**Files:** Modify `gui/include/ads1292/gui/SessionPanel.h` + `gui/src/SessionPanel.cpp`; extend `tests/cpp/test_gui_smoke.cpp`.

**Interfaces (add to SessionPanel):**
- `ads1292::dsp::QualityGate qualityGate() const;`
- `ads1292::TestProtocol protocol() const;`
- (keep `metadata()`/`setMetadata()`.)

**Implementation:**
- Restructure the ctor: create a `QTabWidget* tabs = new QTabWidget(this);` as the panel's single child (a QVBoxLayout on `this` holding `tabs`). 
  - **Session tab**: a QWidget with the existing 6-field QFormLayout (Session ID/Subject/Electrode/Montage/Operator/Notes). `metadata()`/`setMetadata()` unchanged (still read/write these 6 line edits).
  - **Validation tab**: a QWidget with a QFormLayout: 5 `QLineEdit` (or QDoubleSpinBox/QSpinBox) for min_duration_seconds, min_contact_ok_percent, min_r_peaks, min_hr_bpm, max_hr_bpm; 1 `QCheckBox` "Require QRS clear" (checked by default); 3 `QLineEdit` for the optional caps (max baseline drift / noise rms / peak-to-peak) — EMPTY by default (empty → nullopt). Pre-fill the 5 numerics + checkbox with QualityGate{} defaults (8.0/95.0/5/35.0/180.0/true).
  - **Protocol tab**: a QWidget with a QFormLayout: 4 `QLineEdit` for name/objective/operator_instructions/acceptance_notes. Pre-fill with TestProtocol{} defaults (name "ADS1292 validation protocol", operator_instructions "Follow the listed protocol steps.", acceptance_notes "Review quality gate and artifacts before accepting the run.", objective empty).
  - Store the new widgets as members.
- **`qualityGate() const`:** build a `QualityGate g;` from the fields: parse the 5 numerics via `text().toDouble()`/`toInt()` (on parse failure, keep the struct default — use `bool ok; double v = field->text().toDouble(&ok); if (ok) g.x = v;`); `g.require_qrs_clear = qrsCheck_->isChecked();`. For each of the 3 optional caps: `if (!capField->text().trimmed().isEmpty()) { bool ok; double v = capField->text().toDouble(&ok); if (ok) g.max_... = v; }` (empty/invalid → leave nullopt). Return g.
- **`protocol() const`:** `TestProtocol p; p.name = nameField->text().toStdString(); p.objective = ...; p.operator_instructions = ...; p.acceptance_notes = ...; p.steps = {};` return p (leave steps empty; do NOT normalize).
- Include `<QTabWidget>`, `<QCheckBox>`, `ads1292/dsp/QualityGate.h`, `ads1292/model/TestProtocol.h`.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`, offscreen): construct a SessionPanel; assert `qualityGate()` returns the defaults (min_duration_seconds == 8.0, require_qrs_clear == true, max_noise_rms_counts == nullopt) AND `protocol()` returns the defaults (name == "ADS1292 validation protocol"). Then (if a setter or direct widget access is exposed for the test — add minimal test seams like `setQualityGateMinDurationForTest(double)` OR expose the line edits) verify a changed value flows through: e.g. a seam `qualityGateForTest()`/`protocolForTest()` returning the accessors after a programmatic field change. At minimum assert the DEFAULTS are correct (parity-neutral) + that `metadata()` (Phase 3) still works after the tab restructure.
- [ ] **Step 2: Run, verify fail** (qualityGate()/protocol() don't exist).
- [ ] **Step 3: Implement** the QTabWidget restructure + the Validation/Protocol tabs + qualityGate()/protocol() (+ any small test seams).
- [ ] **Step 4: Build + offscreen ctest** (the Phase-3 metadata tests must still pass — metadata()/setMetadata() unchanged).
- [ ] **Step 5: Commit** `git commit -m "feat: P11 SessionPanel Validation + Protocol tabs (qualityGate/protocol input)"`

---

### Task 2: wire qualityGate + protocol into finalize

**Files:** Modify `gui/src/MainWindow.cpp`; extend `tests/cpp/test_gui_smoke.cpp`.

- In `buildFinalizeOptions()`: set `opt.quality_gate = sessionPanel_->qualityGate(); opt.protocol = sessionPanel_->protocol();` (replace the `quality_gate_template()`/`protocol_template()` calls). (An unedited panel yields the same defaults as the templates → parity-neutral.)

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`): construct MainWindow; via a SessionPanel test seam, set a distinctive protocol name (e.g. "MOTAC protocol") + a non-default quality-gate value (e.g. min_duration_seconds via a seam); run the finalize seam (`finalizeForTest`); read the bundle → `protocol_from_bundle(read_recording_bundle(path)).name == "MOTAC protocol"` (and the quality_gate value if a seam set it). Before the wiring, opt.protocol was the template → name was the default → test fails. (If setting individual qgate/protocol fields via seams is awkward, at minimum assert that the bundle's protocol/quality_gate now come from `sessionPanel_->protocol()`/`qualityGate()` by setting the protocol name via `protocolForTest`/a setter and round-tripping it.)
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the wiring + any needed seam.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 wire SessionPanel quality gate + protocol into the bundle"`

---

## Self-Review

**Coverage:** the Validation + Protocol input tabs = Task 1; the finalize wiring = Task 2. Steps are NOT user-input (left empty — matching the simple-form scope; protocol steps editing is out of scope). Parity-neutral defaults keep an unedited panel == the templates.

**Type consistency:** `qualityGate()` (QualityGate) + `protocol()` (TestProtocol) (Task 1) → `opt.quality_gate`/`opt.protocol` (Task 2); reuse the Phase-3 SessionPanel + the Phase-1 finalize seam + P10 `protocol_from_bundle`/`quality_gate_from_bundle` (test).

**Risk notes:** keep `metadata()`/`setMetadata()` working after the tab restructure (the Phase-3 tests guard this). Parse numerics defensively (parse-fail → keep default). Empty optional-cap field → nullopt. Parity-neutral defaults so an unedited panel matches the templates (no regression for the existing finalize tests).
