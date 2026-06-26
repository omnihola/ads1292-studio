# P11 Phase 4: Real Device Connection + Port Selection

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Wire the toolbar's port combo / Refresh / Connect controls so the GUI can enumerate ADS1x9x serial ports, connect to a real device (query firmware on a background thread), and acquire from it (instead of always using the simulator). Today the port/Refresh/Connect widgets are unwired locals and Start always creates `SimulatorDeviceSource`.

**Architecture:** Refresh calls `list_ads_ports()` → repopulates the port combo. Connect spawns a background thread that opens a `QSerialByteTransport` + `AdsProtocolDevice` + `query_firmware()`, then posts the result back via a queued signal to a slot that records the connected port + firmware string and updates the status. Start branches: if a port is connected, create a fresh `QSerialByteTransport` + `AdsProtocolDevice` (stored as members so they outlive the worker thread) and pass to `worker_.start(...)`; otherwise fall back to the simulator. The real-serial paths can't be CI-tested (no hardware) — they're smoke; the refresh/connect-state/start-branch LOGIC is tested via seams.

**Tech Stack:** C++17, CMake, Catch2, Qt (SerialPort). Oracle: `controller.py` (connect → query firmware → start with the device), `device.py`.

## Global Constraints

- **C++17**; Qt GUI + qt_runtime (QSerialPort) + core/acq. Branch `c++`; never touch `main`. `build/` gitignored. Reconfigure after adding files.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **Reuse:** `qt/AdsPorts.h list_ads_ports() -> std::vector<AdsPort{device,description,hwid}>`; `qt/QSerialByteTransport(const QString& port_name, int timeout_ms)`; `acq/AdsProtocolDevice(IByteTransport&, double sample_rate_hz)` + `query_firmware()`; `acq/SimulatorDeviceSource`; `qt/AcquisitionWorker::start(IDeviceSource*, AcquisitionMode, csv_path)`.
- **The real-serial paths (open port / query_firmware / stream over a live board) are SMOKE/hardware-only.** Test the refresh enumeration (no crash, boardless → no ADS ports), the connect-RESULT state machine (via a seam injecting a fake result), and the Start branch-selection (via a seam) — NOT a real serial open.
- **Device lifetime:** the `QSerialByteTransport` + `AdsProtocolDevice` for a real acquisition MUST outlive the worker thread — store as members (`std::unique_ptr`), created at Start, cleared on stop/finalize. The finalize-thread join (Phase 1 dtor) + worker stop bound their lifetime.
- **Threading:** the Connect query-firmware runs on a background thread; results return via QMetaObject::invokeMethod/queued signal (no off-GUI-thread widget access). Store the connect thread as a member + join in the dtor (like the finalize thread).

## File Structure

```
gui/include/ads1292/gui/MainWindow.h + gui/src/MainWindow.cpp   # port combo/Refresh/Connect members + wiring; Start branch; device members
tests/cpp/test_gui_smoke.cpp                                     # refresh + connect-state + start-branch seams
```

---

### Task 1: Refresh — enumerate ports into the combo

**Files:** Modify `gui/include/ads1292/gui/MainWindow.h` + `gui/src/MainWindow.cpp`; extend `tests/cpp/test_gui_smoke.cpp`.

