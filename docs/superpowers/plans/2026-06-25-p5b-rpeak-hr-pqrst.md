# P5b: R-peak + HR + PQRST Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproduce the Python ECG analysis chain on top of the (already bit-exact) P5a filters — SciPy `find_peaks` (distance + prominence), `detect_r_peaks`, `heart_rate_summary`, and `pqrst_review` — verified against the P-1 frozen golden fixtures (`rpeak/*` exact peak indices + intermediates; `review/hr_summary`, `review/pqrst`).

**Architecture:** A portable `core/dsp` extension (pure C++17, no Qt): a faithful `find_peaks(distance, prominence)` (local-maxima → distance-by-height → prominence), then `detect_r_peaks` (bandpass → center → prominence/polarity → find_peaks), `heart_rate_summary`, and `pqrst_review` (average-beat morphology). All sit on the P5a `bandpass`/`filtfilt` proven to match SciPy. Every function is gated by a committed golden fixture.

**Tech Stack:** C++17, CMake, Catch2 + nlohmann/json. Re-uses P5a `core/dsp` filters and the `EventMarker`-style model pattern. Oracle: `signal_processing.py`; golden: `tests/fixtures/golden/{rpeak,review}/`.

## Global Constraints

- **C++17**; `core/dsp` stays pure portable C++ (stdlib only, all `double`, no Qt/OS).
- **Layering**: depends on P5a `core/dsp` (bandpass/filtfilt) + core model. No new external deps.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Parity gates:** R-peak indices = EXACT integer match; the rpeak-chain intermediates (filtered, centered, scale_std, prominence) to abs 1e-6/1e-9; HR/PQRST floats to abs 1e-9 (average_beat to 1e-6).
- **SciPy `find_peaks(x, distance, prominence)` — apply conditions in SciPy's order (distance BEFORE prominence; verified):**
  1. **local maxima** (`_local_maxima_1d`): scan `i = 1 .. n-2`; if `x[i-1] < x[i]`: set `i_ahead = i+1`; while `i_ahead < n-1 && x[i_ahead] == x[i]`: `++i_ahead`; if `x[i_ahead] < x[i]`: it is a peak (plateau `[i, i_ahead-1]`) with midpoint `(i + i_ahead - 1) / 2` (integer div); record midpoint; set `i = i_ahead`.
  2. **distance** (`_select_by_peak_distance(peaks, priority=x[peaks], distance)`): `d = ceil(distance)`; `keep` all-true; visit peaks in DESCENDING priority (height) order (`argsort(priority)` then reverse); for each kept peak `j`: walk left `k=j-1` while `k>=0 && peaks[j]-peaks[k] < d` → `keep[k]=false`; walk right `k=j+1` while `k<m && peaks[k]-peaks[j] < d` → `keep[k]=false`. Keep peaks where `keep` is true.
  3. **prominence** (`_peak_prominences(x, peaks)`): for each peak `p` — left: `i=p, lmin=x[p]`; while `i>=0 && x[i] <= x[p]`: if `x[i] < lmin` `lmin=x[i]`; `--i`. right: `i=p, rmin=x[p]`; while `i<n && x[i] <= x[p]`: if `x[i] < rmin` `rmin=x[i]`; `++i`. `prominence[p] = x[p] - max(lmin, rmin)`. Keep peaks with `prominence >= prominence_min`.
  Return the surviving peak indices in ascending order.
