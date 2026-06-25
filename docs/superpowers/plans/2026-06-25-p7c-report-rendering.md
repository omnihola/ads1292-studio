# P7c: Report Rendering (HTML + ECG/PQRST/spectrum PNG) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate a recording-review report — a styled HTML summary (quality/HR/PQRST/gate/calibration/metadata/events tables) plus ECG-with-R-peaks, PQRST average-beat, and power-spectrum PNG plots — by porting `report.py`'s `_html` (text, parity-tested) and rendering the plots via the existing GPL-isolated QCustomPlot backends offscreen (PNG, smoke-tested).

**Architecture:** A portable `build_review_html(...)` (Qt-free, text) reproduces `report.py::_html`'s structure + values from the verified metrics/gate/calibration/metadata/events; the 3 PNGs are rendered by extending the P4/P6 `IWaveformPlot`/`IXYPlot` backends with `savePng` (QCustomPlot::savePng, offscreen) and feeding them the verified `build_review_render_frame` (ECG+peaks) / `pqrst_review` / `build_spectrum_analysis` data. `export_review_report(...)` (gui-linked) assembles HTML + 3 PNGs. Parity: HTML is structure/value-parity-tested vs the oracle; PNGs are offscreen smoke (file written, non-trivial size). The protocol-segment tables (`analyze_protocol_segments`/segment-gate — not ported) are DEFERRED; the report renders without a protocol (the common path).

**Tech Stack:** C++17, CMake, Catch2; Qt Widgets + the GPL-isolated `QCustomPlotWaveform`/`QCustomPlotXY` (`savePng`). Reuses P5b/c (pqrst/spectrum), P6 (build_review_render_frame), P5c (compute_quality_metrics/quality_label), P7a (evaluate_quality_gate), P7b-1/2 (Calibration/SessionMetadata/EventMarker). Oracle: `report.py` (`_html`, `export_review_report`, `_write_ecg_png`/`_write_pqrst_png`/`_write_spectrum_png`).

## Global Constraints

- **C++17**; `build_review_html` is pure portable C++ (stdlib only, no Qt). The PNG rendering + `export_review_report` are gui-linked (Qt). GPL isolation: ONLY `QCustomPlotWaveform.cpp` + `QCustomPlotXY.cpp` may include `qcustomplot.h` (preserve).
- **Layering**: `build_review_html` in `io/` or `core/report` (no Qt); PNG render + assembly in `gui/`. Reuses verified P5/P6/P7 code.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`. GUI/PNG tests run under `QT_QPA_PLATFORM=offscreen`; reuse `ensureApp()`.
- **Parity gates:** HTML = the `_html` table structure + the formatted values (assert the HTML string contains the right `<tr><th>...</th><td>...</td></tr>` rows for the metrics/gate/calibration). PNG = offscreen smoke (savePng returns true, the file exists + is > a few hundred bytes). No pixel parity (matplotlib ≠ QCustomPlot).
- **`build_review_html` (report.py::_html, EXACT structure for the non-deferred sections):** main metrics table rows (in order, with these exact labels + value formats): `("Quality", quality_label)`, `("ECG source", ecg_source)`, `("Samples", sample_count)`, `("Duration", "{:.2f} s")`, `("Contact OK", "{:.2f}%")`, `("Lead-off bad samples", lead_off_bad_samples)`, `("R peaks", r_peaks)`, `("Median HR", "{:.1f} bpm")`, `("HR range", "{min:.1f}-{max:.1f} bpm")`, `("QRS clear", bool→"true"/"false")`, `("P wave", p_tentative?"tentative":"not reliable")`, `("T wave", t_tentative?"tentative":"not reliable")`, `("Baseline drift", "{:.1f} counts")`, `("Noise RMS", "{:.1f} counts")`, `("Peak-to-peak", "{:.1f} counts")`, `("CH1 score", "{:.2f}")`, `("CH2 score", "{:.2f}")`. Each row = `<tr><th>{html-escape(k)}</th><td>{html-escape(v)}</td></tr>`. Optional sections (when provided): metadata table (Session ID/Subject ID/Electrode/Montage/Operator/Notes — note `bool→"True"/"False"` capitalization in Python's `str(bool)` for QRS clear: Python `str(True)`=="True" — match that), events table, calibration table (`Label`, `Reference voltage "{vref_mv/1000:.3f} V"`, `PGA gain "{:g}"`, `ADC bits`, `ECG scale "{microvolts_per_count:.4f} uV/count"`), quality-gate table (`Status`=gate.label, `Failures`= join("; ") or "None"). Wrap in the `<!doctype html>...<style>...` document with `<title>{escape(title)}</title>` + `<img>` refs to the 3 PNG names. **Match Python's `str(bool)` → "True"/"False"** (capital) for QRS clear. **DEFER** the protocol + segment-metrics + segment-gate sections (analyze_protocol_segments not ported) — emit them only if you port that later; for now omit (render works without a protocol).
- **HTML escaping**: replicate Python's `html.escape` (at minimum `& < > " '` → `&amp; &lt; &gt; &quot; &#x27;`).
- **PNG rendering** (smoke parity only): ECG PNG = `build_review_render_frame(samples,...)` → a `QCustomPlotWaveform` (ECG plot_ecg + peak markers, resp plot_resp) → `savePng`. PQRST PNG = `pqrst_review` → a `QCustomPlotXY` line (time_ms vs average_beat) → savePng. Spectrum PNG = `build_spectrum_analysis` → a `QCustomPlotXY` (FFT line + histogram bars) → savePng. The data is all verified; only the savePng wiring is new.

