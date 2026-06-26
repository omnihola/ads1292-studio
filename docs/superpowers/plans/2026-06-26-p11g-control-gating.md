# P11 Phase 7: GuiState Control Gating

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Enable/disable the toolbar controls based on the current state so the user can't trigger invalid actions (Start while streaming, Connect while streaming, change save formats mid-recording, etc.). Today the buttons are local variables with ad-hoc Start/Stop swaps; there's no coherent gating.

**Architecture:** Promote the toolbar buttons to members; add a `streaming_` bool; add a single `refreshControls()` that applies the enable/disable matrix from the current state (`streaming_`, `connecting_`, `connectedPort_`, port selected); call `refreshControls()` at every state transition (Start, stop/finalize-idle, connect begin/result).

**Tech Stack:** C++17, CMake, Catch2, Qt. Oracle: `ui_qt/gui_state.py` / the control-state matrix (the enable rules).

## Global Constraints

- **C++17**; Qt GUI. Branch `c++`; never touch `main`. `build/` gitignored.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **Current state**: `startBtn`/`stopBtn` are LOCAL in the ctor (captured in the Start/Stop lambdas); `refreshBtn_`/`connectBtn_`/`loadBtn_`/`saveH5Check_`/`portCombo_` are members. `connectedPort_`/`connecting_` members exist; there is NO `streaming_` member yet (Start/Stop swap the two buttons inline).
- **The enable/disable matrix** (idle = not streaming, not connecting):
  | Control | Enabled when |
  |---|---|
  | refreshBtn_ | `!streaming_ && !connecting_` |
  | connectBtn_ | `!streaming_ && !connecting_` (a port may or may not be selected — keep simple: enabled when idle) |
  | startBtn_ | `!streaming_ && !connecting_` |
  | stopBtn_ | `streaming_` |
  | loadBtn_ | `!streaming_` |
  | saveH5Check_ | `!streaming_` |
  | portCombo_ | `!streaming_ && !connecting_` |
  (`saveCsvCheck_` stays permanently disabled — informational.)

## File Structure

```
gui/include/ads1292/gui/MainWindow.h + gui/src/MainWindow.cpp   # promote buttons + streaming_ + refreshControls() + call sites
tests/cpp/test_gui_smoke.cpp                                     # control-state assertions
```

---

### Task 1: promote buttons + refreshControls()

**Files:** Modify `gui/include/ads1292/gui/MainWindow.h` + `gui/src/MainWindow.cpp`; extend `tests/cpp/test_gui_smoke.cpp`.

- **Members** (MainWindow.h): `QPushButton* startBtn_ = nullptr; QPushButton* stopBtn_ = nullptr; bool streaming_ = false;`.
- **Promote** the ctor's local `startBtn`/`stopBtn` to `startBtn_`/`stopBtn_` (and update the Start/Stop lambdas to use the members instead of captured locals — capture `this` and use `startBtn_`/`stopBtn_`).
- **`void MainWindow::refreshControls()`**: apply the matrix:
  ```cpp
  if (refreshBtn_)  refreshBtn_->setEnabled(!streaming_ && !connecting_);
  if (connectBtn_)  connectBtn_->setEnabled(!streaming_ && !connecting_);
  if (startBtn_)    startBtn_->setEnabled(!streaming_ && !connecting_);
  if (stopBtn_)     stopBtn_->setEnabled(streaming_);
  if (loadBtn_)     loadBtn_->setEnabled(!streaming_);
  if (saveH5Check_) saveH5Check_->setEnabled(!streaming_);
  if (portCombo_)   portCombo_->setEnabled(!streaming_ && !connecting_);
  ```
  Call `refreshControls()` once at the end of the ctor (initial idle state: streaming_ false, connecting_ false → Start/Refresh/Connect/Load enabled, Stop disabled).
- **Test accessors** (MainWindow.h): `bool startEnabledForTest() const { return startBtn_ && startBtn_->isEnabled(); }`, `bool stopEnabledForTest() const`, `bool loadEnabledForTest() const`, and `void setStreamingForTest(bool s) { streaming_ = s; refreshControls(); }` (drive the matrix in a test).

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`, offscreen): construct MainWindow; initial (idle): `REQUIRE(mw.startEnabledForTest()); REQUIRE_FALSE(mw.stopEnabledForTest()); REQUIRE(mw.loadEnabledForTest());`. `mw.setStreamingForTest(true);` → `REQUIRE_FALSE(mw.startEnabledForTest()); REQUIRE(mw.stopEnabledForTest()); REQUIRE_FALSE(mw.loadEnabledForTest());` (streaming → Start/Load disabled, Stop enabled). `mw.setStreamingForTest(false);` → back to idle.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the members + promote + refreshControls() + the initial call + the accessors.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 GuiState control gating (refreshControls matrix)"`

---

### Task 2: call refreshControls() at every transition

**Files:** Modify `gui/src/MainWindow.cpp`; extend `tests/cpp/test_gui_smoke.cpp`.

- Replace the ad-hoc `startBtn_->setEnabled(false); stopBtn_->setEnabled(true);` (and the reverse) scattered in the Start/Stop/finished handlers with `streaming_ = true; refreshControls();` (at Start) and `streaming_ = false; refreshControls();` (at stop-request + at the finalize-idle transitions + the empty-capture early return).
- In `onConnectResult` (connect done): after setting `connecting_ = false`, call `refreshControls()` (re-enable the idle controls).
- In the Connect lambda (connect begin): after `connecting_ = true;`, call `refreshControls()` (disable Start/Refresh/etc. while connecting).
- Ensure EVERY place that currently flips a button's enabled state instead sets the `streaming_`/`connecting_` flag + calls `refreshControls()` (single source of truth). Remove the now-redundant individual setEnabled calls in those handlers (keep `refreshControls()` as the one place that gates).

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`): drive a real transition through a seam — e.g. after `mw.injectConnectResultForTest(...)` the controls are idle-enabled; (if a Start seam exists) starting sets streaming → Stop enabled. At minimum: assert that `connecting_`-style transitions gate correctly via the existing seams (injectConnectResultForTest leaves connecting_ false → controls idle-enabled). Confirm the existing persistence smoke still works (Start → stream → finalize → idle re-enables Start). 
- [ ] **Step 2: Run, verify fail/pass.**
- [ ] **Step 3: Implement** the refreshControls() calls at all transitions; remove the redundant inline setEnabled flips.
- [ ] **Step 4: Build + offscreen ctest** (existing Start/Stop/persistence tests still pass).
- [ ] **Step 5: Commit** `git commit -m "feat: P11 gate controls at every state transition"`

---

## Self-Review

**Coverage:** the matrix + refreshControls() = Task 1; the transition call-sites = Task 2. Single source of truth (refreshControls) replaces the scattered setEnabled flips.

**Risk notes:** promote startBtn/stopBtn to members carefully (the lambdas capture them — switch to `this` + the members). Don't break the existing Start/Stop/persistence behavior (the buttons must still swap correctly — now via streaming_ + refreshControls). The connecting_ gating must re-enable on connect result (don't leave the UI stuck disabled). Keep saveCsvCheck_ permanently disabled (informational).