- **`detect_r_peaks(values, sr)` (from signal_processing.py, verbatim):** if `!finite(sr) || sr<=0` → empty; if `size < (int)sr` → empty; `filtered = bandpass(values, sr)`; `centered = filtered - median(filtered)`; `scale = std(centered)` (population std, ddof=0); `prominence = max(20.0, scale*0.45)`; `pos = max(centered)`, `neg = |min(centered)|`; `peak_signal = (pos >= neg) ? centered : -centered`; `peaks = find_peaks(peak_signal, distance=(int)(0.35*sr), prominence)`; return as ints.
- **`heart_rate_summary(peaks, sr)`:** if `peaks.size()<2 || !finite(sr) || sr<=0` → `{0,0,0,0}`; `rr[i] = (peaks[i+1]-peaks[i]) / sr`; `bpm[i] = 60/rr[i]`; `valid = bpm where 40<=bpm<=180`; if empty → `{0,0,0,0}`; else `{median(valid), min(valid), max(valid), valid.size()}`.
- **`pqrst_review(values, peaks, sr)`:** `filtered = bandpass(values, sr, low=0.15, high=40.0)`; `pre=(int)(0.25*sr)`, `post=(int)(0.55*sr)`; for each peak: if `peak-pre<0 || peak+post>filtered.size()` skip; `beat = filtered[peak-pre .. peak+post)`; `beat -= median(beat[0 .. max(1,(int)(0.12*sr)))`; collect. If no beats → `{false,false,false,0,{},{}}`. `avg = mean over beats (per index)`; `r_amp = |avg[pre]|`; `half = max(1, pre/2)`; `noise = median(|avg[0..half) - median(avg[0..half))|) + 1e-9`; `p_start=pre-(int)(0.22*sr)`, `p_end=pre-(int)(0.08*sr)`, `t_start=pre+(int)(0.12*sr)`, `t_end=pre+(int)(0.38*sr)`; `p_range = (p_end>p_start) ? ptp(avg[p_start..p_end)) : 0`; `t_range = (t_end>t_start) ? ptp(avg[t_start..t_end)) : 0`; `qrs_clear = r_amp > max(40, noise*8)`; `p_tentative = p_range > max(15, noise*3)`; `t_tentative = t_range > max(25, noise*4)`; `time_ms[i] = ((i - pre)/sr)*1000` for `i in 0..pre+post`. `ptp` = max−min. `mean over beats`: per-index average across collected beats. numpy `median`: avg of two middles for even length.

## File Structure

```
core/
  include/ads1292/dsp/Peaks.h        # find_peaks
  src/dsp/Peaks.cpp
  include/ads1292/dsp/EcgReview.h    # RPeakChain, detect_r_peaks, HeartRateSummary, heart_rate_summary, PqrstReview, pqrst_review
  src/dsp/EcgReview.cpp
tests/cpp/
  test_find_peaks.cpp                # find_peaks unit cases
  test_detect_r_peaks.cpp            # rpeak fixtures (exact peaks + chain)
  test_hr_pqrst.cpp                  # review/hr_summary + review/pqrst fixtures
```

---

### Task 1: find_peaks (local maxima + distance + prominence)

**Files:**
- Create: `core/include/ads1292/dsp/Peaks.h`, `core/src/dsp/Peaks.cpp`
- Modify: `core/CMakeLists.txt`; Create test `tests/cpp/test_find_peaks.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (in `namespace ads1292::dsp`): `std::vector<int> find_peaks(const std::vector<double>& x, int distance, double prominence_min);` (applies local-maxima → distance → prominence in SciPy order; returns ascending indices).

- [ ] **Step 1: Write the failing find_peaks test** (hand-computed cases + the SciPy-confirmed ordering case)

```cpp
// tests/cpp/test_find_peaks.cpp
#include "catch.hpp"
#include "ads1292/dsp/Peaks.h"
using ads1292::dsp::find_peaks;

TEST_CASE("find_peaks: distance keeps the taller peak (scipy order)", "[peaks]") {
  std::vector<double> x = {0, 5, 0, 10, 0, 6, 0};   // peaks at 1(5),3(10),5(6)
  REQUIRE(find_peaks(x, /*distance=*/3, /*prominence=*/0.0) == std::vector<int>{3});
  REQUIRE(find_peaks(x, 3, 4.0) == std::vector<int>{3});      // prominence after distance
}

