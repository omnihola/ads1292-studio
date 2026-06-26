# P11 Phase 9: Live Calibration (testable model/stats + GUI wiring; device measurement hardware-only)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Port the live-stream calibration DATA MODEL + STATISTICS (LiveStreamCalibration + normalized + peak-to-peak + summarize — all testable) and wire a "Calibrate Live" button + result state + the bundle's `acquisition.live_calibration`. The actual device measurement (`run_live_stream_calibration`, which needs ADS1292 register-level commands the C++ device layer never implemented) is a documented HARDWARE-ONLY path — like P7d/Phase-4's real-serial paths.

**Architecture:** A `LiveStreamCalibration` model + `live_stream_peak_to_peak_counts(values)` + `summarize_live_stream_calibration(peak_to_peak_counts, test_signal_pp_uv)` (pure math, fully tested). A "Calibrate Live" button spawns a background thread that — on real hardware — would run the register-level calibration; that device method is documented hardware-only. The result (a `LiveStreamCalibration`) flows to `onCalibrateResult` (seam-tested), is stored, and is written into the bundle's `acquisition.live_calibration` json. The whole non-device path (model + stats + result-state + bundle wiring) is tested; only the register-command measurement is hardware-only.

**Tech Stack:** C++17, CMake, Catch2. Oracle: `src/ads1292_studio/calibration.py` (LiveStreamCalibration, normalized, live_stream_peak_to_peak_counts, summarize_live_stream_calibration), `device.py` (run_live_stream_calibration — hardware-only).

## Global Constraints

- **C++17**; the model/stats are core (no Qt); the button/state are gui. Branch `c++`; never touch `main`. `build/` gitignored. Reconfigure after adding files.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **`LiveStreamCalibration` (calibration.py)**: `double mean_uv_per_count; double std_uv_per_count; double cv_percent; int runs; double test_signal_pp_uv; std::string scale_type = "live_processed";` + `normalized()`: mean as-is; std = max(0, std); runs = max(0, runs); cv = cv>=0 ? cv : 0; test_signal = test_signal_pp_uv > 0 ? test_signal_pp_uv : 2016.6666666667; scale_type = trim(scale_type) or "live_processed".
- **`live_stream_peak_to_peak_counts(values)`**: require >= 4 samples; keep finite; require >= 4 finite; `low,high = percentile(finite, [1.0, 99.0])`; pp = high - low; require pp > 0; return pp. (Reuse the C++ `percentile` from `core/dsp/Stats.h` — match numpy percentile (linear interpolation). Throw std::invalid_argument on the error conditions, matching Python ValueError.)
- **`summarize_live_stream_calibration(peak_to_peak_counts, test_signal_pp_uv)`**: filter counts > 0; require non-empty; `scales[i] = test_signal_pp_uv / counts[i]`; mean = mean(scales); std = (scales.size()>1) ? sample-std (ddof=1) : 0.0; cv = mean ? (std/mean*100) : 0; → `LiveStreamCalibration{mean, std, cv, (int)scales.size(), test_signal_pp_uv}.normalized()`.
- **Bundle wiring**: `AcquisitionProvenance.live_calibration` is an `nlohmann::json` object. A `live_calibration_to_json(const LiveStreamCalibration&)` → `{mean_uv_per_count, std_uv_per_count, cv_percent, runs, test_signal_pp_uv, scale_type}` (read calibration.py for the exact key names/order of the acquisition live-calibration dict — CONFIRM via the Python serialization). When a calibration is present, the GUI sets the provenance's live_calibration before finalize.
- **The device measurement is HARDWARE-ONLY** — do NOT port the register R/W blind; the Calibrate worker is a documented hardware-only path. For the smoke, the result is injected via a seam.

## File Structure

