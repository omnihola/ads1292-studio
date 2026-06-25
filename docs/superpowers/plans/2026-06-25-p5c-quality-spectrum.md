# P5c: Quality Metrics + Spectrum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the Python signal-quality and spectrum analysis on top of the already-verified P5a filters and P5b R-peak/HR/PQRST — `estimate_realtime_snr`, the channel-selection chain (`qrs_like_score`/`choose_ecg_channel`/`review_channels`), `compute_quality_metrics`, and `build_spectrum_analysis` (Hann-windowed rFFT + histogram) — verified against the P-1 frozen golden fixtures (`review/realtime_snr`, `review/quality_metrics`, `spectrum/`).

**Architecture:** Extend `core/dsp` (pure C++17, no Qt) with numpy-faithful primitives (`percentile` linear interpolation, `hanning`, `histogram`) and the quality/spectrum functions. The FFT uses a vendored KissFFT (BSD, double precision) behind a thin `rfft` wrapper. Everything reuses the proven P5a `bandpass` and P5b `detect_r_peaks`/`heart_rate_summary`/`pqrst_review`. Each function is gated by a committed golden fixture.

**Tech Stack:** C++17, CMake, Catch2 + nlohmann/json, vendored KissFFT (double). Oracle: `quality.py` / `signal_processing.py` / `spectrum.py`; golden: `tests/fixtures/golden/{review,spectrum}/`.

## Global Constraints