- Store the port combo + Refresh button as members: `QComboBox* portCombo_ = nullptr; QPushButton* refreshBtn_ = nullptr;` (declare in .h; assign in the ctor instead of the locals).
- A method `void MainWindow::refreshPorts()`: `portCombo_->clear(); auto ports = ads1292::qt::list_ads_ports(); if (ports.empty()) { portCombo_->addItem("(no port)"); } else { for (const auto& p : ports) portCombo_->addItem(QString::fromStdString(p.device + " — " + p.description)); }` (store the device path as the item's userData via `addItem(text, QVariant(QString::fromStdString(p.device)))` so Connect/Start can read the raw device path). Wire `connect(refreshBtn_, &QPushButton::clicked, this, &MainWindow::refreshPorts);` (or a lambda). Call `refreshPorts()` once in the ctor to populate initially.
- Test accessor: `int portComboCountForTest() const { return portCombo_ ? portCombo_->count() : 0; }` and `void refreshPortsForTest() { refreshPorts(); }`.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`, offscreen): construct MainWindow; `mw.refreshPortsForTest();` → `REQUIRE(mw.portComboCountForTest() >= 1);` (on a boardless CI host, list_ads_ports() is empty → the combo has the single "(no port)" item; with a board it has the ports — either way >= 1, no crash). The point is refresh runs + populates without crashing.
- [ ] **Step 2: Run, verify fail** (refreshPorts / the accessors don't exist).
- [ ] **Step 3: Implement** the members + refreshPorts + the wiring + accessors.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 Refresh enumerates ADS ports into the combo"`

---

### Task 2: Connect — background firmware query + connection state

**Files:** Modify `gui/include/ads1292/gui/MainWindow.h` + `gui/src/MainWindow.cpp`; extend `tests/cpp/test_gui_smoke.cpp`.

- Members: `QPushButton* connectBtn_ = nullptr; std::string connectedPort_; bool connecting_ = false; std::thread connectThread_;`.
- A slot `void MainWindow::onConnectResult(bool ok, const std::string& port, const std::string& detail)` (GUI thread): `connecting_ = false; if (ok) { connectedPort_ = port; state_.connection = "connected " + port + " (fw " + detail + ")"; } else { connectedPort_.clear(); state_.connection = "connect failed: " + detail; } statusPanel_->updateFromState(state_); ...` (re-enable buttons).
- Wire `connect(connectBtn_, &QPushButton::clicked, ...)`: read the selected port path from `portCombo_->currentData().toString().toStdString()` (the device path stored in Task 1); if empty / "(no port)" → log + return; set `connecting_ = true`; if `connectThread_.joinable()` join it; spawn `connectThread_ = std::thread([this, port]{ bool ok=false; std::string detail; try { ads1292::qt::QSerialByteTransport t(QString::fromStdString(port), 1000); ads1292::acq::AdsProtocolDevice dev(t, 500.0); detail = dev.query_firmware(); ok = (detail.rfind("no firmware response",0) != 0); } catch (const std::exception& e) { ok=false; detail = e.what(); } QMetaObject::invokeMethod(this, [this,ok,port,detail]{ onConnectResult(ok, port, detail); }, Qt::QueuedConnection); });`. (The transport is local to the connect thread — opened, queried, closed when the thread ends. This is a VALIDATION connect; Start re-opens for streaming.)
- In `~MainWindow()`: also `if (connectThread_.joinable()) connectThread_.join();` (alongside the finalize-thread join — close the UAF).
- **Test seam:** `void MainWindow::injectConnectResultForTest(bool ok, const std::string& port, const std::string& detail) { onConnectResult(ok, port, detail); }` + `std::string connectedPortForTest() const { return connectedPort_; }`. (The real serial open needs hardware; the test drives the RESULT handling.)

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`): construct MainWindow; `mw.injectConnectResultForTest(true, "/dev/cu.usbserial-1", "1.12");` → `REQUIRE(mw.connectedPortForTest() == "/dev/cu.usbserial-1");`. Then `mw.injectConnectResultForTest(false, "", "open failed");` → `REQUIRE(mw.connectedPortForTest().empty());` (failure clears the connected port). This tests the connect-state machine without hardware.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the members + onConnectResult + the Connect wiring (background thread) + the dtor join + the seams.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 Connect queries firmware on a background thread + tracks connection state"`

---

### Task 3: Start branches on the real device vs the simulator

**Files:** Modify `gui/src/MainWindow.cpp` + `.h`; extend `tests/cpp/test_gui_smoke.cpp`.

- Members for the real-device lifetime: `std::unique_ptr<ads1292::qt::QSerialByteTransport> transport_; std::unique_ptr<ads1292::acq::AdsProtocolDevice> realDevice_;`.
- In the Start lambda: after computing the csv_path, BRANCH:
  ```cpp
  if (!connectedPort_.empty()) {
    transport_ = std::make_unique<ads1292::qt::QSerialByteTransport>(QString::fromStdString(connectedPort_), 1000);
    realDevice_ = std::make_unique<ads1292::acq::AdsProtocolDevice>(*transport_, 500.0);
    worker_.start(realDevice_.get(), mode, recordingCsvPath_);
  } else {
    activeSource_ = std::make_unique<ads1292::acq::SimulatorDeviceSource>(200, 0);
    worker_.start(activeSource_.get(), mode, recordingCsvPath_);
  }
  ```
  Set `opt.port = connectedPort_;` in buildFinalizeOptions (so the provenance records the real port — fixes the Phase-1 M2 deferral).
- On stop/finalize completion: the worker stop + finalize join bound the device; clear `realDevice_`/`transport_` after the finalize completes (or in the idle transition) so the port is released. (Don't clear mid-stream.)
- **Test seam:** the real-serial branch needs hardware. Add `bool startUsesRealDeviceForTest() const { return !connectedPort_.empty(); }` so a test can assert the branch SELECTION: inject a connected port (Task 2 seam) → `REQUIRE(mw.startUsesRealDeviceForTest());`; no connected port → `REQUIRE_FALSE(...)` (simulator path). (Do NOT open a real serial port in the test.)

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`): construct MainWindow; with no connect → `REQUIRE_FALSE(mw.startUsesRealDeviceForTest());`. `mw.injectConnectResultForTest(true, "/dev/cu.x", "1.12");` → `REQUIRE(mw.startUsesRealDeviceForTest());`. (The branch-selection predicate; the actual real-serial Start is hardware-only.) Also confirm the existing simulator-based persistence smoke still works (no connected port → simulator → bundle written).
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the device members + the Start branch + `opt.port` + the post-finalize device cleanup + the seam.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 Start acquires from the connected device or the simulator"`

---

## Self-Review

**Coverage:** refresh (Task 1), connect + state (Task 2), start-branch + device lifetime (Task 3). The real-serial open/query/stream is hardware-only (smoke); the refresh enumeration, connect-result state machine, and start-branch predicate are seam-tested. The provenance port (Phase-1 M2) is filled here.

**Type consistency:** `list_ads_ports` (Task 1) → combo userData; `connectedPort_` set by `onConnectResult` (Task 2) consumed by the Start branch (Task 3); the device members (transport_/realDevice_) outlive the worker. The connect thread + finalize thread both joined in the dtor.

**Risk notes:** device lifetime — transport_/realDevice_ must outlive the worker thread; create at Start, clear only after finalize (not mid-stream). Threading — connect query on a background thread, result via queued invokeMethod, thread joined in dtor (UAF closed). The real-serial paths can't be CI-tested — don't fake a hardware test; seam-test the logic + document the hardware-only paths. Don't regress the simulator persistence path (no connected port → simulator → bundle).