```
core/include/ads1292/model/LiveStreamCalibration.h + core/src/.../LiveStreamCalibration.cpp   # NEW: model + normalized
core/include/ads1292/dsp/LiveCalibration.h + core/src/dsp/LiveCalibration.cpp                  # NEW: peak_to_peak + summarize (or fold into the model module)
gui/src/MainWindow.cpp + .h                                                                     # Calibrate button + state + bundle wiring
tests/cpp/test_live_calibration.cpp                                                            # NEW
```

---

### Task 1: LiveStreamCalibration model + statistics

**Files:** Create the model + stats headers/sources (place sensibly — e.g. `core/.../LiveStreamCalibration.h` for the struct + `core/dsp/LiveCalibration.h` for the 2 functions, OR one module); core CMake; Create `tests/cpp/test_live_calibration.cpp`; tests CMake.

**Interfaces (namespace `ads1292` for the model, `ads1292::dsp` for the stats — match the codebase's conventions):**
- `struct LiveStreamCalibration { double mean_uv_per_count=0; double std_uv_per_count=0; double cv_percent=0; int runs=0; double test_signal_pp_uv=0; std::string scale_type="live_processed"; LiveStreamCalibration normalized() const; };`
- `double live_stream_peak_to_peak_counts(const std::vector<double>& values);`
- `LiveStreamCalibration summarize_live_stream_calibration(const std::vector<double>& peak_to_peak_counts, double test_signal_pp_uv);`

- [ ] **Step 1: Write the failing test** (`tests/cpp/test_live_calibration.cpp`):
  - `normalized()`: a LiveStreamCalibration with std=-1, runs=-2, cv=-5, test_signal=0, scale_type="  " → normalized → std==0, runs==0, cv==0, test_signal==Approx(2016.6666666667), scale_type=="live_processed".
  - `live_stream_peak_to_peak_counts`: a ramp/known array of >=4 values → assert pp == Approx(percentile99 - percentile1) (compute the expected from a known small array, e.g. `{0,1,2,...,100}` → p1≈1, p99≈99 → pp≈98, with numpy linear interpolation — compute the exact expected). `{1,2,3}` (size 3) → throws. An all-equal array → pp<=0 → throws.
  - `summarize_live_stream_calibration`: `peak_to_peak_counts = {100.0, 100.0}` (2 runs equal), `test_signal_pp_uv = 2000.0` → scales = {20.0, 20.0} → mean 20.0, std 0.0, cv 0.0, runs 2. A varying set, e.g. `{100, 200}`, test 2000 → scales {20, 10} → mean 15, std = sample-std({20,10}) = `sqrt(((20-15)^2+(10-15)^2)/(2-1))` = `sqrt(50)` ≈ 7.0710678, cv = 7.0710678/15*100 ≈ 47.14. Empty/all-zero → throws.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the struct + normalized + peak_to_peak (reuse `ads1292::dsp::percentile` — confirm it matches numpy linear interpolation; if not, compute [1,99] percentile with linear interpolation directly) + summarize (filter>0, scales, mean, sample-std ddof=1, cv).
- [ ] **Step 4: Wire CMake, build, ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 LiveStreamCalibration model + statistics (peak-to-peak, summarize)"`

---

### Task 2: Calibrate button + result state + bundle live_calibration

**Files:** Modify `gui/src/MainWindow.cpp` + `.h`; (a `live_calibration_to_json` in io or the gui); extend the tests.

- **`live_calibration_to_json(const ads1292::LiveStreamCalibration&)`** → `nlohmann::json` with the keys Python writes for `acquisition.live_calibration` (READ calibration.py / acquisition.py for the exact dict — likely `{mean_uv_per_count, std_uv_per_count, cv_percent, runs, test_signal_pp_uv, scale_type}`; match the key names + any rounding). Put it where the bundle/acquisition serialization lives (io) or a small gui helper.
- **GUI**: add a `QPushButton* calibrateBtn_ = nullptr;` "Calibrate Live" to the toolbar. Member `std::optional<ads1292::LiveStreamCalibration> liveCalibration_;` + `std::thread calibrateThread_;`.
- **Calibrate clicked**: if no `connectedPort_` → log "connect a device first" + return. Else `calibrating_ = true; refreshControls();` (gate the buttons), spawn `calibrateThread_` that — on real hardware — would run the register-level calibration (DOCUMENTED HARDWARE-ONLY: the C++ AdsProtocolDevice lacks register R/W; this path is a stub that reports "live calibration requires the register-level device protocol (hardware-only; not ported)" OR, if you choose, a minimal best-effort — but DO NOT port the register commands blind; document it). Post the result/failure back via `QMetaObject::invokeMethod` → `onCalibrateResult`.
- **`onCalibrateResult(bool ok, const LiveStreamCalibration& cal, const std::string& detail)`** (GUI thread): `calibrating_ = false;` if ok → `liveCalibration_ = cal.normalized(); state_.connection += " | cal " + fmt(cal.mean_uv_per_count) + " uV/count";` else log detail. `refreshControls();`.
- **Dtor**: join `calibrateThread_` (UAF — like the finalize/connect threads).
- **Bundle wiring**: in `buildFinalizeOptions()`, if `liveCalibration_` has a value, set the FinalizeOptions' acquisition live_calibration (finalize_live_recording's provenance gets `a.live_calibration = live_calibration_to_json(*liveCalibration_)`). Pass `liveCalibration_` through FinalizeOptions (add `std::optional<...> live_calibration;` to FinalizeOptions) and in finalize_live_recording set `a.live_calibration = live_calibration_to_json(*opt.live_calibration)` when present.
- **refreshControls**: gate `calibrateBtn_` (enabled when `!streaming_ && !connecting_ && !calibrating_ && a port connected`).
- **Test seam**: `void injectCalibrateResultForTest(const ads1292::LiveStreamCalibration& cal) { onCalibrateResult(true, cal, ""); }` + `bool hasLiveCalibrationForTest() const { return liveCalibration_.has_value(); }`.