## File Structure

```
io/include/ads1292/io/ReviewHtml.h     # build_review_html (Qt-free, text)
io/src/ReviewHtml.cpp
gui/include/ads1292/gui/IWaveformPlot.h # MODIFY: add savePng
gui/include/ads1292/gui/IXYPlot.h       # MODIFY: add savePng
gui/src/QCustomPlotWaveform.cpp         # MODIFY: implement savePng
gui/src/QCustomPlotXY.cpp               # MODIFY: implement savePng
gui/src/ReportExport.{h,cpp}            # export_review_report (gui-linked: HTML + 3 PNGs)
tests/cpp/test_review_html.cpp
tests/cpp/test_gui_smoke.cpp            # MODIFY: PNG render + report-export smoke
```

---

### Task 1: build_review_html (Qt-free HTML builder)

**Files:** Create `io/include/ads1292/io/ReviewHtml.h` + `io/src/ReviewHtml.cpp`; Modify io CMake; Create `tests/cpp/test_review_html.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: `QualityMetrics`/`quality_label` (P5c), `QualityGateResult` (P7a), `Calibration` (P7b-2), `SessionMetadata` (P7b-1), `EventMarker` (model).
- Produces (namespace `ads1292::io`): `struct ReviewHtmlInputs { std::string title; ads1292::dsp::QualityMetrics metrics; ads1292::dsp::QualityGateResult gate; ads1292::Calibration calibration; std::optional<ads1292::SessionMetadata> metadata; std::vector<ads1292::EventMarker> events; std::string ecg_png_name, pqrst_png_name, spectrum_png_name; };` and `std::string build_review_html(const ReviewHtmlInputs& in);`.

- [ ] **Step 1: Write the failing test** (assert the HTML contains the right rows/values)

```cpp
// tests/cpp/test_review_html.cpp
#include "catch.hpp"
#include "ads1292/io/ReviewHtml.h"
using namespace ads1292;
TEST_CASE("build_review_html renders the metrics + gate + calibration tables", "[report]") {
  io::ReviewHtmlInputs in;
  in.title = "Test Report";
  in.metrics.quality_label_set("Good ECG/QRS");  // OR set fields then call quality_label
  in.metrics.ecg_source = "CH2"; in.metrics.sample_count = 2500; in.metrics.duration_seconds = 4.998;
  in.metrics.contact_ok_percent = 100.0; in.metrics.r_peaks = 6; in.metrics.hr_median_bpm = 72.0;
  in.metrics.hr_min_bpm = 71.0; in.metrics.hr_max_bpm = 73.0; in.metrics.qrs_clear = true;
  in.metrics.baseline_drift_counts = 1.0; in.metrics.noise_rms_counts = 6.3; in.metrics.peak_to_peak_counts = 715.0;
  in.metrics.score_ch1 = 0.0; in.metrics.score_ch2 = 100.39;
  in.gate.passed = true;  // label() -> "Pass"
  in.calibration = Calibration{};   // defaults
  in.ecg_png_name = "r-ecg.png"; in.pqrst_png_name = "r-pqrst.png"; in.spectrum_png_name = "r-spectrum.png";
  auto html = io::build_review_html(in);
  REQUIRE(html.find("<!doctype html>") != std::string::npos);
  REQUIRE(html.find("<title>Test Report</title>") != std::string::npos);
  REQUIRE(html.find("<th>ECG source</th><td>CH2</td>") != std::string::npos);
  REQUIRE(html.find("<th>R peaks</th><td>6</td>") != std::string::npos);
  REQUIRE(html.find("<th>Median HR</th><td>72.0 bpm</td>") != std::string::npos);
  REQUIRE(html.find("<th>QRS clear</th><td>True</td>") != std::string::npos);   // Python str(True)
  REQUIRE(html.find("<h2>Quality Gate</h2>") != std::string::npos);
  REQUIRE(html.find("<th>Status</th><td>Pass</td>") != std::string::npos);
  REQUIRE(html.find("<h2>Calibration</h2>") != std::string::npos);
  REQUIRE(html.find("r-ecg.png") != std::string::npos);
}
```
(Adapt the `QualityMetrics` field setup to the real struct — if `quality_label` is a free function, set the fields so `quality_label(metrics)` returns "Good ECG/QRS", or store the label in the inputs. Confirm the metrics field names.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `build_review_html` per the Global Constraints (the metrics table rows with exact labels/formats, optional metadata/events tables, calibration + gate tables, the styled HTML doc + 3 `<img>` refs). Use a file-local `escape()` (Python html.escape semantics: `& < > " '`). `quality_label` via `ads1292::dsp::quality_label(metrics)`. `bool→"True"/"False"` (capital, matching Python `str(bool)`). DEFER the protocol/segment sections.

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit** `git commit -m "feat: P7c build_review_html (Qt-free report HTML)"`

