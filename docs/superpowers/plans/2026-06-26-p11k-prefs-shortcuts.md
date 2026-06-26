# P11 Phase 12: Preferences Persistence + Keyboard Shortcuts (FINAL phase)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Persist the user's toolbar choices (save formats, port, mode, window) across sessions via QSettings, and add keyboard shortcuts (Space = Start/Stop toggle, Ctrl+R = refresh ports). The LAST phase of the Part-4 GUI-parity build-out.

**Architecture:** A pure-data `Preferences` struct (+ to_map/from_map, testable) mirrors the Python dataclass. MainWindow saves Preferences to QSettings on close and restores them in the ctor (applying to the save checkboxes + port/mode/window combos). QShortcuts wire Space → Start/Stop, Ctrl+R → refresh.

**Tech Stack:** C++17, CMake, Catch2, Qt. Oracle: `ui_qt/preferences.py` (the Preferences dataclass) + `main_window.py` (QSettings storage + shortcuts).

## Global Constraints

- **C++17**; the Preferences struct is core/gui-data (no Qt for the struct); QSettings/QShortcut are gui. Branch `c++`; never touch `main`. `build/` gitignored.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **`Preferences` (preferences.py)**: `std::string port=""; std::string mode="Live Monitor"; bool save_csv=true; bool save_h5=true; bool save_xlsx=false; std::string window="8 s"; std::string gain="1x"; std::string speed="25 mm/s";` + `to_map()` (string→string, bools as "true"/"false") + `from_map(map)` (defaults for missing keys; bool parse).
- **The C++ widgets to bind**: `saveH5Check_`, `saveXlsxCheck_` (saveCsvCheck_ is always-on informational), `portCombo_`, the mode combo, the window combo. (Read MainWindow.cpp for their exact members/locals — the mode/window combos may be locals; promote them to members if QSettings restore needs them.)

## File Structure

```
gui/include/ads1292/gui/Preferences.h + gui/src/Preferences.cpp   # NEW: struct + to_map/from_map
gui/src/MainWindow.cpp + .h                                        # QSettings save/restore + QShortcuts
tests/cpp/test_preferences.cpp                                     # NEW: round-trip
tests/cpp/test_gui_smoke.cpp                                       # QSettings seam + shortcuts present
```

---

### Task 1: Preferences struct + serialization

**Files:** Create `gui/include/ads1292/gui/Preferences.h` + `gui/src/Preferences.cpp`; gui CMake; Create `tests/cpp/test_preferences.cpp`; tests CMake.

**Interfaces (namespace `ads1292::gui`):**
```cpp
struct Preferences {
  std::string port = "";
  std::string mode = "Live Monitor";
  bool save_csv = true;
  bool save_h5 = true;
  bool save_xlsx = false;
  std::string window = "8 s";
  std::string gain = "1x";
  std::string speed = "25 mm/s";
  std::map<std::string, std::string> to_map() const;             // bools as "true"/"false"
  static Preferences from_map(const std::map<std::string, std::string>& m);  // defaults for missing; bool parse
};
```
- `to_map()`: every field → string (bools → "true"/"false").
- `from_map(m)`: start from defaults; for each key present in `m`, set the field (bool fields parsed via "true"/"1"/"yes" → true, case-insensitive; else use the string). Missing keys keep the default. (Mirror preferences.py from_dict + _to_bool.)

- [ ] **Step 1: Write the failing test** (`tests/cpp/test_preferences.cpp`):
  - Defaults: `Preferences p;` → `p.mode=="Live Monitor"`, `p.save_h5==true`, `p.save_xlsx==false`, `p.window=="8 s"`.
  - Round-trip: `Preferences a; a.port="/dev/cu.x"; a.save_xlsx=true; a.window="4 s"; auto m = a.to_map(); auto b = Preferences::from_map(m);` → `b.port=="/dev/cu.x"; b.save_xlsx==true; b.window=="4 s"; b.save_h5==true`.
  - from_map with missing keys → defaults: `from_map({{"port","/dev/y"}})` → port "/dev/y" but mode=="Live Monitor", save_h5==true (defaults).
  - bool parse: `from_map({{"save_xlsx","true"}}).save_xlsx==true`; `from_map({{"save_h5","false"}}).save_h5==false`.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the struct + to_map/from_map.
