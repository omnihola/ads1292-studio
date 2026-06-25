# P5d: Live GUI Backfill (display filters + R-peak/HR/SNR overlay) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the P4 live monitor by porting the Python `build_live_render_frame` pipeline — software display filters (HP/Notch/LP/QRS), smoothing, gated R-peak detection + markers, live HR, and a real-time SNR readout — and rendering it in the LiveScope/MainWindow, making the four disabled "(P5)" filter checkboxes live.

**Architecture:** Port `build_live_render_frame` as a PORTABLE core function (`core/view`, pure C++17, no Qt) that takes the raw rolling window (ch1/ch2/status/indices) + display/filter settings and returns a `LiveRenderFrame` (filtered+smoothed+decimated traces, R-peak markers, HR, SNR). The GUI becomes a thin renderer of that frame. It reuses the verified P5a filters and P5b/P5c DSP. No new golden fixtures exist for live render (the P-1 freeze didn't capture frames), so the portable pieces are unit-tested against constructed inputs and the GUI is smoke-tested offscreen.

**Tech Stack:** C++17, CMake, Catch2; Qt Widgets + the P4 IWaveformPlot/QCustomPlotWaveform backend. Oracle: `live_render.py`, `signal_processing.py` (`apply_software_filters`), `plots.py` (`smooth_for_plot`/`decimate_*`), `display.py` (settings).

## Global Constraints

- **C++17**; `core/view` + `core/dsp` stay pure portable C++ (stdlib only, all `double`, no Qt/OS). The GUI layer (gui/) uses Qt; only `QCustomPlotWaveform.cpp` may include `qcustomplot.h` (P4 GPL isolation — preserve it).
- **Layering**: `core/view` depends on `core/dsp` (P5a/P5b/P5c) only. GUI depends on `core` + the IWaveformPlot abstraction.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`. Qt widget tests run under `QT_QPA_PLATFORM=offscreen`; reuse the existing `ensureApp()` guard in `tests/cpp/test_gui_smoke.cpp` (do NOT construct extra QApplications).
- **No new golden fixtures** — P5d is GUI integration. Portable helpers are unit-tested against hand-computed values + reasoning vs the oracle; GUI is offscreen smoke-tested. The filters/peaks/SNR themselves are already golden-verified in P5a/P5b/P5c.
- **`apply_software_filters(values, sr, settings)` (signal_processing.py):** if `settings.bandpass_enabled` → return `bandpass(values, sr)` (QRS filter; returns immediately, overriding the others). Else apply IN SEQUENCE: `if highpass_enabled: display = highpass(display, sr, highpass_hz)`; `if notch_enabled: display = notch(display, sr, notch_hz)`; `if lowpass_enabled: display = lowpass(display, sr, lowpass_hz)`; return display.
- **`SoftwareFilterSettings`:** `bool highpass_enabled=false, notch_enabled=false, lowpass_enabled=false, bandpass_enabled=false; double highpass_hz=0.5, notch_hz=60.0, lowpass_hz=40.0`.
- **`EcgDisplaySettings`:** `double time_window_seconds=8.0, gain=1.0; int sweep_speed_mm_s=25`.
- **`smooth_for_plot(values, window=5)` (plots.py):** if `window<=1 || size<window` → return values unchanged; if `window` even → `window+=1`; `pad=window/2`; edge-pad `values` by `pad` on each side; return the moving average (convolution with `1/window` kernel, 'valid' mode) → output length == input size.
- **`endpoint_indices(size, max_points)`:** if `size<=0||max_points<=0`→`{}`; if `size<=max_points`→`{0..size-1}`; else `unique( (int)(i*(size-1)/(count-1)) for i in 0..count-1 )` with `count=max(1,max_points)` (numpy `linspace(0,size-1,count,dtype=int)` truncates toward zero; then unique-sort).
- **`extrema_bin_edges(size, max_points)`:** `bin_count=max(1,(max_points-2)/2)` (int div); edges = `(int)(i*size/bin_count)` for `i in 0..bin_count` (numpy `linspace(0,size,bin_count+1,dtype=int)`).
- **`decimate_for_plot(x, y, max_points)`:** if `size<=max_points`→`(x,y)`; else `idx=endpoint_indices(size,max_points)`; return `(x[idx], y[idx])`.
- **`decimate_extrema_for_plot(x, y, max_points)`:** if `size<=max_points`→`(x,y)`; if `max_points<4`→`decimate_for_plot`; else `edges=extrema_bin_edges`; `keep={0, size-1}`; for each `[start,stop)` bin: if `stop>start`, add `start+argmin(y[start:stop])` and `start+argmax(...)`; return `(x[idx], y[idx])` over `sorted(unique(keep))`.
- **`build_live_render_frame(...)` (live_render.py):** guard `!finite(sr)||sr<=0` → none. `visible_count = min(buffers' sizes, (int)(time_window_seconds*sr)+2)`; if `<=0` → none. `visible_x = tail(indices, visible_count)/sr`; `left = max(0, x[-1]-window)`; `right = max(window, x[-1])`. `ecg_raw=tail(ch2)`, `resp_raw=tail(ch1)`. `visible_ecg = display_signal_values(ecg_raw, settings, invert=ecg_inverted, gain)`; `visible_resp = display_signal_values(resp_raw, settings, invert=false, gain)`. `display_signal_values`: `display=apply_software_filters(v,sr,settings)`; `scale = invert ? -gain : gain`; return `scale==1.0 ? display : display*scale`. `visible_ecg_plot=smooth_for_plot(visible_ecg, smoothing_window)`; same for resp. `visible_status=tail(status)`. `contact_ok = status.size && mean(status==0) >= 0.95`. `ecg_has_signal = ptp(visible_ecg) > 1e-9`. If `contact_ok && ecg_has_signal && visible_count >= (int)(1.0*sr)` → `peaks = detect_r_peaks(visible_ecg, sr, prefiltered=bandpass_enabled)` else `peaks={}`. `peaks_x=visible_x[peaks]`, `peaks_y=visible_ecg_plot[peaks]`. `(plot_ecg_x,plot_ecg)=decimate_extrema_for_plot(visible_x,visible_ecg_plot,max_render_points)`; same for resp; `(plot_status_x,plot_status)=decimate_for_plot(visible_x,visible_status,max_render_points)`. `heart_rate=heart_rate_summary(peaks,sr)`; `snr=estimate_realtime_snr(visible_ecg,sr)`.
- **`detect_r_peaks` prefiltered param:** extend P5b `detect_r_peaks(values, sr)` to `detect_r_peaks(values, sr, bool prefiltered=false)`: if `prefiltered`, skip the bandpass (`filtered = values` directly); else `filtered = bandpass(values, sr)`. Rest unchanged. (Matches the Python keyword arg.)

## File Structure

```
core/
  include/ads1292/dsp/Display.h        # EcgDisplaySettings, SoftwareFilterSettings, apply_software_filters
  src/dsp/Display.cpp
  include/ads1292/view/PlotDecimate.h  # smooth_for_plot, endpoint_indices, extrema_bin_edges, decimate_for_plot, decimate_extrema_for_plot
  src/view/PlotDecimate.cpp
  include/ads1292/view/LiveRender.h    # LiveRenderFrame, build_live_render_frame
  src/view/LiveRender.cpp
  src/dsp/EcgReview.cpp                 # MODIFY: detect_r_peaks gains a prefiltered param
gui/
  include/ads1292/gui/IWaveformPlot.h   # MODIFY: add setMarkers(graphIndex, x, y)
  src/QCustomPlotWaveform.cpp           # MODIFY: implement markers (scatter graph)
  src/LiveScope.{h,cpp}                 # MODIFY: hold raw buffers + settings; render LiveRenderFrame
  src/MainWindow.{h,cpp}                # MODIFY: 4 filter checkboxes live + SNR/HR strip
tests/cpp/
  test_display_filters.cpp   # apply_software_filters chain
  test_plot_decimate.cpp     # smooth + decimate helpers
  test_live_render.cpp       # build_live_render_frame
  test_gui_smoke.cpp         # MODIFY: LiveScope/MainWindow filter+SNR smoke
```

---

### Task 1: display settings + filter chain + plot helpers

**Files:**
- Create: `core/include/ads1292/dsp/Display.h`, `core/src/dsp/Display.cpp`; `core/include/ads1292/view/PlotDecimate.h`, `core/src/view/PlotDecimate.cpp`.
- Modify: `core/CMakeLists.txt`; Create `tests/cpp/test_display_filters.cpp`, `tests/cpp/test_plot_decimate.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: P5a `bandpass`/`highpass`/`lowpass`/`notch` (Filtfilt.h).
- Produces (namespace `ads1292::dsp`): `struct EcgDisplaySettings {...}`, `struct SoftwareFilterSettings {...}`, `std::vector<double> apply_software_filters(const std::vector<double>& values, double sr, const SoftwareFilterSettings& s);`
- Produces (namespace `ads1292::view`): `std::vector<double> smooth_for_plot(const std::vector<double>& values, int window);`, `std::vector<int> endpoint_indices(int size, int max_points);`, `std::vector<int> extrema_bin_edges(int size, int max_points);`, `void decimate_for_plot(const std::vector<double>& x, const std::vector<double>& y, int max_points, std::vector<double>& ox, std::vector<double>& oy);`, `void decimate_extrema_for_plot(...same sig...);`

- [ ] **Step 1: Write the failing tests** (filter chain + plot helpers, hand-computed/oracle-derived)

```cpp
// tests/cpp/test_display_filters.cpp
#include "catch.hpp"
#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/Filtfilt.h"
using namespace ads1292::dsp;
TEST_CASE("apply_software_filters: bandpass_enabled returns the QRS bandpass", "[live]") {
  std::vector<double> v(600); for (size_t i=0;i<v.size();++i) v[i] = std::sin(0.1*i)*30.0;
  SoftwareFilterSettings s; s.bandpass_enabled = true;
  REQUIRE(apply_software_filters(v, 500.0, s) == bandpass(v, 500.0));   // exact same vector
}
TEST_CASE("apply_software_filters: none enabled returns input unchanged", "[live]") {
  std::vector<double> v = {1,2,3,4,5};
  REQUIRE(apply_software_filters(v, 500.0, SoftwareFilterSettings{}) == v);
}
TEST_CASE("apply_software_filters: hp+notch composes highpass then notch", "[live]") {
  std::vector<double> v(600); for (size_t i=0;i<v.size();++i) v[i]=i%7;
  SoftwareFilterSettings s; s.highpass_enabled=true; s.notch_enabled=true;
  auto expect = notch(highpass(v, 500.0, 0.5), 500.0, 60.0);
  REQUIRE(apply_software_filters(v, 500.0, s) == expect);
}
```
```cpp
// tests/cpp/test_plot_decimate.cpp
#include "catch.hpp"
#include "ads1292/view/PlotDecimate.h"
using namespace ads1292::view;
TEST_CASE("smooth_for_plot: window<=1 or short returns input", "[live]") {
  std::vector<double> v={1,2,3};
  REQUIRE(smooth_for_plot(v,1)==v);
  REQUIRE(smooth_for_plot(v,5)==v);   // size<window
}
TEST_CASE("smooth_for_plot: moving average preserves length", "[live]") {
  std::vector<double> v={0,0,0,10,0,0,0};
  auto s = smooth_for_plot(v, 3);
  REQUIRE(s.size()==v.size());
  REQUIRE(s[3] == Approx(10.0/3.0));   // centered avg of {0,10,0}
}
TEST_CASE("decimate_extrema_for_plot keeps endpoints + per-bin min/max", "[live]") {
  std::vector<double> x(100), y(100); for (int i=0;i<100;++i){x[i]=i; y[i]=(i==50)?99.0:(double)(i%3);}
  std::vector<double> ox, oy; decimate_extrema_for_plot(x,y,10,ox,oy);
  REQUIRE(ox.front()==0); REQUIRE(ox.back()==99);
  REQUIRE(std::find(oy.begin(),oy.end(),99.0) != oy.end());   // the spike survives
}
TEST_CASE("decimate_for_plot returns input when small", "[live]") {
  std::vector<double> x={0,1,2}, y={3,4,5}, ox, oy; decimate_for_plot(x,y,10,ox,oy);
  REQUIRE(ox==x); REQUIRE(oy==y);
}
```

- [ ] **Step 2: Run to verify they fail.**

- [ ] **Step 3: Implement** `Display.{h,cpp}` (settings + `apply_software_filters` per Global Constraints, reusing P5a) and `PlotDecimate.{h,cpp}` (the 5 helpers per Global Constraints; `smooth_for_plot` = edge-pad + moving average; `endpoint_indices`/`extrema_bin_edges` = the numpy int-linspace formulas; the two decimators).

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/Display.h core/src/dsp/Display.cpp core/include/ads1292/view/PlotDecimate.h core/src/view/PlotDecimate.cpp core/CMakeLists.txt tests/cpp/test_display_filters.cpp tests/cpp/test_plot_decimate.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5d display filters + plot decimation helpers"
```

---

### Task 2: build_live_render_frame (portable)

**Files:**
- Create: `core/include/ads1292/view/LiveRender.h`, `core/src/view/LiveRender.cpp`.
- Modify: `core/include/ads1292/dsp/EcgReview.h` + `core/src/dsp/EcgReview.cpp` (add the `prefiltered` param to `detect_r_peaks`).
- Modify: `core/CMakeLists.txt`; Create `tests/cpp/test_live_render.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: P5a `bandpass`, P5b `detect_r_peaks`(+prefiltered)/`heart_rate_summary`/`HeartRateSummary`, P5c `estimate_realtime_snr`/`SignalNoiseEstimate`, Task 1 `apply_software_filters`/`smooth_for_plot`/`decimate_extrema_for_plot`/`decimate_for_plot`.
- Produces (namespace `ads1292::view`):
  - `struct LiveRenderFrame { std::string source; double left, right; std::vector<double> visible_x, visible_ecg, visible_ecg_plot, visible_resp_plot, visible_status; std::vector<int> peaks; std::vector<double> peaks_x, peaks_y, plot_ecg_x, plot_ecg, plot_resp_x, plot_resp, plot_status_x, plot_status; ads1292::dsp::HeartRateSummary heart_rate; ads1292::dsp::SignalNoiseEstimate snr; bool valid; };`
  - `LiveRenderFrame build_live_render_frame(const std::vector<int>& indices, const std::vector<double>& ch1, const std::vector<double>& ch2, const std::vector<int>& status, const ads1292::dsp::EcgDisplaySettings& display_settings, const ads1292::dsp::SoftwareFilterSettings& filter_settings, const std::string& source, double sample_rate_hz, int smoothing_window, int max_render_points, bool ecg_inverted);` (returns `frame.valid=false` for the `none` cases)

- [ ] **Step 1: Write the failing test** (synthetic clean ECG window → filter+peaks+HR+SNR; contact gating)

```cpp
// tests/cpp/test_live_render.cpp
#include "catch.hpp"
#include "ads1292/view/LiveRender.h"
#include <cmath>
using namespace ads1292::view; using namespace ads1292::dsp;
namespace {
// 6 s @ 500 Hz synthetic ECG-ish on ch2 (Gaussian R-peaks ~72 bpm), flat-ish ch1
void make_window(std::vector<int>& idx, std::vector<double>& ch1, std::vector<double>& ch2, std::vector<int>& st) {
  const int n=3000; const double sr=500.0;
  for (int i=0;i<n;++i){ idx.push_back(i); ch1.push_back(0.0); st.push_back(0);
    double t=i/sr, v=0.0; for(double bt=0.2; bt<6.0; bt+=60.0/72.0){ double d=t-bt; v+=200.0*std::exp(-(d*d)/(2*0.01*0.01)); }
    ch2.push_back(v); }
}
}
TEST_CASE("build_live_render_frame: clean window detects peaks + HR + SNR", "[live]") {
  std::vector<int> idx, st; std::vector<double> ch1, ch2; make_window(idx,ch1,ch2,st);
  EcgDisplaySettings ds; SoftwareFilterSettings fs;  // window 8s, no filters
  auto f = build_live_render_frame(idx,ch1,ch2,st,ds,fs,"CH2",500.0,5,2000,false);
  REQUIRE(f.valid);
  REQUIRE(f.peaks.size() >= 5);              // ~7 beats in 6 s
  REQUIRE(f.heart_rate.median_bpm > 40.0);
  REQUIRE(f.snr.valid);
  REQUIRE(f.plot_ecg.size() <= 2000);
}
TEST_CASE("build_live_render_frame: lead-off window detects no peaks", "[live]") {
  std::vector<int> idx, st; std::vector<double> ch1, ch2; make_window(idx,ch1,ch2,st);
  for (auto& s : st) s = 0x0F;               // all lead-off
  auto f = build_live_render_frame(idx,ch1,ch2,st,EcgDisplaySettings{},SoftwareFilterSettings{},"CH2",500.0,5,2000,false);
  REQUIRE(f.valid);
  REQUIRE(f.peaks.empty());                  // contact gate blocks detection
}
TEST_CASE("build_live_render_frame: bad sr returns invalid", "[live]") {
  std::vector<int> idx={0}; std::vector<double> c={0.0}; std::vector<int> st={0};
  auto f = build_live_render_frame(idx,c,c,st,EcgDisplaySettings{},SoftwareFilterSettings{},"CH2",0.0,5,2000,false);
  REQUIRE_FALSE(f.valid);
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `detect_r_peaks` prefiltered param (EcgReview), then `build_live_render_frame` per the Global Constraints (tail extraction, display_signal_values with gain/invert, smoothing, the contact_ok/ecg_has_signal/min-duration gate, peaks/HR/SNR, decimation). `mean(status==0)` = fraction of status entries equal to 0. `ptp` = max-min.

- [ ] **Step 4: Wire CMake, build, run.** Iterate until the 3 cases pass.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/view/LiveRender.h core/src/view/LiveRender.cpp core/include/ads1292/dsp/EcgReview.h core/src/dsp/EcgReview.cpp core/CMakeLists.txt tests/cpp/test_live_render.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5d build_live_render_frame (filter+smooth+gated peaks+HR+SNR) portable"
```

---

### Task 3: LiveScope renders the frame + R-peak markers

**Files:**
- Modify: `gui/include/ads1292/gui/IWaveformPlot.h` (add `setMarkers`), `gui/src/QCustomPlotWaveform.cpp` (+ its header — implement the scatter graph).
- Modify: `gui/src/LiveScope.{h,cpp}` — hold raw rolling buffers (`std::deque<double> ch1_, ch2_; std::deque<int> status_, indices_`), `SoftwareFilterSettings` + `EcgDisplaySettings`, and render via `build_live_render_frame`.
- Modify: `tests/cpp/test_gui_smoke.cpp` (LiveScope filter smoke).

**Interfaces:**
- `IWaveformPlot`: add `virtual void setMarkers(int graphIndex, const std::vector<double>& x, const std::vector<double>& y) = 0;` (R-peak scatter overlay on the ECG plot). `QCustomPlotWaveform` implements it as a dedicated scatter graph (no line, `ssCircle`/`ssCross`), behind the SAME GPL isolation (only the .cpp includes qcustomplot.h).
- `LiveScope`: `void pushStreamSample(const ads1292::StreamSample& s)` now appends to the raw deques (cap at `(int)(window_seconds*sr)+2`, default sr 500); `void setFilterSettings(const SoftwareFilterSettings&)`; `void setWindowSeconds(double)`; `const LiveRenderFrame& lastFrame() const`; `void refresh()` builds the frame via `build_live_render_frame` and renders: ECG plot graph0 = `(plot_ecg_x, plot_ecg)`, markers = `(peaks_x, peaks_y)`; resp plot graph0 = `(plot_resp_x, plot_resp)`.

- [ ] **Step 1: Write the failing LiveScope smoke** (append, using `ensureApp()`)

```cpp
TEST_CASE("LiveScope renders a filtered frame with R-peak markers", "[gui]") {
  ensureApp();
  ads1292::gui::LiveScope scope;
  for (int i=0;i<3000;++i){ ads1292::StreamSample s; s.ch2 = (i%417<5)?300:0; s.ch1=0; s.status_byte=0; scope.pushStreamSample(s); }
  ads1292::dsp::SoftwareFilterSettings fs; fs.bandpass_enabled = true;
  scope.setFilterSettings(fs);
  scope.refresh();
  REQUIRE(scope.lastFrame().valid);            // frame built, no crash
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** the `setMarkers` abstraction + QCustomPlotWaveform scatter graph (preserve GPL isolation — only QCustomPlotWaveform.cpp includes qcustomplot.h), and restructure LiveScope to hold raw deques + settings and render `build_live_render_frame`. Keep the parent-aware ownership from P4.

- [ ] **Step 4: Build + `QT_QPA_PLATFORM=offscreen ctest`.** The LiveScope smoke + all prior pass. Verify GPL isolation: `grep -rn '#include.*qcustomplot.h' gui/` shows ONLY `gui/src/QCustomPlotWaveform.cpp`.

- [ ] **Step 5: Commit**

```bash
git add gui/include/ads1292/gui/IWaveformPlot.h gui/include/ads1292/gui/QCustomPlotWaveform.h gui/src/QCustomPlotWaveform.cpp gui/include/ads1292/gui/LiveScope.h gui/src/LiveScope.cpp tests/cpp/test_gui_smoke.cpp
git commit -m "feat: P5d LiveScope renders live frame + R-peak markers"
```

---

### Task 4: MainWindow filter controls + SNR/HR strip

**Files:**
- Modify: `gui/src/MainWindow.{h,cpp}` — make the four "(P5)" filter checkboxes live (toggle a `SoftwareFilterSettings`, push to LiveScope), add a live SNR + HR readout (extend StatusPanel or add a strip), and wire the tick to update them from `LiveScope::lastFrame()`.
- Modify: `gui/src/StatusPanel.{h,cpp}` (or add labels) for the SNR (dB) + live HR (bpm) readout.
- Modify: `tests/cpp/test_gui_smoke.cpp` (MainWindow filter-toggle smoke).

**Interfaces:**
- MainWindow holds a `SoftwareFilterSettings filter_`; the four checkboxes (HP/Notch/LP/QRS) are ENABLED (remove the P5 disabled placeholder + tooltip) and on toggle update `filter_` (QRS↔bandpass_enabled, etc.) and call `scope_->setFilterSettings(filter_)`. The tick reads `scope_->lastFrame()` and updates a SNR label (`snr.snr_db`, show "—" when `!snr.valid`) + a live-HR label (`heart_rate.median_bpm`).
- StatusPanel: add `void updateLive(double snr_db, bool snr_valid, double hr_bpm)` (or fold into `GuiState`).

- [ ] **Step 1: Write the failing MainWindow smoke** (append, `ensureApp()`)

```cpp
TEST_CASE("MainWindow filter toggles + SNR strip update without crash", "[gui]") {
  ensureApp();
  ads1292::gui::MainWindow win;
  int shown = win.runSimulatorToCompletion(8);   // P4 helper: drains the simulator
  REQUIRE(shown == 112);                          // 8*14 (regression: P4 path intact)
  win.setDisplayFilterForTest(/*qrs=*/true);      // toggles bandpass + refreshes
  REQUIRE(win.liveSnrDbForTest() == win.liveSnrDbForTest());  // not NaN-poisoned (self-equal)
}
```
(Add the two tiny test hooks `setDisplayFilterForTest(bool)` and `double liveSnrDbForTest() const` to MainWindow so the headless test can exercise the filter+SNR path without simulating clicks.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** the live filter checkboxes (enable + wire to `filter_` + `scope_->setFilterSettings`), the SNR + HR readout (StatusPanel labels updated from `lastFrame()`), and the two test hooks. Keep the P4 `runSimulatorToCompletion` + `--smoke` behavior intact.

- [ ] **Step 4: Build + `QT_QPA_PLATFORM=offscreen ctest`** (MainWindow smoke + all prior pass) + `QT_QPA_PLATFORM=offscreen ./build/gui/ads1292_gui --smoke; echo exit=$?` prints `exit=0`. Verify GPL isolation grep unchanged.

- [ ] **Step 5: Commit**

```bash
git add gui/src/MainWindow.h gui/src/MainWindow.cpp gui/include/ads1292/gui/StatusPanel.h gui/src/StatusPanel.cpp tests/cpp/test_gui_smoke.cpp
git commit -m "feat: P5d MainWindow live display-filter controls + SNR/HR readout"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P5 live-GUI backfill scope):
- display filters (HP/Notch/LP/QRS) wired live → Tasks 1,3,4 ✓
- real-time SNR readout → Tasks 2,4 ✓
- live R-peak overlay + HR + smoothing + contact gating (build_live_render_frame) → Tasks 2,3 ✓
- the four "(P5)" placeholder checkboxes become live → Task 4 ✓

**2. Placeholder scan:** The portable algorithms (apply_software_filters, smooth_for_plot, decimate_*, build_live_render_frame) are spelled out concretely in the Global Constraints; every test body + interface signature is concrete. No golden fixtures exist for live render (verified — the P-1 freeze has no live/plots dir), so unit tests use hand-computed/oracle-derived expectations and constructed windows; this is called out explicitly, not a placeholder.

**3. Type consistency:** `EcgDisplaySettings`/`SoftwareFilterSettings`/`apply_software_filters` (Task 1) used by Task 2's `build_live_render_frame` and Task 3/4's GUI; `smooth_for_plot`/`decimate_*` (Task 1) used by Task 2; `detect_r_peaks`'s new `prefiltered` param (Task 2) matches the Python kwarg; `LiveRenderFrame` (Task 2) rendered by Task 3 LiveScope + read by Task 4 MainWindow; `setMarkers` (Task 3) added to the P4 IWaveformPlot. `HeartRateSummary`/`SignalNoiseEstimate` are the P5b/P5c structs.

**Risk notes for the executor:**
- LiveScope is being RESTRUCTURED from the P4 RollingTrace model to raw deques + `build_live_render_frame`. The P4 RollingTrace may become unused by LiveScope (keep it if other code uses it; otherwise it's dead — note in the report, don't delete without checking).
- GPL isolation MUST survive the `setMarkers` addition — only `QCustomPlotWaveform.cpp` includes `qcustomplot.h`. The scatter graph is created there.
- The smoke's `runSimulatorToCompletion(8)==112` is a regression guard that the P4 simulator path still works after the LiveScope restructure.
- No golden parity here — but `apply_software_filters`'s `bandpass_enabled` branch is tested to EQUAL `bandpass()` (already golden), so the filter chain inherits P5a's verified correctness.
- Keep everything `double`; the GUI widget tests run under `QT_QPA_PLATFORM=offscreen` and reuse `ensureApp()`.
