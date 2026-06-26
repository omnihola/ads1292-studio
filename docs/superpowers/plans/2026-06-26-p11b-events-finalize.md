# P11 Phase 2: Live Events → Finalization

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Events annotated during acquisition (via the EventConsole) are saved into the recording bundle + H5 on Stop, and a loaded recording's events are shown in the review event panel. Today `onWorkerFinished` snapshots `opt.events = {}` (events are dropped); the event log isn't cleared at Start; loaded recordings don't display their events.

**Architecture:** On the GUI thread in `onWorkerFinished`, snapshot `eventConsole_->log().events()` into `opt.events` BEFORE spawning the finalize thread (avoiding a race). Add `EventConsole::clear()` and call it at Start (fresh log per recording). On load, read events from the recording's bundle (if present) and call `reviewEventLogPanel_->setEvents(events)`.

**Tech Stack:** C++17, CMake, Catch2, Qt. Oracle: `controller.py` (`_finalize_recording` snapshots `tuple(self.event_markers)` on the GUI thread; load → `set_event_markers`).

## Global Constraints

- **C++17**; Qt GUI + io. Branch `c++`; never touch `main`. `build/` gitignored. Reconfigure after adding files.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **Reuse:** `EventConsole::log()` → `ads1292::view::EventLog`; `EventLog::events()` → `const std::vector<ads1292::EventMarker>&`. `io::finalize_live_recording`'s `FinalizeOptions::events`. `io::is_recording_bundle_path`/`read_recording_bundle`/`events_from_bundle` (P10). `ReviewEventLogPanel::setEvents(const std::vector<EventMarker>&)`. `EventConsole::addPointEventForTest(label, notes)` (test seam to inject events).
- **Snapshot on the GUI thread** (not in the finalize thread) — the events vector is captured by value into `opt`, then `opt` is captured by value by the thread (already the pattern from Phase 1). Match Python's GUI-thread snapshot.

## File Structure

```
gui/include/ads1292/gui/EventConsole.h + gui/src/EventConsole.cpp   # ADD clear()
gui/include/ads1292/gui/MainWindow.h + gui/src/MainWindow.cpp        # snapshot events in onWorkerFinished + clear at Start + setEvents on load
tests/cpp/test_gui_smoke.cpp                                          # extend
```

---

### Task 1: snapshot events into finalize + clear at Start

**Files:** Modify `gui/include/ads1292/gui/EventConsole.h` + `gui/src/EventConsole.cpp` (add `clear()`); Modify `gui/src/MainWindow.cpp` (snapshot + clear); extend `tests/cpp/test_gui_smoke.cpp`.

**Interfaces:**
- `void EventConsole::clear();` — clears the owned `log_` (EventLog — add `EventLog::clear()` if it lacks one: `events_.clear();` + reset any pending range) + refreshes the status line to 0.

**MainWindow changes:**
- In `onWorkerFinished` (GUI thread): set `opt.events = eventConsole_->log().events();` (snapshot the current annotations) — replace the `{}`. (This is captured by value into `opt`, then into the finalize thread lambda — safe.)
- At Start (startBtn lambda): `eventConsole_->clear();` (fresh event log for the new recording) before/after `worker_.start(...)`.
- For the test: ensure `finalizeForTest()` (the Phase-1 seam) also snapshots `eventConsole_->log().events()` into its `opt` (so a test can inject events via `addPointEventForTest` then finalize and see them in the bundle). If `finalizeForTest` builds opt via `buildFinalizeOptions()`, make `buildFinalizeOptions()` set `opt.events = eventConsole_->log().events();` so both the real path and the seam share it.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`, offscreen): construct MainWindow; set recordingsDir to temp; inject events via `eventConsole`'s test seam — expose `EventConsole* eventConsoleForTest()` or add events through a MainWindow seam — call `eventConsole_->addPointEventForTest("rest","baseline")` (twice, one a range if the seam supports it); pre-author a CSV (the Phase-1 seam pattern); call `finalizeForTest()`; read the produced bundle (`read_recording_bundle`) → `events_from_bundle(bundle)` → assert the injected events are present (size >= the count + a label matches). Before the fix `opt.events` is `{}` → the bundle has 0 events → test fails.
  - Also assert `EventConsole::clear()` empties the log (`addPointEventForTest` then `clear()` → `log().events().empty()`).
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** `EventConsole::clear()` (+ `EventLog::clear()` if needed), the snapshot in `buildFinalizeOptions()`/onWorkerFinished, and `eventConsole_->clear()` at Start. Add an `EventConsole* eventConsoleForTest()` seam on MainWindow if needed for the test.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 snapshot live events into finalize + clear log at Start"`

---

### Task 2: display a loaded recording's events

**Files:** Modify `gui/src/MainWindow.cpp` (loadRecordingForTest / the load path); extend `tests/cpp/test_gui_smoke.cpp`.

**MainWindow changes:**
- In `loadRecordingForTest(csvPath)` (the existing load path): after reading the CSV, ALSO read the recording's events: `auto bp = ads1292::io::recording_bundle_path(csvPath); std::vector<ads1292::EventMarker> events; if (ads1292::io::is_recording_bundle_path(bp)) events = ads1292::io::events_from_bundle(ads1292::io::read_recording_bundle(bp));` then `reviewEventLogPanel_->setEvents(events);` (and update any event-count display). (If there's no bundle, events stay empty — no change.)
  - Store the loaded events in a member if the review waveform overlay needs them (Phase 6 expands this); for Phase 2, populating the ReviewEventLogPanel is sufficient.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp`): build a recording dir with `rec.csv` + a bundle `rec.json` (via `write_recording_bundle` with 2 known events); construct MainWindow; `mw.loadRecordingForTest((dir/"rec.csv").string());` then assert the review event panel reflects the 2 events. Expose a test accessor on MainWindow or ReviewEventLogPanel (`int reviewEventCountForTest()` or read the panel text) to assert the events were set. Before the fix, load doesn't read events → panel shows 0 → test fails.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the event read + `setEvents` in the load path + the test accessor.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 display loaded recording's events in the review panel"`

---

## Self-Review

**Coverage:** events-into-bundle = Task 1 (snapshot + clear); events-on-load = Task 2. Both reuse the P10 read API + the EventConsole/ReviewEventLogPanel. The live waveform event-overlay during acquisition is already present (P6 era) — this phase is about the SAVE + LOAD round-trip of annotations.

**Type consistency:** `EventConsole::log().events()` (vector<EventMarker>) → `opt.events` (Task 1); `events_from_bundle` (vector<EventMarker>) → `setEvents` (Task 2). `EventConsole::clear()` new.

**Risk notes:** snapshot events on the GUI thread (in onWorkerFinished/buildFinalizeOptions), never in the finalize thread (race). `EventLog::clear()` must also reset any pending range state in the EventConsole status. The load path reads events only if a bundle exists (non-bundle CSV → empty, no regression).