- [ ] **Step 4: Wire CMake, build, ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 Preferences struct + serialization"`

---

### Task 2: QSettings persistence + keyboard shortcuts

**Files:** Modify `gui/src/MainWindow.cpp` + `.h`; extend `tests/cpp/test_gui_smoke.cpp`.

- **Promote** the mode/window combos to members if not already (`modeCombo_`, `winCombo_`) so restore can set them.
- **`Preferences MainWindow::currentPreferences() const`** (seam): read the current widget states into a Preferences (port from `portCombo_->currentData()`/currentText, mode from `modeCombo_->currentText`, save_h5/save_xlsx from the checkboxes, window from `winCombo_->currentText`). 
- **`void MainWindow::applyPreferences(const Preferences& p)`** (seam): set the widgets from `p` (saveH5Check_->setChecked(p.save_h5); saveXlsxCheck_->setChecked(p.save_xlsx); select the matching mode/window combo items; select the port if present in the combo).
- **QSettings**: in `~MainWindow()` or a `closeEvent` override: `QSettings s("ADS1292Studio", "ads1292-studio"); auto m = currentPreferences().to_map(); for (auto& [k,v] : m) s.setValue(QString::fromStdString(k), QString::fromStdString(v));`. In the ctor (AFTER the widgets are built): `QSettings s(...); std::map<std::string,std::string> m; for (const auto& key : s.allKeys()) m[key.toStdString()] = s.value(key).toString().toStdString(); if (!m.empty()) applyPreferences(Preferences::from_map(m));`. (Guard: don't apply if no saved settings.)
  - For testability, factor the save/restore through `currentPreferences()`/`applyPreferences()` (the seams) so a test can round-trip WITHOUT touching the global QSettings store: `applyPreferences(p)` then `currentPreferences()` == p.
- **Keyboard shortcuts** (ctor): `new QShortcut(QKeySequence(Qt::Key_Space), this, [this]{ /* toggle: if streaming_ click Stop else click Start */ if (streaming_) stopBtn_->click(); else if (startBtn_->isEnabled()) startBtn_->click(); });` and `new QShortcut(QKeySequence("Ctrl+R"), this, [this]{ refreshPorts(); });`. (Include `<QShortcut>`.) A `bool spaceShortcutPresentForTest()` / count accessor if useful.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`, offscreen):
  - Prefs seam round-trip: `MainWindow mw; Preferences p; p.save_h5=false; p.save_xlsx=true; p.window="4 s"; mw.applyPreferences(p); auto got = mw.currentPreferences();` → `REQUIRE(got.save_h5==false); REQUIRE(got.save_xlsx==true); REQUIRE(got.window=="4 s");` (the widgets reflect + read back the prefs).
  - Shortcuts present: assert the Space + Ctrl+R QShortcuts exist (`findChildren<QShortcut*>().size() >= 2`, or accessors).
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** currentPreferences/applyPreferences + the QSettings save (close) + restore (ctor) + the QShortcuts.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 QSettings preferences persistence + keyboard shortcuts"`

---

## Self-Review

**Coverage:** Preferences struct + serialization (Task 1, testable) + QSettings persistence + shortcuts (Task 2). The gain/speed prefs are stored but the C++ may not have those exact combos — store them as pass-through (saved/restored if the widgets exist; ignored otherwise). The QSettings global store is NOT touched by the test (the currentPreferences/applyPreferences seams round-trip the widget state directly).

**Type consistency:** `Preferences` (Task 1) ↔ `currentPreferences()`/`applyPreferences()` (Task 2) ↔ the toolbar widgets. The QShortcuts trigger the existing Start/Stop/refresh.

**Risk notes:** the QSettings restore in the ctor must run AFTER the widgets are built. Don't apply if no saved settings (first run → defaults). The mode/window combos may be locals — promote to members for restore. The test round-trips via the seams (not the global QSettings) to stay isolated/deterministic. Space toggle: respect the gating (only click Start if enabled). This is the FINAL phase — after it, the whole Part-4 build-out is complete.