TEST_CASE("find_peaks: plateau midpoint", "[peaks]") {
  std::vector<double> x = {0, 1, 2, 2, 2, 1, 0};    // plateau [2..4] -> midpoint 3
  REQUIRE(find_peaks(x, 1, 0.0) == std::vector<int>{3});
}

TEST_CASE("find_peaks: prominence filters low peaks", "[peaks]") {
  std::vector<double> x = {0, 1, 0, 10, 0};          // peak at 1 (prom 1), 3 (prom 10)
  REQUIRE(find_peaks(x, 1, 5.0) == std::vector<int>{3});
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement `find_peaks`** with the three SciPy sub-algorithms from the Global Constraints (local-maxima with plateau midpoint; `_select_by_peak_distance` visiting peaks in descending height with `d=ceil(distance)`; `_peak_prominences` left/right contour). Apply distance THEN prominence. Return ascending indices.

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/Peaks.h core/src/dsp/Peaks.cpp core/CMakeLists.txt tests/cpp/test_find_peaks.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5b find_peaks (local maxima + distance + prominence, SciPy order)"
```

---

### Task 2: detect_r_peaks (chain parity vs golden)

**Files:**
- Create: `core/include/ads1292/dsp/EcgReview.h`, `core/src/dsp/EcgReview.cpp` (add `detect_r_peaks` + helpers `median`, `std_pop`)
- Modify: `core/CMakeLists.txt`; Create test `tests/cpp/test_detect_r_peaks.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (in `namespace ads1292::dsp`): `std::vector<int> detect_r_peaks(const std::vector<double>& values, double sample_rate_hz);` (per the Global-Constraints algorithm; reuses P5a `bandpass`).

- [ ] **Step 1: Write the failing rpeak-parity test** (the 3 rpeak fixtures: exact peaks + the chain intermediates)

```cpp
// tests/cpp/test_detect_r_peaks.cpp
#include "catch.hpp"
#include "ads1292/dsp/EcgReview.h"
#include "ads1292/dsp/Filtfilt.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace { json fx(const std::string& n){ std::ifstream in(std::string(FIXTURE_DIR)+"/rpeak/"+n+".json"); json j; in>>j; return j; } }

TEST_CASE("detect_r_peaks reproduces the clean 72bpm peaks exactly", "[rpeak]") {
  auto f = fx("rpeak_chain_clean_72bpm");
  auto sig = f.at("input").at("signal").get<std::vector<double>>();
  auto got = detect_r_peaks(sig, 500.0);
  auto exp = f.at("output").at("peaks").get<std::vector<int>>();
  REQUIRE(got == exp);                                   // EXACT index match
}
TEST_CASE("detect_r_peaks fast 110bpm exact", "[rpeak]") {
  auto f = fx("rpeak_chain_fast_110bpm");
  auto sig = f.at("input").at("signal").get<std::vector<double>>();
  REQUIRE(detect_r_peaks(sig, 500.0) == f.at("output").at("peaks").get<std::vector<int>>());
}
TEST_CASE("detect_r_peaks short-below-sr returns empty", "[rpeak]") {
  auto f = fx("rpeak_chain_short_below_sr");
  auto sig = f.at("input").at("signal").get<std::vector<double>>();
  REQUIRE(detect_r_peaks(sig, 500.0).empty());
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement `detect_r_peaks`** exactly per the Global Constraints (early returns; `bandpass` from P5a; `centered = filtered - median`; `scale = population std`; `prominence = max(20, scale*0.45)`; polarity by excursion; `find_peaks(distance=(int)(0.35*sr), prominence)`). Add file-local `median` (numpy semantics) and `std_pop` (population std, mean-subtracted). The peaks must match EXACTLY; if off, the `centered`/`prominence`/polarity will reveal which stage — the rpeak fixture also stores `filtered`/`centered`/`scale_std`/`prominence`/`polarity` you can spot-check.

- [ ] **Step 4: Wire CMake, build, run.** Iterate until all 3 rpeak fixtures pass (exact peaks). If peaks differ by one or a near-miss, the prominence threshold or the distance tie-break ordering is off.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/EcgReview.h core/src/dsp/EcgReview.cpp core/CMakeLists.txt tests/cpp/test_detect_r_peaks.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5b detect_r_peaks with exact golden peak-index parity"
```

---

### Task 3: heart_rate_summary (parity vs golden)

**Files:**
- Modify: `core/include/ads1292/dsp/EcgReview.h`, `core/src/dsp/EcgReview.cpp` (add `HeartRateSummary` + `heart_rate_summary`)
- Modify: `tests/cpp/CMakeLists.txt`; Create test `tests/cpp/test_hr_pqrst.cpp` (HR cases).

**Interfaces:**
- Produces (in `namespace ads1292::dsp`):
  - `struct HeartRateSummary { double median_bpm, min_bpm, max_bpm; int valid_rr_count; };`
  - `HeartRateSummary heart_rate_summary(const std::vector<int>& peaks, double sample_rate_hz);`

- [ ] **Step 1: Write the failing HR-parity test**

```cpp
// tests/cpp/test_hr_pqrst.cpp
#include "catch.hpp"
#include "ads1292/dsp/EcgReview.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace { json rv(const std::string& n){ std::ifstream in(std::string(FIXTURE_DIR)+"/review/"+n+".json"); json j; in>>j; return j; } }

TEST_CASE("heart_rate_summary matches the golden", "[review]") {
  auto f = rv("hr_summary_clean_72bpm");
  auto peaks = f.at("input").at("peaks").get<std::vector<int>>();
  auto got = heart_rate_summary(peaks, 500.0);
  auto o = f.at("output");
  REQUIRE(got.median_bpm == Approx(o.at("median_bpm").get<double>()).margin(1e-9));
  REQUIRE(got.min_bpm == Approx(o.at("min_bpm").get<double>()).margin(1e-9));
  REQUIRE(got.max_bpm == Approx(o.at("max_bpm").get<double>()).margin(1e-9));
  REQUIRE(got.valid_rr_count == o.at("valid_rr_count").get<int>());
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement `heart_rate_summary`** per the Global Constraints (R-R → bpm, 40..180 filter, median/min/max/count; empty/short → zeros). numpy `median` = avg of two middles for even length.

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/EcgReview.h core/src/dsp/EcgReview.cpp tests/cpp/test_hr_pqrst.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5b heart_rate_summary vs golden"
```

---

### Task 4: pqrst_review (parity vs golden)

**Files:**
- Modify: `core/include/ads1292/dsp/EcgReview.h`, `core/src/dsp/EcgReview.cpp` (add `PqrstReview` + `pqrst_review`)
- Modify: `tests/cpp/test_hr_pqrst.cpp` (PQRST case).

**Interfaces:**
- Produces (in `namespace ads1292::dsp`):
  - `struct PqrstReview { bool qrs_clear, p_tentative, t_tentative; int beats_used; std::vector<double> average_beat, time_ms; };`
  - `PqrstReview pqrst_review(const std::vector<double>& values, const std::vector<int>& peaks, double sample_rate_hz);`

- [ ] **Step 1: Write the failing PQRST-parity test**

```cpp
// append to tests/cpp/test_hr_pqrst.cpp
TEST_CASE("pqrst_review matches the golden", "[review]") {
  auto f = rv("pqrst_clean_72bpm");
  auto sig = f.at("input").at("signal").get<std::vector<double>>();
  auto peaks = f.at("input").at("peaks").get<std::vector<int>>();
  auto got = pqrst_review(sig, peaks, 500.0);
  auto o = f.at("output");
  REQUIRE(got.qrs_clear == o.at("qrs_clear").get<bool>());
  REQUIRE(got.p_tentative == o.at("p_tentative").get<bool>());
  REQUIRE(got.t_tentative == o.at("t_tentative").get<bool>());
  REQUIRE(got.beats_used == o.at("beats_used").get<int>());
  auto eb = o.at("average_beat").get<std::vector<double>>();
  REQUIRE(got.average_beat.size() == eb.size());
  for (size_t i=0;i<eb.size();++i) REQUIRE(got.average_beat[i] == Approx(eb[i]).margin(1e-6));
  auto tm = o.at("time_ms").get<std::vector<double>>();
  REQUIRE(got.time_ms.size() == tm.size());
  for (size_t i=0;i<tm.size();++i) REQUIRE(got.time_ms[i] == Approx(tm[i]).margin(1e-9));
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement `pqrst_review`** per the Global Constraints (bandpass low=0.15/high=40; per-beat window pre/post with the baseline subtraction; mean beat; r_amp/noise/p_range/t_range; the three boolean flags; average_beat + time_ms). Reuse P5a `bandpass`. `ptp` = max−min over the slice.

- [ ] **Step 4: Wire CMake, build, run.** Iterate until the PQRST fixture passes (booleans + beats_used + average_beat to 1e-6 + time_ms to 1e-9). If average_beat is off, the per-beat baseline subtraction window or the mean is wrong.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/EcgReview.h core/src/dsp/EcgReview.cpp tests/cpp/test_hr_pqrst.cpp
git commit -m "feat: P5b pqrst_review (average-beat morphology) vs golden"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P5 R-peak/HR/PQRST scope):
- find_peaks → Task 1 ✓
- detect_r_peaks (exact peak parity) → Task 2 ✓
- heart_rate_summary → Task 3 ✓
- pqrst_review → Task 4 ✓
- quality metrics + spectrum → **P5c** (out of scope here)
- GUI SNR strip + display-filter backfill → **P5d** (out of scope here)
- `choose_ecg_channel`/`review_channels` (the channel-selection wrapper) → folded into P5c's quality task (it calls detect_r_peaks + qrs_like_score), noted; not built here.

**2. Placeholder scan:** Task 1/2/4 Step 3 describe the SciPy algorithm (spelled out concretely in the Global Constraints) rather than transcribing it inline, because the algorithm IS the spec and the golden fixtures (exact peaks, 1e-6/1e-9 floats) are the authoritative gate. Every test body, interface signature, and the exact rpeak targets (peaks `[200,617,1033,1450,1867,2283]`, prominence `40.782804`, polarity `positive`) are concrete.

**3. Type consistency:** `find_peaks` (Task 1) used by `detect_r_peaks` (Task 2). `detect_r_peaks` not strictly needed by Tasks 3/4 (they take peaks from the fixture input), but `heart_rate_summary`/`pqrst_review` share `EcgReview.{h,cpp}`. `HeartRateSummary`/`PqrstReview` structs defined in Task 3/4 headers, consumed by their tests. The P5a `bandpass` signature (`bandpass(v, sr, low, high)`) is used by `detect_r_peaks` (defaults) and `pqrst_review` (0.15/40).

**Risk notes for the executor:**
- The hardest item is `find_peaks` matching SciPy's EXACT peak set — the distance tie-break (descending height) and the prominence contour walk must be exact. Validate Task 1 standalone before Task 2 relies on it.
- `detect_r_peaks` exact-index parity depends on BOTH the P5a bandpass (already proven) AND find_peaks; if peaks are off, spot-check the fixture's stored `centered`/`prominence`/`polarity` to localize the stage.
- `std` must be POPULATION std (ddof=0, divide by N) to match numpy `np.std` default; using sample std (ddof=1) will shift the prominence threshold and change peaks.
- numpy `median` for an even-length array is the average of the two middle elements after sorting — implement it that way everywhere (detect_r_peaks centering, pqrst baseline, noise).
- Keep everything `double`.