- **C++17**; `core/dsp` stays pure portable C++ (stdlib + KissFFT only, all `double`, no Qt/OS).
- **Layering**: depends on P5a `core/dsp` filters + P5b `EcgReview` + the `StreamSample` model (`ch1`, `ch2`, `int lead_off_bits() const`). KissFFT vendored under `third_party/kissfft` (BSD — NOT GPL, no isolation needed), compiled with `-Dkiss_fft_scalar=double`.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Parity gates:** SNR/quality floats to abs 1e-9; channel labels + counts exact; spectrum `ecg_frequency_hz` abs 1e-9, `ecg_power` REL 1e-9, `histogram_bin_edges` abs 1e-9, `histogram_counts` EXACT.
- **numpy `percentile(x, q)` (default 'linear'):** sort ascending; `pos = (q/100)*(n-1)`; `lo = floor(pos)`; `frac = pos - lo`; result = `(lo+1 < n) ? x[lo] + frac*(x[lo+1]-x[lo]) : x[lo]`.
- **numpy `hanning(M)`:** `M<=0`→empty; `M==1`→`{1.0}`; else `w[n] = 0.5 - 0.5*cos(2*pi*n/(M-1))`, n=0..M-1.
- **numpy `histogram(v, bins)` (uniform):** `lo=min(v)`, `hi=max(v)`; if `lo==hi`: `lo-=0.5; hi+=0.5`. `edges[i] = lo + i*(hi-lo)/bins` for i=0..bins (so `edges[bins]==hi`). Counts via numpy's uniform-bin algorithm: `norm = bins/(hi-lo)`; for each v: `k = (int)((v-lo)*norm)`; if `k==bins` `k=bins-1`; **float correction**: while `k>0 && v < edges[k]` `--k`; while `k<bins-1 && v >= edges[k+1]` `++k`; `counts[k]++`. (Reproduces numpy's decrement/increment fixups so boundary samples land in the same bin.)
- **numpy `rfftfreq(n, d=1/sr)`:** `f[i] = i*sr/n` for i=0..n/2 (length n//2+1).
- **numpy `rfft(x)`:** via KissFFT `kiss_fftr` (double). For real input length n, returns n//2+1 complex bins. `power[i] = re^2 + im^2` of bin i. (KissFFT and numpy/pocketfft both radix-decompose; for the fixture's n the agreement is well within REL 1e-9 — verify against the golden.)
- **`estimate_realtime_snr(values, sr)`:** `finite = values[isfinite]`; if `finite.size<3` → `{0,0,0,0,(int)size,0,false}`; `centered = finite - median(finite)`; `signal_rms = sqrt(mean(centered^2))`; `noise_rms = _noise_rms(finite)`; `p2p = percentile(finite,95) - percentile(finite,5)`; `duration = sr>0 ? (size-1)/sr : 0`; if `signal_rms<=1e-12` → `{0,signal_rms,noise_rms,p2p,size,duration,false}`; if `noise_rms<=1e-12` → `{80,...,true}`; else `snr_db = 20*log10(signal_rms/noise_rms)`.
- **`_noise_rms(v)`:** if `v.size<3` → 0; `diff = np.diff(v)`; `mad = median(|diff - median(diff)|)`; return `1.4826 * mad / sqrt(2)`.
- **`_baseline_drift(v, sr)`:** if `v.size<2` → 0; `window = max(1, min((int)sr, (int)v.size/2))`; `start = median(v[0..window))`; `end = median(v[size-window..size))`; return `|end-start|`.
- **`qrs_like_score(v, sr)`:** `filtered = bandpass(v, sr)` (P5a defaults); if `filtered.size<100` → 0; `diff = np.diff(filtered - median(filtered))`; `mad = median(|diff - median(diff)|) + 1e-9`; return `percentile(|diff|, 99) / mad`.
- **`_channel_selection_score(v, sr)`:** `peaks = detect_r_peaks(v, sr)`; `summary = heart_rate_summary(peaks, sr)`; `regularity = max(1, summary.valid_rr_count)`; return `qrs_like_score(v, sr) * regularity`.
- **`choose_ecg_channel(ch1, ch2, sr, override)`:** `override = upper(override)`; `score_ch1/ch2 = qrs_like_score`; `select_ch1/ch2 = _channel_selection_score`; `denominator = max(min(select_ch1,select_ch2), 1e-9)`; `confidence = max(select_ch1,select_ch2)/denominator`; if `override∈{CH1,CH2}` → `{override, score_ch1, score_ch2, confidence}`; else `channel = (select_ch2 > select_ch1*1.05) ? "CH2" : "CH1"`.
- **`review_channels(ch1, ch2, sr, source)`:** `choice = choose_ecg_channel(...override=source)`; `selected = (choice.channel=="CH2") ? ch2 : ch1`; `peaks = detect_r_peaks(selected, sr)`; `heart_rate = heart_rate_summary(peaks, sr)`; `pqrst = pqrst_review(selected, peaks, sr)`; return `{choice, peaks, heart_rate, pqrst}`.
- **`compute_quality_metrics(samples, sr, source)`:** if empty → `QualityMetrics(0, 0, "CH1", 0, 0, 0, 0,0,0, false,false,false, 0,0, 0,0,0)`; `ch1=[s.ch1]`, `ch2=[s.ch2]` (as double); `result = review_channels(ch1, ch2, sr, source)`; `ecg = (result.source.channel=="CH2") ? ch2 : ch1`; `lead_bad = count(s.lead_off_bits()!=0)`; `duration = size>1 ? (size-1)/sr : 0`; `baseline_drift = _baseline_drift(ecg, sr)`; `noise_rms = _noise_rms(ecg)`; `p2p = ecg.size ? max(ecg)-min(ecg) : 0`; `contact_ok = 100*(size-lead_bad)/size`; fields per the struct below.
- **`build_spectrum_analysis(samples, source, sr, max_freq=60, bins=48)`:** `values = (source=="CH1") ? [s.ch1] : [s.ch2]` (as double); if `values.size==0` → `{source, {}, {}, {}, {}}`; `(freq, power) = _fft_power(values, sr, max_freq)`; `(counts, edges) = histogram(values, max(1,bins))`. `_fft_power`: if `values.size<2` → `({},{})`; `centered = values - mean(values)`; `window = hanning(size)`; `spectrum = rfft(centered*window)`; `freqs = rfftfreq(size, 1/sr)`; `power = |spectrum|^2`; `keep = freqs <= max_freq`; return filtered (freq,power).

## File Structure

```
third_party/kissfft/            # vendored KissFFT (kiss_fft.{h,c}, kiss_fftr.{h,c}, _kiss_fft_guts.h)
third_party/CMakeLists.txt      # add kissfft STATIC target (-Dkiss_fft_scalar=double)
core/
  include/ads1292/dsp/Stats.h       # percentile, hanning, histogram, mean
  src/dsp/Stats.cpp
  include/ads1292/dsp/Quality.h     # SignalNoiseEstimate, estimate_realtime_snr, _noise_rms, _baseline_drift
  src/dsp/Quality.cpp
  include/ads1292/dsp/ChannelSelect.h  # ChannelChoice, ReviewResult, qrs_like_score, choose_ecg_channel, review_channels
  src/dsp/ChannelSelect.cpp
  include/ads1292/dsp/QualityMetrics.h # QualityMetrics, compute_quality_metrics
  src/dsp/QualityMetrics.cpp
  include/ads1292/dsp/Spectrum.h    # SpectrumAnalysis, build_spectrum_analysis, rfft
  src/dsp/Spectrum.cpp
tests/cpp/
  test_quality_snr.cpp     # realtime_snr fixture
  test_channel_select.cpp  # qrs_like_score / choose_ecg_channel unit
  test_quality_metrics.cpp # quality_metrics fixture
  test_spectrum.cpp        # spectrum fixture
```

---

### Task 1: percentile/noise/baseline + estimate_realtime_snr

**Files:**
- Create: `core/include/ads1292/dsp/Stats.h`, `core/src/dsp/Stats.cpp` (add `percentile`, `mean`; `median`/`std_pop` may be shared — re-declare here or reuse EcgReview's; prefer a small `Stats` with `percentile` + `mean` and reuse EcgReview's `median`).
- Create: `core/include/ads1292/dsp/Quality.h`, `core/src/dsp/Quality.cpp`.
- Modify: `core/CMakeLists.txt`; Create `tests/cpp/test_quality_snr.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (namespace `ads1292::dsp`):
  - `double percentile(const std::vector<double>& x, double q);` (numpy linear)
  - `double mean(const std::vector<double>& x);`
  - `struct SignalNoiseEstimate { double snr_db, signal_rms_counts, noise_rms_counts, peak_to_peak_counts; int sample_count; double duration_seconds; bool valid; };`
  - `double noise_rms(const std::vector<double>& values);`  (the `_noise_rms` helper, exposed for reuse)
  - `double baseline_drift(const std::vector<double>& values, double sample_rate_hz);`
  - `SignalNoiseEstimate estimate_realtime_snr(const std::vector<double>& values, double sample_rate_hz);`
- Consumes: `median` (EcgReview or a local copy), P5a not needed here.

- [ ] **Step 1: Write the failing SNR-parity test**

```cpp
// tests/cpp/test_quality_snr.cpp
#include "catch.hpp"
#include "ads1292/dsp/Quality.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace { json rv(const std::string& n){ std::ifstream in(std::string(FIXTURE_DIR)+"/review/"+n+".json"); json j; in>>j; return j; } }

TEST_CASE("estimate_realtime_snr matches the golden", "[review]") {
  auto f = rv("realtime_snr_clean_72bpm");
  auto v = f.at("input").at("signal").get<std::vector<double>>();
  auto g = estimate_realtime_snr(v, 500.0);
  auto o = f.at("output");
  REQUIRE(g.snr_db == Approx(o.at("snr_db").get<double>()).margin(1e-9));
  REQUIRE(g.signal_rms_counts == Approx(o.at("signal_rms_counts").get<double>()).margin(1e-9));
  REQUIRE(g.noise_rms_counts == Approx(o.at("noise_rms_counts").get<double>()).margin(1e-9));
  REQUIRE(g.peak_to_peak_counts == Approx(o.at("peak_to_peak_counts").get<double>()).margin(1e-9));
  REQUIRE(g.sample_count == o.at("sample_count").get<int>());
  REQUIRE(g.duration_seconds == Approx(o.at("duration_seconds").get<double>()).margin(1e-9));
  REQUIRE(g.valid == o.at("valid").get<bool>());
}
```
(Golden: snr_db=23.073775303708093, signal_rms=95.76507623054161, noise_rms=6.722307792621297, p2p=126.51817234735327, sample_count=2500, duration=4.998, valid=true.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `percentile`/`mean` (Stats), `noise_rms`/`baseline_drift`/`estimate_realtime_snr` (Quality) per the Global Constraints. Reuse `median` (include EcgReview.h or add a local `median`). Filter non-finite first; the early-return branches matter.

- [ ] **Step 4: Wire CMake, build, run.** Iterate until the 7 SNR fields match at 1e-9. If `peak_to_peak` is off, the percentile linear interpolation is wrong; if `noise_rms` is off, the MAD or the `/sqrt(2)` is wrong.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/Stats.h core/src/dsp/Stats.cpp core/include/ads1292/dsp/Quality.h core/src/dsp/Quality.cpp core/CMakeLists.txt tests/cpp/test_quality_snr.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5c percentile/noise_rms/baseline + estimate_realtime_snr vs golden 1e-9"
```

---

### Task 2: channel selection (qrs_like_score / choose_ecg_channel / review_channels)

**Files:**
- Create: `core/include/ads1292/dsp/ChannelSelect.h`, `core/src/dsp/ChannelSelect.cpp`
- Modify: `core/CMakeLists.txt`; Create `tests/cpp/test_channel_select.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: P5a `bandpass`, P5b `detect_r_peaks`/`heart_rate_summary`/`pqrst_review` (+ `PqrstReview`/`HeartRateSummary`), `percentile` (Task 1), `median` (EcgReview).
- Produces (namespace `ads1292::dsp`):
  - `double qrs_like_score(const std::vector<double>& values, double sample_rate_hz);`
  - `struct ChannelChoice { std::string channel; double score_ch1, score_ch2, confidence; };`
  - `ChannelChoice choose_ecg_channel(const std::vector<double>& ch1, const std::vector<double>& ch2, double sample_rate_hz, const std::string& override_source);`
  - `struct ReviewResult { ChannelChoice source; std::vector<int> peaks; HeartRateSummary heart_rate; PqrstReview pqrst; };`
  - `ReviewResult review_channels(const std::vector<double>& ch1, const std::vector<double>& ch2, double sample_rate_hz, const std::string& source);`

- [ ] **Step 1: Write the failing channel-select test** (uses the quality fixture's ch1/ch2 to pin the scores + chosen channel)

```cpp
// tests/cpp/test_channel_select.cpp
#include "catch.hpp"
#include "ads1292/dsp/ChannelSelect.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace { json rv(const std::string& n){ std::ifstream in(std::string(FIXTURE_DIR)+"/review/"+n+".json"); json j; in>>j; return j; } }

TEST_CASE("choose_ecg_channel reproduces the golden scores + channel", "[review]") {
  auto f = rv("quality_metrics_clean_72bpm");
  auto ch1 = f.at("input").at("ch1").get<std::vector<double>>();
  auto ch2 = f.at("input").at("ch2").get<std::vector<double>>();
  auto o = f.at("output");
  auto c = choose_ecg_channel(ch1, ch2, 500.0, "Auto");
  REQUIRE(c.score_ch1 == Approx(o.at("score_ch1").get<double>()).margin(1e-9));
  REQUIRE(c.score_ch2 == Approx(o.at("score_ch2").get<double>()).margin(1e-9));
  REQUIRE(c.channel == o.at("ecg_source").get<std::string>());   // "CH2"
}
```
(Golden: score_ch1=0.0, score_ch2=100.39270264893261, ecg_source="CH2".)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `qrs_like_score` (bandpass → diff → MAD → percentile(99)/mad; `<100` → 0), `_channel_selection_score` (file-local; detect_r_peaks → heart_rate_summary → `qrs_like_score * max(1,valid_rr_count)`), `choose_ecg_channel` (the `select_ch2 > select_ch1*1.05` rule, override upper-cased), `review_channels`. Reuse P5a/P5b. Note: `score_ch1=0.0` because ch1 is flat/low → qrs_like_score returns a small value or the channel has no QRS; confirm against the fixture.

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS (scores + channel match).

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/ChannelSelect.h core/src/dsp/ChannelSelect.cpp core/CMakeLists.txt tests/cpp/test_channel_select.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5c channel selection (qrs_like_score/choose_ecg_channel/review_channels)"
```

---

### Task 3: compute_quality_metrics (parity vs golden)

**Files:**
- Create: `core/include/ads1292/dsp/QualityMetrics.h`, `core/src/dsp/QualityMetrics.cpp`
- Modify: `core/CMakeLists.txt`; Create `tests/cpp/test_quality_metrics.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: `review_channels`/`ReviewResult` (Task 2), `noise_rms`/`baseline_drift` (Task 1), the `StreamSample` model (`ch1`, `ch2`, `int lead_off_bits() const`).
- Produces (namespace `ads1292::dsp`):
  - `struct QualityMetrics { int sample_count; double duration_seconds; std::string ecg_source; double contact_ok_percent; int lead_off_bad_samples; int r_peaks; double hr_median_bpm, hr_min_bpm, hr_max_bpm; bool qrs_clear, p_tentative, t_tentative; double score_ch1, score_ch2, baseline_drift_counts, noise_rms_counts, peak_to_peak_counts; };`
  - `QualityMetrics compute_quality_metrics(const std::vector<ads1292::StreamSample>& samples, double sample_rate_hz, const std::string& source);`

- [ ] **Step 1: Write the failing quality-parity test** (reconstruct samples from the fixture's ch1/ch2/status_byte)

```cpp
// tests/cpp/test_quality_metrics.cpp
#include "catch.hpp"
#include "ads1292/dsp/QualityMetrics.h"
#include "ads1292/model/StreamSample.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace { json rv(const std::string& n){ std::ifstream in(std::string(FIXTURE_DIR)+"/review/"+n+".json"); json j; in>>j; return j; } }

TEST_CASE("compute_quality_metrics matches the golden", "[review]") {
  auto f = rv("quality_metrics_clean_72bpm");
  auto ch1 = f.at("input").at("ch1").get<std::vector<int>>();
  auto ch2 = f.at("input").at("ch2").get<std::vector<int>>();
  int status = f.at("input").at("status_byte").get<int>();
  std::vector<ads1292::StreamSample> samples;
  for (size_t i=0;i<ch1.size();++i){ ads1292::StreamSample s; s.ch1=ch1[i]; s.ch2=ch2[i]; s.status_byte=status; samples.push_back(s); }
  auto m = compute_quality_metrics(samples, 500.0, "Auto");
  auto o = f.at("output");
  REQUIRE(m.sample_count == o.at("sample_count").get<int>());
  REQUIRE(m.ecg_source == o.at("ecg_source").get<std::string>());
  REQUIRE(m.contact_ok_percent == Approx(o.at("contact_ok_percent").get<double>()).margin(1e-9));
  REQUIRE(m.lead_off_bad_samples == o.at("lead_off_bad_samples").get<int>());
  REQUIRE(m.r_peaks == o.at("r_peaks").get<int>());
  REQUIRE(m.hr_median_bpm == Approx(o.at("hr_median_bpm").get<double>()).margin(1e-9));
  REQUIRE(m.qrs_clear == o.at("qrs_clear").get<bool>());
  REQUIRE(m.p_tentative == o.at("p_tentative").get<bool>());
  REQUIRE(m.t_tentative == o.at("t_tentative").get<bool>());
  REQUIRE(m.score_ch2 == Approx(o.at("score_ch2").get<double>()).margin(1e-9));
  REQUIRE(m.baseline_drift_counts == Approx(o.at("baseline_drift_counts").get<double>()).margin(1e-9));
  REQUIRE(m.noise_rms_counts == Approx(o.at("noise_rms_counts").get<double>()).margin(1e-9));
  REQUIRE(m.peak_to_peak_counts == Approx(o.at("peak_to_peak_counts").get<double>()).margin(1e-9));
}
```
(Golden: sample_count=2500, ecg_source="CH2", contact_ok=100.0, lead_off_bad=0, r_peaks=6, hr_median=71.94244604316548, qrs=true, p=false, t=true, score_ch2=100.39270264893261, baseline_drift=1.0, noise_rms=6.2901390827230514, p2p=715.0.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `compute_quality_metrics` per the Global Constraints (empty guard; build ch1/ch2 double arrays; `review_channels`; pick ecg by channel; `lead_bad` via `s.lead_off_bits()!=0`; `contact_ok = 100.0*(size-lead_bad)/size`; `baseline_drift`/`noise_rms`/`p2p` on ecg). Reuse Task 1/2 functions.

- [ ] **Step 4: Wire CMake, build, run.** Iterate until all fields match. `noise_rms` here (6.290) differs from the SNR fixture's (6.722) because it's on the chosen ecg channel of THIS recording — expected.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/QualityMetrics.h core/src/dsp/QualityMetrics.cpp core/CMakeLists.txt tests/cpp/test_quality_metrics.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5c compute_quality_metrics vs golden 1e-9"
```

---

### Task 4: KissFFT + spectrum (build_spectrum_analysis parity)

**Files:**
- Create: `third_party/kissfft/{kiss_fft.h,kiss_fft.c,kiss_fftr.h,kiss_fftr.c,_kiss_fft_guts.h}` (vendored from the KissFFT 1.3.x release; BSD-3).
- Modify: `third_party/CMakeLists.txt` (add `kissfft` STATIC target compiled with `-Dkiss_fft_scalar=double`).
- Create: `core/include/ads1292/dsp/Spectrum.h`, `core/src/dsp/Spectrum.cpp`.
- Modify: `core/CMakeLists.txt` (link `kissfft` into `ads1292_core`); add `histogram`/`hanning` to `Stats.{h,cpp}`. Create `tests/cpp/test_spectrum.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (namespace `ads1292::dsp`):
  - `std::vector<double> hanning(int M);`
  - `void histogram(const std::vector<double>& v, int bins, std::vector<long>& counts, std::vector<double>& edges);` (numpy uniform)
  - `std::vector<std::complex<double>> rfft(const std::vector<double>& x);` (KissFFT kiss_fftr wrapper; returns n/2+1 bins)
  - `struct SpectrumAnalysis { std::string ecg_label; std::vector<double> ecg_frequency_hz, ecg_power; std::vector<long> histogram_counts; std::vector<double> histogram_bin_edges; };`
  - `SpectrumAnalysis build_spectrum_analysis(const std::vector<ads1292::StreamSample>& samples, const std::string& source, double sample_rate_hz, double max_frequency_hz=60.0, int histogram_bins=48);`

- [ ] **Step 1: Vendor KissFFT.** Download the KissFFT source (BSD-3) and copy `kiss_fft.{h,c}`, `kiss_fftr.{h,c}`, `_kiss_fft_guts.h` into `third_party/kissfft/`. Add to `third_party/CMakeLists.txt`:
```cmake
add_library(kissfft STATIC kissfft/kiss_fft.c kissfft/kiss_fftr.c)
target_include_directories(kissfft PUBLIC kissfft)
target_compile_definitions(kissfft PUBLIC kiss_fft_scalar=double)
```

- [ ] **Step 2: Write the failing spectrum-parity test**

```cpp
// tests/cpp/test_spectrum.cpp
#include "catch.hpp"
#include "ads1292/dsp/Spectrum.h"
#include "ads1292/model/StreamSample.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace { json sp(const std::string& n){ std::ifstream in(std::string(FIXTURE_DIR)+"/spectrum/"+n+".json"); json j; in>>j; return j; } }

TEST_CASE("build_spectrum_analysis matches the golden", "[spectrum]") {
  auto f = sp("spectrum_clean_72bpm_ch2");
  auto ch2 = f.at("input").at("ch2").get<std::vector<int>>();
  std::vector<ads1292::StreamSample> samples;
  for (int v : ch2){ ads1292::StreamSample s; s.ch2=v; samples.push_back(s); }
  auto a = build_spectrum_analysis(samples, "CH2", 500.0, 60.0, 48);
  auto o = f.at("output");
  auto ef = o.at("ecg_frequency_hz").get<std::vector<double>>();
  auto ep = o.at("ecg_power").get<std::vector<double>>();
  auto hc = o.at("histogram_counts").get<std::vector<long>>();
  auto he = o.at("histogram_bin_edges").get<std::vector<double>>();
  REQUIRE(a.ecg_frequency_hz.size() == ef.size());
  for (size_t i=0;i<ef.size();++i) REQUIRE(a.ecg_frequency_hz[i] == Approx(ef[i]).margin(1e-9));
  REQUIRE(a.ecg_power.size() == ep.size());
  for (size_t i=0;i<ep.size();++i) REQUIRE(a.ecg_power[i] == Approx(ep[i]).epsilon(1e-9));   // REL 1e-9
  REQUIRE(a.histogram_counts == hc);                                                          // EXACT
  REQUIRE(a.histogram_bin_edges.size() == he.size());
  for (size_t i=0;i<he.size();++i) REQUIRE(a.histogram_bin_edges[i] == Approx(he[i]).margin(1e-9));
}
```
(Golden: 246 freq/power bins, freq[0]=0, freq[1]=0.244140625, power[0]=402280.1254…; 48 counts, 49 edges.)

- [ ] **Step 3: Run to verify it fails.**

- [ ] **Step 4: Implement** `hanning`, `histogram` (Stats), `rfft` (KissFFT kiss_fftr wrapper: `kiss_fftr_alloc(n,0,...)`, pack the real input, read n/2+1 `kiss_fft_cpx` out, free the cfg), and `build_spectrum_analysis`/`_fft_power` per the Global Constraints (center by mean, Hann window, rfft, power=|.|^2, rfftfreq, keep ≤ max_freq; histogram on the raw values). Use `kiss_fftr` (real FFT), NOT the complex `kiss_fft`.

- [ ] **Step 5: Wire CMake (link kissfft), build, run.** Iterate. If `ecg_power` fails REL 1e-9 on a few small-magnitude bins, report DONE_WITH_CONCERNS with the max relative error + which bins; if histogram_counts mismatch, the bin float-correction is off; if freq is off, rfftfreq is wrong.

- [ ] **Step 6: Commit**

```bash
git add third_party/kissfft third_party/CMakeLists.txt core/include/ads1292/dsp/Spectrum.h core/src/dsp/Spectrum.cpp core/include/ads1292/dsp/Stats.h core/src/dsp/Stats.cpp core/CMakeLists.txt tests/cpp/test_spectrum.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5c KissFFT spectrum + histogram vs golden (freq 1e-9, power rel 1e-9, counts exact)"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P5 quality/spectrum scope):
- estimate_realtime_snr + _noise_rms + _baseline_drift → Task 1 ✓
- channel selection (qrs_like_score/choose_ecg_channel/review_channels) → Task 2 ✓
- compute_quality_metrics → Task 3 ✓
- build_spectrum_analysis (rFFT + histogram) → Task 4 ✓
- GUI SNR strip + display-filter backfill → **P5d** (out of scope here)

**2. Placeholder scan:** The numpy primitives (percentile/hanning/histogram/rfftfreq) and all functions are spelled out concretely in the Global Constraints; the golden fixtures are the authoritative gate. Every test body, signature, and the exact golden targets are concrete. KissFFT internals are vendored, not transcribed (a third-party BSD lib).

**3. Type consistency:** `percentile`/`mean` (Task 1) used by Task 2 (`qrs_like_score`); `noise_rms`/`baseline_drift` (Task 1) used by Task 3; `review_channels`/`ChannelChoice`/`ReviewResult` (Task 2) used by Task 3; `hanning`/`histogram` (Task 4, added to Stats) + `rfft`. `SignalNoiseEstimate`/`QualityMetrics`/`ChannelChoice`/`ReviewResult`/`SpectrumAnalysis` match the Python dataclasses field-for-field. `StreamSample` (`ch1`/`ch2`/`lead_off_bits()`) is the existing model.

**Risk notes for the executor:**
- **FFT precision (Task 4):** KissFFT (double) vs numpy/pocketfft must agree to REL 1e-9 on `ecg_power`. For the fixture's n and the broad ECG spectrum (powers ≫ 1) this is expected to hold, but a near-zero bin could blow the relative error. If so, report DONE_WITH_CONCERNS with the worst bin — do NOT loosen the tolerance unilaterally.
- **histogram counts EXACT (Task 4):** numpy's float bin-assignment fixups (the decrement/increment loop) must be reproduced or boundary samples land one bin off.
- **percentile (Task 1):** numpy's linear interpolation (`pos=(q/100)*(n-1)`) — an off-by-one or a `q/100*n` mistake shifts p2p.
- `np.diff` reduces length by 1; `qrs_like_score`'s `<100` guard is on the FILTERED length.
- Keep everything `double` (KissFFT compiled with `kiss_fft_scalar=double`).