---

### Task 2: savePng on the plot backends

**Files:** Modify `gui/include/ads1292/gui/IWaveformPlot.h` + `IXYPlot.h` (add `savePng`); Modify `gui/src/QCustomPlotWaveform.cpp` + `QCustomPlotXY.cpp` (implement). Modify `tests/cpp/test_gui_smoke.cpp` (savePng smoke).

**Interfaces:**
- `IWaveformPlot`/`IXYPlot`: add `virtual bool savePng(const std::string& path, int width = 1000, int height = 360) = 0;` (returns true on success). Implemented in the two backends via `m_plot->savePng(QString::fromStdString(path), width, height)` (the ONLY files that include qcustomplot.h). Doc-comments only in the headers; NO qcustomplot.h leak.

- [ ] **Step 1: Write the failing savePng smoke** (offscreen, ensureApp)

```cpp
TEST_CASE("QCustomPlotWaveform + QCustomPlotXY savePng write files offscreen", "[gui]") {
  ensureApp();
  auto wf = std::make_unique<ads1292::gui::QCustomPlotWaveform>();
  wf->setData(0, {0,1,2,3}, {0,1,4,9}); wf->setAutoscale(true);
  auto wpath = (std::filesystem::temp_directory_path()/"p7c_wave.png").string();
  REQUIRE(wf->savePng(wpath, 800, 300));
  REQUIRE(std::filesystem::file_size(wpath) > 200);
  ads1292::gui::QCustomPlotXY xy;
  xy.setLine({0,1,2,3},{1,2,1,2}); xy.setAutoscale(true);
  auto xpath = (std::filesystem::temp_directory_path()/"p7c_xy.png").string();
  REQUIRE(xy.savePng(xpath, 800, 300));
  REQUIRE(std::filesystem::file_size(xpath) > 200);
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `savePng` on both abstractions + backends (call `m_plot->replot()` then `m_plot->savePng(...)`; return the bool). Preserve GPL isolation (only the two .cpp include qcustomplot.h).

- [ ] **Step 4: Build + `QT_QPA_PLATFORM=offscreen ctest`.** Smoke passes; `grep -rn '#include.*qcustomplot.h' gui/` still only the two backend .cpp.

- [ ] **Step 5: Commit** `git commit -m "feat: P7c savePng on IWaveformPlot/IXYPlot backends"`

---

### Task 3: export_review_report (assembly)

**Files:** Create `gui/include/ads1292/gui/ReportExport.h` + `gui/src/ReportExport.cpp`; Modify gui CMake; Modify `tests/cpp/test_gui_smoke.cpp` (report-export smoke). Optionally add a `--export-report <csv> <outdir>` flag to `gui/src/main.cpp`.

**Interfaces:**
- Produces (namespace `ads1292::gui`): `struct ReportExportResult { std::string html_path, ecg_png_path, pqrst_png_path, spectrum_png_path; };` and `ReportExportResult export_review_report(const std::vector<ads1292::StreamSample>& samples, const std::string& out_dir, const std::string& title = "ADS1292 Studio Review", double sample_rate_hz = 500.0, const std::string& source = "Auto", const std::optional<ads1292::SessionMetadata>& metadata = std::nullopt, const std::vector<ads1292::EventMarker>& events = {}, const ads1292::Calibration& calibration = {});`
- Logic: `create_directories(out_dir)`; `metrics = compute_quality_metrics(samples, sr, source)`; `gate = evaluate_quality_gate(metrics)`; pick deterministic file names (NO timestamp — use the slug + a fixed name, OR accept a stamp arg; the GUI passes a stamp); render the 3 PNGs (ECG via build_review_render_frame + QCustomPlotWaveform.savePng; PQRST via pqrst_review on the chosen channel + QCustomPlotXY.savePng; spectrum via build_spectrum_analysis + QCustomPlotXY.savePng); write the HTML via `build_review_html(...)` with the 3 PNG basenames. Return the paths.

- [ ] **Step 1: Write the failing report-export smoke** (offscreen, ensureApp)

```cpp
TEST_CASE("export_review_report writes HTML + 3 PNGs offscreen", "[gui]") {
  ensureApp();
  std::vector<ads1292::StreamSample> rec;
  for (int i=0;i<3000;++i){ ads1292::StreamSample s; double t=i/500.0,v=0.0; for(double bt=0.2;bt<6.0;bt+=60.0/72.0){double d=t-bt; v+=200.0*std::exp(-(d*d)/(2*0.01*0.01));} s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s);}
  auto out = (std::filesystem::temp_directory_path()/"p7c_report").string();
  auto r = ads1292::gui::export_review_report(rec, out, "Smoke");
  REQUIRE(std::filesystem::exists(r.html_path));
  REQUIRE(std::filesystem::exists(r.ecg_png_path));
  REQUIRE(std::filesystem::exists(r.pqrst_png_path));
  REQUIRE(std::filesystem::exists(r.spectrum_png_path));
  REQUIRE(std::filesystem::file_size(r.ecg_png_path) > 200);
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `export_review_report` (gui-linked; reuse build_review_render_frame + pqrst_review + build_spectrum_analysis + build_review_html + the savePng backends). Add it to `ads1292_gui_lib`. Optionally wire `--export-report <csv> <outdir>` in `main.cpp` (read_recording_csv → export_review_report → print the paths → exit 0).