- [ ] **Step 1: Write the failing test** (extend `test_gui_smoke.cpp` + `test_live_finalize.cpp`):
  - gui: construct MainWindow; assert `calibrateBtn_` exists; `mw.injectCalibrateResultForTest(<a LiveStreamCalibration mean=0.0481>)` → `REQUIRE(mw.hasLiveCalibrationForTest());`.
  - bundle wiring: set a live calibration via the seam, run the finalize seam → read the bundle → `acquisition_from_bundle(...).live_calibration` (the json) has `mean_uv_per_count` ≈ the injected value. (Confirm via read_recording_bundle → the acquisition section's live_calibration object.) OR an io test: `FinalizeOptions opt; opt.live_calibration = <cal>;` → finalize → bundle's acquisition.live_calibration non-empty with the mean.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** live_calibration_to_json + the button + the calibrate thread (hardware-only documented path) + onCalibrateResult + dtor join + refreshControls gating + the FinalizeOptions.live_calibration + finalize wiring + the seams.
- [ ] **Step 4: Build + offscreen ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P11 Calibrate Live button + live_calibration into the bundle (device measurement hardware-only)"`

---

## Self-Review

**Coverage:** the model + stats (Task 1, fully tested) + the button/state/bundle-wiring (Task 2, seam-tested). The device register-level measurement is DOCUMENTED HARDWARE-ONLY (not ported blind) — consistent with the user's decision + the P7d/Phase-4 hardware-only-path precedent.

**Type consistency:** `LiveStreamCalibration` (Task 1) → `liveCalibration_` + `live_calibration_to_json` (Task 2) → the bundle's acquisition.live_calibration. The calibrate thread joined in the dtor (UAF) like the finalize/connect threads.

**Risk notes:** `live_stream_peak_to_peak_counts` percentile must match numpy [1,99] linear interpolation (reuse/verify the C++ percentile). `summarize` std is SAMPLE std (ddof=1). The device measurement is hardware-only — do NOT port register R/W blind; document it + seam-test the result path. Join the calibrate thread in the dtor (it captures this). Confirm the live_calibration json key names against calibration.py/acquisition.py.
