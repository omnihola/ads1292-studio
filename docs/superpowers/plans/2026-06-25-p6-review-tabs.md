# P6: Review Tabs (quality / PQRST / spectrum / event log / info) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the recording-review UI — load a saved recording (CSV/HDF5) and show its waveform + R-peaks, quality summary, PQRST average beat, power spectrum + amplitude histogram, event log, and recording info — by porting `build_review_render_frame` as a portable core function and rendering it through new review panels in a tabbed MainWindow.

**Architecture:** Port `build_review_render_frame` (full-recording analysis: filter/smooth/decimate + `review_channels` + `compute_quality_metrics` + `pqrst_review`) as a PORTABLE core function (`core/view`, pure C++17). Add a generic GPL-isolated XY/bar plot backend (a sibling of P4's `QCustomPlotWaveform`) for the PQRST line, spectrum line, and histogram bars. The review panels are thin renderers; MainWindow becomes a `QTabWidget` (Live tab wrapping the P4/P5d layout + Review tabs). Reuses the verified P5 DSP and P2 readers; no new golden fixtures (GUI integration), so portable pieces are unit-tested and the GUI is smoke-tested offscreen.

**Tech Stack:** C++17, CMake, Catch2; Qt Widgets + a new GPL-isolated `QCustomPlotXY` backend; P2 `read_recording_csv`/`read_recording_h5`. Oracle: `review_render.py`, `plots.py` (`robust_ylim`), `display.py` (`display_mode_label`), `quality.py` (`quality_label`), `ui_qt/analysis_panels.py` (panel layout).

## Global Constraints

- **C++17**; `core/view` stays pure portable C++ (stdlib only, all `double`, no Qt/OS). GUI uses Qt; GPL isolation: ONLY backend `.cpp` files (`QCustomPlotWaveform.cpp`, the new `QCustomPlotXY.cpp`) may include `qcustomplot.h` — no GUI header references any `QCP*` type or includes `qcustomplot.h`.
- **Layering**: `core/view` depends on `core/dsp` (P5) only. GUI depends on `core` + `io` (the recording readers) + the plot abstractions.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`. Qt widget tests run under `QT_QPA_PLATFORM=offscreen`; reuse the `ensureApp()` guard in `tests/cpp/test_gui_smoke.cpp`.
- **No new golden fixtures** — review render wasn't frozen in P-1. Portable helpers are unit-tested vs hand-computed/oracle-derived values; the DSP they call is already golden-verified (P5). GUI is offscreen smoke-tested.
- **`robust_ylim(values, min_span)` (plots.py):** `size==0` → `(-1.0, 1.0)`; `lo,hi = (size>50) ? percentile(values,[1,99]) : (min,max)`; if `lo==hi` → `lo-=1; hi+=1`; `span=hi-lo`; if `span<min_span` → `center=(hi+lo)/2; lo=center-min_span/2; hi=center+min_span/2`; `pad=max(1.0, 0.15*(hi-lo))`; return `(lo-pad, hi+pad)`. (percentile = the P5c numpy-linear `percentile`.)
- **`quality_label(metrics)` (quality.py):** if `contact_ok_percent<95 || !qrs_clear` → `"Needs review"`; if `r_peaks<5 || hr_median_bpm<=0` → `"Insufficient ECG"`; if `contact_ok_percent>=99 && qrs_clear` → `"Good ECG/QRS"`; else → `"Usable ECG/QRS"`.
- **`display_mode_label(settings, filters)` (display.py):** `n = settings.normalized()`; build `active`: if `filters.bandpass_enabled` → `["QRS"]` else append `"HP"`(if highpass), `"notch"`(if notch), `"LP"`(if lowpass); `filter_text = active.empty() ? "raw" : join(active,"+")`; return `filter_text + " | " + g(n.gain) + "x | " + g(n.time_window_seconds) + "s | " + n.sweep_speed_mm_s + " mm/s"` where `g(x)` = the `%g` format. `EcgDisplaySettings::normalized()` snaps each field to the nearest of the choice tuples in display.py (`DISPLAY_WINDOW_CHOICES`, `DISPLAY_GAIN_CHOICES`, `SWEEP_SPEED_CHOICES` — read the exact tuples from display.py); `nearest_choice(v, choices)` = the choice minimizing `|choice-v|`.
- **`build_review_render_frame(samples, display_settings, filter_settings, source, sr, smoothing_window, max_points, ecg_inverted, min_ecg_span_counts, min_resp_span_counts)` (review_render.py):** if `!finite(sr)||sr<=0` → `sr=500.0`. `full_ch1=[s.ch1]`, `full_ch2=[s.ch2]` (double); `status_values=[s.lead_off_bits()]`. `ecg = display_signal_values(full_ch2, filter_settings, ecg_inverted, display_settings.gain, sr)`; `resp = display_signal_values(full_ch1, filter_settings, /*invert=*/false, /*gain=*/1.0, sr)` (resp UNITY gain, like P5d). `review = review_channels(full_ch1, full_ch2, sr, source)`; `metrics = compute_quality_metrics(samples, sr, source)`; `pqrst_raw = (review.source.channel=="CH2") ? full_ch2 : full_ch1`; `pqrst = pqrst_review(pqrst_raw, review.peaks, sr)`. `x[i]=i/sr`; `display_ecg=smooth_for_plot(ecg, smoothing_window)`, `display_resp=smooth_for_plot(resp, smoothing_window)`; `decimate_extrema_for_plot(x, display_ecg, max_points)`→`(plot_ecg_x, plot_ecg)`; same for resp; `decimate_for_plot(x, status_arr, max_points)`→`(plot_status_x, plot_status)`. `peak_x[k]=review.peaks[k]/sr`; `peak_y[k]=display_ecg[review.peaks[k]]` (the SMOOTHED curve). `x_right=max(1.0, x.empty()?1.0:x.back())`. `ecg_ylim=robust_ylim(display_ecg, min_ecg_span_counts*display_settings.gain)`; `resp_ylim=robust_ylim(display_resp, min_resp_span_counts)`; `status_top=max(1.0, status_arr.empty()?1.0:max(status_arr)+0.5)`; `status_ylim=(-0.5, status_top)`. `mode = display_mode_label(...) + ", display-smoothed"`. `duration_seconds = sample_count/sr` (note: count/sr, NOT (count-1)/sr). Fields per the struct.

## File Structure

```
core/
  include/ads1292/view/ReviewRender.h    # ReviewRenderFrame, build_review_render_frame
  src/view/ReviewRender.cpp
  include/ads1292/view/PlotStats.h        # robust_ylim
  src/view/PlotStats.cpp
  include/ads1292/dsp/Display.h           # MODIFY: add normalized(), display_mode_label, the choice tuples + nearest_choice
  include/ads1292/dsp/QualityMetrics.h    # MODIFY: add quality_label(const QualityMetrics&)
gui/
  include/ads1292/gui/IXYPlot.h           # abstract line/bar plot (no qcustomplot.h)
  include/ads1292/gui/QCustomPlotXY.h     # forward-declares QCustomPlot
  src/QCustomPlotXY.cpp                    # ONLY new file including qcustomplot.h
  src/PqrstPanel.{h,cpp}                   # average-beat line
  src/SpectrumPanel.{h,cpp}                # FFT line + histogram bars
  src/QualityInfoPanel.{h,cpp}             # QualityMetrics text/cards
  src/ReviewEventLogPanel.{h,cpp}          # event/log text
  src/MainWindow.{h,cpp}                   # MODIFY: QTabWidget (Live + Review tabs) + Load CSV/H5
tests/cpp/
  test_review_render.cpp     # build_review_render_frame + robust_ylim + quality_label + display_mode_label
  test_gui_smoke.cpp         # MODIFY: review panels + MainWindow tab/load smoke
```

---

### Task 1: portable review core (frame + robust_ylim + labels)

**Files:**
- Create: `core/include/ads1292/view/ReviewRender.h` + `core/src/view/ReviewRender.cpp`; `core/include/ads1292/view/PlotStats.h` + `core/src/view/PlotStats.cpp`.
- Modify: `core/include/ads1292/dsp/Display.h` + `src/dsp/Display.cpp` (add `EcgDisplaySettings::normalized()` + the choice tuples + `nearest_choice` + `display_mode_label`); `core/include/ads1292/dsp/QualityMetrics.h` + `src/dsp/QualityMetrics.cpp` (add `quality_label`).
- Modify: `core/CMakeLists.txt`; Create `tests/cpp/test_review_render.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: P5 `apply_software_filters`/`smooth_for_plot`/`decimate_*`/`review_channels`/`compute_quality_metrics`/`pqrst_review`/`percentile`, P5d `display_signal_values` logic (re-implement the small `disp*scale` helper locally or expose it).
- Produces:
  - `ads1292::view`: `std::pair<double,double> robust_ylim(const std::vector<double>& values, double min_span);`
  - `ads1292::view`: `struct ReviewRenderFrame { std::string source, mode; int sample_count; double duration_seconds; std::vector<int> status_values; std::vector<double> plot_ecg_x, plot_ecg, plot_resp_x, plot_resp, plot_status_x, plot_status, peak_x, peak_y; double x_right; std::pair<double,double> ecg_ylim, resp_ylim, status_ylim; ads1292::dsp::ChannelChoice review_source; std::vector<int> review_peaks; ads1292::dsp::HeartRateSummary review_hr; ads1292::dsp::PqrstReview pqrst; ads1292::dsp::QualityMetrics metrics; };` and `ReviewRenderFrame build_review_render_frame(const std::vector<ads1292::StreamSample>& samples, const ads1292::dsp::EcgDisplaySettings& display_settings, const ads1292::dsp::SoftwareFilterSettings& filter_settings, const std::string& source, double sample_rate_hz, int smoothing_window, int max_points, bool ecg_inverted, double min_ecg_span_counts, double min_resp_span_counts);`
  - `ads1292::dsp`: `EcgDisplaySettings EcgDisplaySettings::normalized() const;` (or a free `normalized(settings)`), `std::string display_mode_label(const EcgDisplaySettings&, const SoftwareFilterSettings&);`, `std::string quality_label(const QualityMetrics&);`

- [ ] **Step 1: Write the failing tests** (robust_ylim/quality_label/display_mode_label exact cases + a synthetic-recording frame)

```cpp
// tests/cpp/test_review_render.cpp
#include "catch.hpp"
#include "ads1292/view/ReviewRender.h"
#include "ads1292/view/PlotStats.h"
#include "ads1292/dsp/Display.h"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/model/StreamSample.h"
#include <cmath>
using namespace ads1292; using namespace ads1292::view; using namespace ads1292::dsp;

TEST_CASE("robust_ylim: empty -> (-1,1); flat -> padded", "[review]") {
  REQUIRE(robust_ylim({}, 0.0) == std::pair<double,double>{-1.0, 1.0});
  auto [lo, hi] = robust_ylim(std::vector<double>(10, 5.0), 0.0);  // <=50 -> min==max==5 -> 4..6 -> pad max(1,0.3)=1
  REQUIRE(lo == Approx(3.0)); REQUIRE(hi == Approx(7.0));
}
TEST_CASE("quality_label thresholds", "[review]") {
  QualityMetrics m{}; m.contact_ok_percent=100; m.qrs_clear=true; m.r_peaks=6; m.hr_median_bpm=72;
  REQUIRE(quality_label(m) == "Good ECG/QRS");
  m.contact_ok_percent=96; REQUIRE(quality_label(m) == "Usable ECG/QRS");
  m.qrs_clear=false; REQUIRE(quality_label(m) == "Needs review");
  m.qrs_clear=true; m.contact_ok_percent=100; m.r_peaks=3; REQUIRE(quality_label(m) == "Insufficient ECG");
}
TEST_CASE("display_mode_label QRS + raw", "[review]") {
  EcgDisplaySettings ds;  // 8s, 1x, 25 mm/s (already normalized defaults)
  SoftwareFilterSettings qrs; qrs.bandpass_enabled = true;
  REQUIRE(display_mode_label(ds, qrs) == "QRS | 1x | 8s | 25 mm/s");
  REQUIRE(display_mode_label(ds, SoftwareFilterSettings{}) == "raw | 1x | 8s | 25 mm/s");
}
TEST_CASE("build_review_render_frame on a synthetic recording", "[review]") {
  std::vector<StreamSample> samples;
  for (int i=0;i<3000;++i){ StreamSample s; double t=i/500.0, v=0.0;
    for(double bt=0.2; bt<6.0; bt+=60.0/72.0){ double d=t-bt; v+=200.0*std::exp(-(d*d)/(2*0.01*0.01)); }
    s.ch2=(int)v; s.ch1=0; s.status_byte=0; samples.push_back(s); }
  auto f = build_review_render_frame(samples, EcgDisplaySettings{}, SoftwareFilterSettings{}, "Auto", 500.0, 5, 5000, false, 50.0, 50.0);
  REQUIRE(f.sample_count == 3000);
  REQUIRE(f.duration_seconds == Approx(6.0));     // count/sr = 3000/500
  REQUIRE(f.review_peaks.size() >= 5);
  REQUIRE(f.metrics.r_peaks == (int)f.review_peaks.size());
  REQUIRE(f.pqrst.average_beat.size() > 0);
  REQUIRE(f.ecg_ylim.second > f.ecg_ylim.first);
}
```

- [ ] **Step 2: Run to verify they fail.**

- [ ] **Step 3: Implement** `robust_ylim` (PlotStats, using P5c `percentile`), `quality_label` (QualityMetrics), `normalized()`+`display_mode_label` (Display — read the exact choice tuples from `display.py`), and `build_review_render_frame` (ReviewRender) per the Global Constraints. Note `duration_seconds = sample_count/sr` (NOT (count-1)/sr — review differs from SNR). Reuse P5 throughout.

- [ ] **Step 4: Wire CMake, build, run.** Iterate until the 4 cases pass.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/view/ReviewRender.h core/src/view/ReviewRender.cpp core/include/ads1292/view/PlotStats.h core/src/view/PlotStats.cpp core/include/ads1292/dsp/Display.h core/src/dsp/Display.cpp core/include/ads1292/dsp/QualityMetrics.h core/src/dsp/QualityMetrics.cpp core/CMakeLists.txt tests/cpp/test_review_render.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P6 build_review_render_frame + robust_ylim + quality/mode labels"
```

---

### Task 2: generic GPL-isolated XY/bar plot backend

**Files:**
- Create: `gui/include/ads1292/gui/IXYPlot.h` (abstract), `gui/include/ads1292/gui/QCustomPlotXY.h` (forward-decl QCustomPlot), `gui/src/QCustomPlotXY.cpp` (the ONLY new file including qcustomplot.h).
- Modify: `gui/CMakeLists.txt` (add QCustomPlotXY.cpp to `ads1292_gui_lib`); Modify `tests/cpp/test_gui_smoke.cpp` (XY plot smoke).

**Interfaces:**
- `IXYPlot` (namespace `ads1292::gui`): `virtual void setLine(const std::vector<double>& x, const std::vector<double>& y) = 0;` `virtual void setBars(const std::vector<double>& centers, const std::vector<double>& heights, double width) = 0;` `virtual void setTitle(const std::string&) = 0;` `virtual void setYRange(double,double)=0;` `virtual void setAutoscale(bool)=0;` `virtual void replotNow()=0;` `virtual QWidget* widget()=0;`. NO qcustomplot.h.
- `QCustomPlotXY : IXYPlot` — owns a forward-declared `QCustomPlot* m_plot`; the .cpp creates a line graph (for setLine) and a `QCPBars` (for setBars). Parent-aware destructor (like P4). ONLY this .cpp includes qcustomplot.h.

- [ ] **Step 1: Write the failing XY smoke** (offscreen, `ensureApp()`)

```cpp
TEST_CASE("QCustomPlotXY line + bars render offscreen", "[gui]") {
  ensureApp();
  ads1292::gui::QCustomPlotXY plot;
  plot.setLine({0,1,2,3}, {0,1,4,9});
  plot.setBars({0.5,1.5,2.5}, {2,5,3}, 1.0);
  plot.setTitle("test"); plot.setAutoscale(true); plot.replotNow();
  REQUIRE(plot.widget() != nullptr);
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `IXYPlot` + `QCustomPlotXY` (line graph + QCPBars, parent-aware ownership). Keep GPL isolation: only `QCustomPlotXY.cpp` includes qcustomplot.h.

- [ ] **Step 4: Build + `QT_QPA_PLATFORM=offscreen ctest`.** The XY smoke + all prior pass. Verify `grep -rn '#include.*qcustomplot.h' gui/` shows ONLY `gui/src/QCustomPlotWaveform.cpp` and `gui/src/QCustomPlotXY.cpp`.

- [ ] **Step 5: Commit**

```bash
git add gui/include/ads1292/gui/IXYPlot.h gui/include/ads1292/gui/QCustomPlotXY.h gui/src/QCustomPlotXY.cpp gui/CMakeLists.txt tests/cpp/test_gui_smoke.cpp
git commit -m "feat: P6 generic GPL-isolated XY/bar plot backend"
```

---

### Task 3: review panels (PQRST, spectrum, quality info, event log)

**Files:**
- Create: `gui/src/PqrstPanel.{h,cpp}`, `gui/src/SpectrumPanel.{h,cpp}`, `gui/src/QualityInfoPanel.{h,cpp}`, `gui/src/ReviewEventLogPanel.{h,cpp}` (headers under `gui/include/ads1292/gui/`).
- Modify: `gui/CMakeLists.txt`; Modify `tests/cpp/test_gui_smoke.cpp` (panel smokes).

**Interfaces:**
- `PqrstPanel : QWidget` — owns an `IXYPlot` (line); `void showFrame(const ads1292::view::ReviewRenderFrame& f)` plots `f.pqrst.average_beat` vs `f.pqrst.time_ms` (empty → clear). 
- `SpectrumPanel : QWidget` — owns two `IXYPlot`s (FFT line + histogram bars); `void showSpectrum(const ads1292::dsp::SpectrumAnalysis& a)` — FFT line `(a.ecg_frequency_hz, a.ecg_power)`; histogram bars: centers = `(edges[i]+edges[i+1])/2`, heights = `counts`, width = `edges[1]-edges[0]`.
- `QualityInfoPanel : QWidget` — a read-only text/label view; `void showMetrics(const ads1292::dsp::QualityMetrics& m)` renders the QualityMetrics fields + `quality_label(m)` (source, sample_count, duration, contact %, lead-off bad, r_peaks, HR median/min/max, qrs/p/t flags, scores, baseline drift, noise rms, p2p, quality label) as labeled text.
- `ReviewEventLogPanel : QWidget` (or QPlainTextEdit subclass) — `void appendLine(const std::string&)`, `void setEvents(const std::vector<ads1292::EventMarker>&)` (render "— events —" then one line per event: index, timestamp, label, notes).

- [ ] **Step 1: Write the failing panel smokes** (offscreen, `ensureApp()`)

```cpp
TEST_CASE("review panels render a frame offscreen", "[gui]") {
  ensureApp();
  // build a synthetic frame via the core (reuse the Task1 synthetic recording)
  std::vector<ads1292::StreamSample> samples; for (int i=0;i<3000;++i){ ads1292::StreamSample s; s.ch2=(i%417<5)?300:0; s.ch1=0; s.status_byte=0; samples.push_back(s);}
  auto f = ads1292::view::build_review_render_frame(samples, {}, {}, "Auto", 500.0, 5, 5000, false, 50.0, 50.0);
  auto spec = ads1292::dsp::build_spectrum_analysis(samples, "CH2", 500.0, 60.0, 48);
  ads1292::gui::PqrstPanel pq; pq.showFrame(f);
  ads1292::gui::SpectrumPanel sp; sp.showSpectrum(spec);
  ads1292::gui::QualityInfoPanel qi; qi.showMetrics(f.metrics);
  ads1292::gui::ReviewEventLogPanel ev; ev.appendLine("loaded"); 
  REQUIRE(pq.isWidgetType()); REQUIRE(sp.isWidgetType()); REQUIRE(qi.isWidgetType());
}
```
(Confirm `build_spectrum_analysis`'s actual signature from `core/include/ads1292/dsp/Spectrum.h` and adapt.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** the four panels (each a thin QWidget rendering from the frame/spectrum/metrics via `IXYPlot` or labels). Lambda connects where needed; no Q_OBJECT unless a signal is required (prefer none). Add the panel sources to `ads1292_gui_lib`.

- [ ] **Step 4: Build + `QT_QPA_PLATFORM=offscreen ctest`** (panel smokes + all prior pass). GPL isolation grep unchanged (only the two backend .cpp).

- [ ] **Step 5: Commit**

```bash
git add gui/include/ads1292/gui/PqrstPanel.h gui/src/PqrstPanel.cpp gui/include/ads1292/gui/SpectrumPanel.h gui/src/SpectrumPanel.cpp gui/include/ads1292/gui/QualityInfoPanel.h gui/src/QualityInfoPanel.cpp gui/include/ads1292/gui/ReviewEventLogPanel.h gui/src/ReviewEventLogPanel.cpp gui/CMakeLists.txt tests/cpp/test_gui_smoke.cpp
git commit -m "feat: P6 review panels (PQRST, spectrum, quality info, event log)"
```

---

### Task 4: tabbed MainWindow + load recording

**Files:**
- Modify: `gui/src/MainWindow.{h,cpp}` — wrap the existing live layout in a "Live ECG" tab inside a `QTabWidget`, add Review tabs (waveform, PQRST, Spectrum, Event Log, Info), and a "Load CSV/H5" toolbar action.
- Modify: `tests/cpp/test_gui_smoke.cpp` (load + render smoke).

**Interfaces:**
- MainWindow gains a `QTabWidget` central widget: tab 0 = the existing live layout (LiveScope + StatusPanel + EventConsole — preserve P4/P5d); tabs for Review waveform (a `QCustomPlotWaveform` or `QCustomPlotXY` showing `plot_ecg`/`plot_resp` + peak markers), PQRST (`PqrstPanel`), Spectrum (`SpectrumPanel`), Event Log (`ReviewEventLogPanel`), Info (`QualityInfoPanel`).
- A "Load Recording" action: reads a path (for the headless test, a method `void loadRecordingForTest(const std::string& csvPath)`); calls `ads1292::io::read_recording_csv(path)` (or `read_recording_h5`), then `build_review_render_frame(samples, ...)` + `build_spectrum_analysis(samples, ...)`, and populates the review panels (waveform setData + markers, `pq.showFrame`, `sp.showSpectrum`, `qi.showMetrics`, event panel).
- Keep `runSimulatorToCompletion`, `--smoke`, the live filter checkboxes, and SNR/HR readout intact.

- [ ] **Step 1: Write the failing load smoke** (offscreen; write a tiny CSV recording via the existing writer, then load it)

```cpp
TEST_CASE("MainWindow loads a recording into the review panels", "[gui]") {
  ensureApp();
  // write a small recording to a temp CSV using the existing io writer, OR craft a minimal CSV the reader accepts
  std::string path = std::string(SCRATCH_DIR) + "/p6_review.csv";   // or a Catch2 tmp path
  // ... write >=1000 stream samples via ads1292::io::write_recording_csv or a hand-written CSV matching the reader ...
  ads1292::gui::MainWindow win;
  REQUIRE(win.runSimulatorToCompletion(4) == 56);          // P4/P5d regression intact
  win.loadRecordingForTest(path);                          // reads + builds review frame + populates panels
  REQUIRE(win.reviewLoadedForTest());                      // a bool the hook sets after a successful load
}
```
(Use whatever recording-write path exists — if `write_recording_csv(samples, path)` is available in `io`, use it to author the fixture; otherwise hand-write a CSV that `read_recording_csv` accepts. Confirm the reader's expected CSV format from `core/.../io/CsvIo.h` / the P2 round-trip test.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** the QTabWidget restructure (Live tab + Review tabs), the load action + `loadRecordingForTest`/`reviewLoadedForTest` hooks, and panel population. Link `ads1292_io` into `ads1292_gui_lib` if not already (for the readers). Preserve GPL isolation + the P4/P5d live behavior.

- [ ] **Step 4: Build + `QT_QPA_PLATFORM=offscreen ctest`** (load smoke + all prior pass), `QT_QPA_PLATFORM=offscreen ./build/gui/ads1292_gui --smoke; echo exit=$?` prints `exit=0`, and `grep -rn '#include.*qcustomplot.h' gui/` shows ONLY the two backend .cpp.

- [ ] **Step 5: Commit**

```bash
git add gui/src/MainWindow.h gui/src/MainWindow.cpp tests/cpp/test_gui_smoke.cpp gui/CMakeLists.txt
git commit -m "feat: P6 tabbed MainWindow + load recording into review panels"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P6 review scope):
- review waveform + R-peaks (build_review_render_frame) → Tasks 1,4 ✓
- quality summary + info → Tasks 1 (quality_label), 3 (QualityInfoPanel) ✓
- PQRST average beat → Tasks 1 (frame.pqrst), 2 (line plot), 3 (PqrstPanel) ✓
- spectrum + histogram → Tasks 2 (line+bars), 3 (SpectrumPanel via build_spectrum_analysis) ✓
- event log → Task 3 (ReviewEventLogPanel) ✓
- tabbed review UI + load recording → Task 4 ✓
- report generation / CLI → **P7** (out of scope here)

**2. Placeholder scan:** The portable algorithms (robust_ylim, quality_label, display_mode_label, build_review_render_frame) are spelled out concretely; every test body + interface signature is concrete. No golden fixtures for review (verified — P-1 has no review-frame dir); unit tests use hand-computed/oracle-derived values + a synthetic recording. KissFFT/QCustomPlot are vendored, not transcribed.

**3. Type consistency:** `ReviewRenderFrame`/`robust_ylim`/`quality_label`/`display_mode_label` (Task 1) consumed by Tasks 3/4; `IXYPlot`/`QCustomPlotXY` (Task 2) used by the PQRST/Spectrum panels (Task 3); the panels (Task 3) assembled by MainWindow (Task 4). `build_spectrum_analysis`/`QualityMetrics`/`ChannelChoice`/`HeartRateSummary`/`PqrstReview` are the P5 structs; `read_recording_csv`/`read_recording_h5` the P2 readers; `EventMarker` the P4 model.

**Risk notes for the executor:**
- GPL isolation now spans TWO backends (`QCustomPlotWaveform.cpp` + `QCustomPlotXY.cpp`) — the grep gate becomes "only those two .cpp include qcustomplot.h". No GUI header may reference `QCP*`.
- `build_review_render_frame` reuses the P5d `display_signal_values` scale logic (ECG gain, resp UNITY gain) — keep resp at gain 1.0, matching the P5d fix.
- `duration_seconds = count/sr` in review (the live/SNR path used (count-1)/sr — do NOT copy that here).
- Task 4 restructures MainWindow into tabs; the P4/P5d live tab + `runSimulatorToCompletion`/`--smoke`/filter-checkboxes/SNR-HR must remain intact (the smoke asserts `runSimulatorToCompletion(4)==56`).
- The load smoke needs a real recording file — author it via the existing `io` writer (confirm `write_recording_csv` exists) or a hand-written CSV the P2 reader accepts; confirm the CSV format from the P2 round-trip test.
- Keep `core/view` pure (no Qt); all DSP reused from P5.