- [ ] **Step 4: Build + `QT_QPA_PLATFORM=offscreen ctest`** (the report-export smoke + all prior pass). If `--export-report` added: `QT_QPA_PLATFORM=offscreen ./build/gui/ads1292_gui --export-report <a.csv> <dir>` writes the artifacts. GPL grep unchanged.

- [ ] **Step 5: Commit** `git commit -m "feat: P7c export_review_report (HTML + ECG/PQRST/spectrum PNGs)"`

---

## Self-Review

**1. Spec coverage:** HTML report (metrics/gate/calibration/metadata/events tables) → Task 1 ✓; PNG rendering (savePng) → Task 2 ✓; export_review_report assembly (HTML + 3 PNGs) → Task 3 ✓. Protocol + segment-metrics sections (analyze_protocol_segments not ported) → DEFERRED (documented). PNG pixel-parity is out of scope (smoke only — matplotlib ≠ QCustomPlot).

**2. Placeholder scan:** the HTML table structure + value formats + escaping are spelled out; the test bodies are concrete; the PNG data sources (build_review_render_frame/pqrst_review/build_spectrum_analysis) are verified. Parity is HTML-structure (Task 1) + offscreen PNG smoke (Tasks 2-3).

**3. Type consistency:** `build_review_html` (Task 1) consumes the verified `QualityMetrics`/`QualityGateResult`/`Calibration`/`SessionMetadata`/`EventMarker`; `savePng` (Task 2) added to `IWaveformPlot`/`IXYPlot`; `export_review_report` (Task 3) composes Task 1 + Task 2 + build_review_render_frame (P6) + pqrst_review (P5b) + build_spectrum_analysis (P5c).

**Risk notes for the executor:**
- HTML parity is on STRUCTURE + VALUES (the `<tr><th>k</th><td>v</td></tr>` rows), not byte-identical whitespace. `str(bool)` → "True"/"False" (capital) for QRS clear — match Python.
- GPL isolation: `savePng` is implemented ONLY in the two backend .cpp; the headers add the pure-virtual decl (no qcustomplot.h).
- PNGs are offscreen smoke (file written + non-trivial size); NO pixel parity.
- `build_review_html` is Qt-FREE (text in io); the PNG render + assembly are gui-linked.
- DEFER the protocol/segment sections (analyze_protocol_segments + SegmentMetrics + evaluate_segment_quality_gates not ported) — render the report without them.
- The report file names: the Python uses a `datetime.now()` stamp (non-deterministic). For the C++ assembly use deterministic names (slug-based) OR accept a stamp arg; the smoke just checks the returned paths exist.
- Confirm the `QualityMetrics` field names + whether `quality_label` is a method or free function before writing Task 1's test.
