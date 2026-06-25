# P5a: DSP Filters (butter / iirnotch / filtfilt) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproduce, bit-for-bit within tolerance, the SciPy filter stack the Python app uses — `butter(2,…)` / `iirnotch` coefficient generation and zero-phase `filtfilt` — verified against the P-1 frozen golden DSP fixtures (coefficients to abs 1e-12, filtfilt outputs to abs 1e-6). This is the keystone numeric phase: R-peak detection, quality metrics, and the GUI display filters all sit on top of it.

**Architecture:** A portable `core/dsp` module (pure C++17, no Qt) implementing the SciPy IIR pipeline: Butterworth analog prototype → frequency transform (lp2lp/lp2hp/lp2bp in zero-pole-gain form) → bilinear transform → transfer-function coefficients; plus `iirnotch`; plus `lfilter`/`lfilter_zi`/`filtfilt` (odd padding + initial conditions). The public wrappers (`bandpass`/`highpass`/`lowpass`/`notch`) mirror `signal_processing.py` exactly, including the `size < 16` median-detrend fallback. Every piece is verified against a committed golden fixture.

**Tech Stack:** C++17, CMake, `std::complex<double>`, Catch2. Re-uses nothing new; produces the foundation for P5b/P5c. The Python oracle is `signal_processing.py` (which calls `scipy.signal`); the committed `tests/fixtures/golden/dsp/*.json` are the parity gates.

## Global Constraints

- **C++17**; `core/dsp` is pure portable C++ — only `<complex>`, `<vector>`, `<cmath>`, etc. NO Qt, NO OS.
- **Layering**: `core/dsp` depends on nothing. Filters live in `core` (used later by `io`/`gui`).
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Parity is the bar.** Coefficient fixtures: abs `1e-12`. filtfilt-output fixtures: abs `1e-6`. The committed golden coefficient values (from `tests/fixtures/golden/dsp/`) are the exact targets, e.g. bandpass `b=[0.0353019945279248, 0, -0.0706039890558496, 0, 0.0353019945279248]`, `a=[1.0, -3.3959948273203824, 4.337679697819303, -2.4855602670882986, 0.5438867661052419]`.
- **SciPy algorithm to replicate (digital, `fs` defaults to 2.0; `Wn` is already normalized to Nyquist by `signal_processing.py`):**
  1. **buttap(N)** — Butterworth analog prototype: `z = {}`, `p[k] = -exp(i·π·m_k / (2N))` for `m_k` in `arange(-N+1, N, 2)`, `k = 1`. (N=2 → `p = {-0.70710678…+0.70710678…i, -0.70710678…-0.70710678…i}`.)
  2. **prewarp**: `fs = 2.0`; `warped = 2·fs·tan(π·Wn/fs)` = `4·tan(π·Wn/2)`.
  3. **frequency transform** (zpk):
     - lowpass `lp2lp_zpk(z,p,k, wo)`: `degree = len(p)-len(z)`; `z*=wo`, `p*=wo`, `k *= wo^degree`.
     - highpass `lp2hp_zpk(z,p,k, wo)`: `degree = len(p)-len(z)`; `z_hp = wo/z` then append `degree` zeros; `p_hp = wo/p`; `k_hp = k · real(prod(-z)/prod(-p))`.
     - bandpass `lp2bp_zpk(z,p,k, wo, bw)`: `degree=len(p)-len(z)`; scale `z·bw/2`, `p·bw/2`; `z_bp = concat(z_lp + sqrt(z_lp²-wo²), z_lp - sqrt(z_lp²-wo²))`; same for poles; append `degree` zeros to `z_bp`; `k_bp = k · bw^degree`. (wo=`sqrt(warped_low·warped_high)`, bw=`warped_high-warped_low`.)
  4. **bilinear_zpk(z,p,k, fs=2.0)**: `fs2 = 2·fs`; `z_d = (fs2+z)/(fs2-z)`; `p_d = (fs2+p)/(fs2-p)`; append `degree = len(p_d_pre)-len(z_d_pre)` zeros at `-1` to `z_d`; `k_d = k · real(prod(fs2-z)/prod(fs2-p))`.
  5. **zpk2tf(z,p,k)**: `b = k · poly(z)`, `a = poly(p)` where `poly(roots)` expands `∏(x - root)` to real polynomial coefficients (take the real part).
- **iirnotch(w0, Q)** (w0 normalized 0..1): `bw = w0/Q`; `gb = 1/sqrt(2)`; `beta = (sqrt(1-gb²)/gb)·tan(π·bw/2)`; `gain = 1/(1+beta)`; `b = gain·{1, -2cos(π·w0), 1}`; `a = {1, -2·gain·cos(π·w0), 2·gain-1}`.
- **filtfilt(b, a, x)** (SciPy defaults): `ntaps = max(len(a), len(b))`; `padlen = 3·(ntaps-1)`; **odd extension** of `x` by `padlen` on each end (`ext = 2·x[0] - x[padlen:0:-1]` on the left, `2·x[-1] - x[-2:-padlen-2:-1]` on the right); compute `zi = lfilter_zi(b,a)`; forward `lfilter(b,a, ext, zi·ext[0])`; reverse; backward `lfilter(b,a, reversed, zi·reversed[0])`; reverse; slice off `padlen` from each end.
- **lfilter_zi(b,a)**: the steady-state initial condition — solve `(I - A) · zi = B` where `A` is the companion-form state matrix and `B` is derived from `b,a` (SciPy: `zi = solve(eye(n) - linalg.companion(a).T, b[1:] - a[1:]·b[0])` with the cumulative-sum normalization; replicate SciPy's `lfilter_zi` exactly).
- **`< 16` fallback** (from `signal_processing.py`): for `bandpass`/`highpass`, if `size < 16` return `arr - median(arr)` (or `arr` empty); `lowpass`/`notch` return `arr` unchanged for `size < 16`. Mirror the exact per-function behavior.

## File Structure

```
core/
  include/ads1292/dsp/Iir.h          # zpk types, butter*, iirnotch, lfilter, lfilter_zi
  src/dsp/Iir.cpp
  include/ads1292/dsp/Filtfilt.h     # filtfilt + the bandpass/highpass/lowpass/notch wrappers
  src/dsp/Filtfilt.cpp
tests/cpp/
  test_iir_coeffs.cpp                # butter + iirnotch vs coeff fixtures (1e-12)
  test_lfilter.cpp                   # lfilter + lfilter_zi unit checks
  test_filtfilt.cpp                  # filtfilt vs filtfilt fixtures (1e-6) + <16 fallback
```

---

### Task 1: Butterworth coefficients (butter bandpass/highpass/lowpass)

**Files:**
- Create: `core/include/ads1292/dsp/Iir.h`, `core/src/dsp/Iir.cpp` (the zpk pipeline + `butter_*`)
- Modify: `core/CMakeLists.txt`; Create test `tests/cpp/test_iir_coeffs.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (in `namespace ads1292::dsp`):
  - `struct Coeffs { std::vector<double> b, a; };`
  - `Coeffs butter_bandpass(double sample_rate_hz, double low_hz, double high_hz);` (matches `_bandpass_coefficients`: `nyq=sr/2; high=min(high_hz/nyq,0.99); low=max(low_hz/nyq,0.0001); butter(2,[low,high],'band')`)
  - `Coeffs butter_highpass(double sample_rate_hz, double cutoff_hz);` (`cut=max(cutoff_hz/(sr/2),0.0001); butter(2,cut,'highpass')`)
  - `Coeffs butter_lowpass(double sample_rate_hz, double cutoff_hz);` (`cut=min(cutoff_hz/(sr/2),0.99); butter(2,cut,'lowpass')`)

- [ ] **Step 1: Write the failing coefficient-parity test** (loads the committed fixtures, compares b/a to abs 1e-12)

```cpp
// tests/cpp/test_iir_coeffs.cpp
#include "catch.hpp"
#include "ads1292/dsp/Iir.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace {
json fx(const std::string& name) {
  std::ifstream in(std::string(FIXTURE_DIR) + "/dsp/" + name + ".json"); json j; in >> j; return j;
}
void check(const Coeffs& got, const json& f) {
  auto eb = f.at("output").at("b"); auto ea = f.at("output").at("a");
  REQUIRE(got.b.size() == eb.size()); REQUIRE(got.a.size() == ea.size());
  for (size_t i = 0; i < eb.size(); ++i) REQUIRE(got.b[i] == Approx(eb[i].get<double>()).margin(1e-12));
  for (size_t i = 0; i < ea.size(); ++i) REQUIRE(got.a[i] == Approx(ea[i].get<double>()).margin(1e-12));
}
}
TEST_CASE("butter bandpass matches the golden coefficients", "[dsp]") {
  check(butter_bandpass(500.0, 0.7, 35.0), fx("coeffs_bandpass_500hz"));
}
TEST_CASE("butter highpass matches", "[dsp]") { check(butter_highpass(500.0, 0.5), fx("coeffs_highpass_500hz")); }
TEST_CASE("butter lowpass matches", "[dsp]") { check(butter_lowpass(500.0, 40.0), fx("coeffs_lowpass_500hz")); }
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement the zpk pipeline + butter** in `Iir.{h,cpp}`: a `Zpk { std::vector<std::complex<double>> z, p; double k; }`; `buttap(N)`; `lp2lp_zpk`/`lp2hp_zpk`/`lp2bp_zpk`; `bilinear_zpk(zpk, fs=2.0)`; `poly(roots)→vector<double>` (real); `zpk2tf(zpk)→Coeffs`; and `butter_bandpass/highpass/lowpass` that normalize Wn exactly like `signal_processing.py`, prewarp (`warped=4·tan(π·Wn/2)`), transform, bilinear, zpk2tf. Follow the Global-Constraints algorithm precisely; the fixtures gate it to 1e-12.

- [ ] **Step 4: Wire CMake (link `nlohmann_json` into tests if not already), build, run.** Iterate against the 1e-12 fixtures; if a coefficient is off, the discrepancy is almost always in the prewarp constant or a zpk transform sign — diff your zpk against SciPy's intermediate values.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/Iir.h core/src/dsp/Iir.cpp core/CMakeLists.txt tests/cpp/test_iir_coeffs.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5a Butterworth coefficient generation (butter bandpass/highpass/lowpass) vs golden 1e-12"
```

---

### Task 2: iirnotch coefficients

**Files:**
- Modify: `core/include/ads1292/dsp/Iir.h`, `core/src/dsp/Iir.cpp` (add `iirnotch`)
- Modify: `tests/cpp/test_iir_coeffs.cpp` (add the notch case).

**Interfaces:**
- Produces: `Coeffs ads1292::dsp::iirnotch(double sample_rate_hz, double notch_hz, double q);` (matches `_notch_coefficients`: `normalized = min(notch_hz/(sr/2), 0.99); iirnotch(normalized, q)`).

- [ ] **Step 1: Add the failing notch test**

```cpp
TEST_CASE("iirnotch matches the golden coefficients", "[dsp]") {
  check(iirnotch(500.0, 60.0, 30.0), fx("coeffs_notch_60hz_500hz"));
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement `iirnotch`** using the closed form in the Global Constraints (`bw=w0/q; gb=1/sqrt2; beta=(sqrt(1-gb²)/gb)·tan(π·bw/2); gain=1/(1+beta); b=gain·{1,-2cos(π·w0),1}; a={1,-2·gain·cos(π·w0),2·gain-1}`). The fixture gates it to 1e-12.

- [ ] **Step 4: Build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/Iir.h core/src/dsp/Iir.cpp tests/cpp/test_iir_coeffs.cpp
git commit -m "feat: P5a iirnotch coefficient generation vs golden 1e-12"
```

---

### Task 3: lfilter + lfilter_zi

**Files:**
- Modify: `core/include/ads1292/dsp/Iir.h`, `core/src/dsp/Iir.cpp` (add `lfilter`, `lfilter_zi`)
- Create test: `tests/cpp/test_lfilter.cpp`; Modify tests CMake.

**Interfaces:**
- Produces:
  - `std::vector<double> ads1292::dsp::lfilter(const Coeffs& c, const std::vector<double>& x, const std::vector<double>& zi);` (direct-form II transposed IIR with initial state `zi`; if `zi` is empty, zero state)
  - `std::vector<double> ads1292::dsp::lfilter_zi(const Coeffs& c);` (SciPy's steady-state initial condition, normalized so the response to a step of 1.0 starts at steady state)

- [ ] **Step 1: Write the failing lfilter/zi test**

```cpp
// tests/cpp/test_lfilter.cpp
#include "catch.hpp"
#include "ads1292/dsp/Iir.h"
using namespace ads1292::dsp;

TEST_CASE("lfilter of a step with a simple IIR", "[dsp]") {
  // y[n] = x[n] (b={1}, a={1}) is identity
  Coeffs id{{1.0}, {1.0}};
  auto y = lfilter(id, {1, 2, 3}, {});
  REQUIRE(y == std::vector<double>{1, 2, 3});
}

TEST_CASE("lfilter_zi makes a step response start at steady state", "[dsp]") {
  // For a lowpass-ish filter, lfilter(b,a, ones, zi*ones[0]) stays ~1.0 (no startup transient)
  Coeffs c = butter_lowpass(500.0, 40.0);
  auto zi = lfilter_zi(c);
  std::vector<double> ones(50, 1.0);
  std::vector<double> z0; for (double v : zi) z0.push_back(v * ones[0]);
  auto y = lfilter(c, ones, z0);
  REQUIRE(y.front() == Approx(1.0).margin(1e-9));   // no transient at the start
  REQUIRE(y.back() == Approx(1.0).margin(1e-9));
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement `lfilter` (transposed direct form II) and `lfilter_zi`.** `lfilter_zi` follows SciPy: with `n=max(len(a),len(b))`, pad `b`/`a` to `n`, normalize by `a[0]`; build the companion-form `A`; solve `(I − A^T)·zi = B` where `B[k] = b[k+1] − a[k+1]·b[0]`, then apply the cumulative-sum step SciPy uses (`zi[0]` set from the sum, propagate). Reproduce `scipy.signal.lfilter_zi` exactly — the step-response test (no startup transient) validates it.

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/Iir.h core/src/dsp/Iir.cpp tests/cpp/test_lfilter.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5a lfilter + lfilter_zi (SciPy steady-state initial conditions)"
```

---

### Task 4: filtfilt + the public filter wrappers (parity vs golden)

**Files:**
- Create: `core/include/ads1292/dsp/Filtfilt.h`, `core/src/dsp/Filtfilt.cpp`
- Modify: `core/CMakeLists.txt`; Create test `tests/cpp/test_filtfilt.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (in `namespace ads1292::dsp`):
  - `std::vector<double> filtfilt(const Coeffs& c, const std::vector<double>& x);` (odd padding + lfilter_zi, SciPy defaults)
  - `std::vector<double> bandpass(const std::vector<double>& v, double sr, double low_hz=0.7, double high_hz=35.0);`
  - `std::vector<double> highpass(const std::vector<double>& v, double sr, double cutoff_hz=0.5);`
  - `std::vector<double> lowpass(const std::vector<double>& v, double sr, double cutoff_hz=40.0);`
  - `std::vector<double> notch(const std::vector<double>& v, double sr, double notch_hz=60.0, double q=30.0);`
  (each mirrors `signal_processing.py`'s `< 16` fallback exactly.)

- [ ] **Step 1: Write the failing filtfilt-parity test** (all 6 filtfilt fixtures + the tiny fallback)

```cpp
// tests/cpp/test_filtfilt.cpp
#include "catch.hpp"
#include "ads1292/dsp/Filtfilt.h"
#include "nlohmann/json.hpp"
#include <fstream>
using nlohmann::json; using namespace ads1292::dsp;
namespace {
json fx(const std::string& n){ std::ifstream in(std::string(FIXTURE_DIR)+"/dsp/"+n+".json"); json j; in>>j; return j; }
std::vector<double> in_signal(const json& f){ return f.at("input").at("signal").get<std::vector<double>>(); }
void check_close(const std::vector<double>& got, const json& f, double tol){
  auto exp = f.at("output").at("filtered").get<std::vector<double>>();
  REQUIRE(got.size() == exp.size());
  for (size_t i=0;i<exp.size();++i) REQUIRE(got[i] == Approx(exp[i]).margin(tol));
}
}
TEST_CASE("filtfilt bandpass long matches golden", "[dsp]") {
  auto f = fx("filtfilt_bandpass_long"); check_close(bandpass(in_signal(f), 500.0), f, 1e-6);
}
TEST_CASE("filtfilt bandpass short window matches", "[dsp]") {
  auto f = fx("filtfilt_bandpass_short_window"); check_close(bandpass(in_signal(f), 500.0), f, 1e-6);
}
TEST_CASE("filtfilt bandpass tiny (<16) uses the median fallback", "[dsp]") {
  auto f = fx("filtfilt_bandpass_tiny_fallback"); check_close(bandpass(in_signal(f), 500.0), f, 1e-9);
}
TEST_CASE("filtfilt notch/highpass/lowpass long match", "[dsp]") {
  check_close(notch(in_signal(fx("filtfilt_notch_long")), 500.0), fx("filtfilt_notch_long"), 1e-6);
  check_close(highpass(in_signal(fx("filtfilt_highpass_long")), 500.0), fx("filtfilt_highpass_long"), 1e-6);
  check_close(lowpass(in_signal(fx("filtfilt_lowpass_long")), 500.0), fx("filtfilt_lowpass_long"), 1e-6);
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement `filtfilt` (odd padding + zi, per Global Constraints) and the 4 wrappers** with the exact `< 16` fallbacks (`bandpass`/`highpass`: `arr - median(arr)`; `lowpass`/`notch`: `arr` unchanged). `bandpass` builds `Coeffs` via `butter_bandpass`, `highpass` via `butter_highpass`, etc., then `filtfilt`.

- [ ] **Step 4: Wire CMake, build, run.** Iterate until all 6 filtfilt fixtures pass to 1e-6 and the tiny fallback to 1e-9. If `filtfilt_bandpass_long` is off only near the edges, the padding (odd extension) or `padlen` is wrong; if it's off everywhere by a scale, `lfilter_zi` is wrong.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/dsp/Filtfilt.h core/src/dsp/Filtfilt.cpp core/CMakeLists.txt tests/cpp/test_filtfilt.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P5a filtfilt + bandpass/highpass/lowpass/notch wrappers vs golden 1e-6"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P5 DSP-filter scope):
- butter coefficient parity (bandpass/highpass/lowpass) → Task 1 ✓
- iirnotch coefficient parity → Task 2 ✓
- lfilter/lfilter_zi → Task 3 ✓
- filtfilt + the public wrappers + `<16` fallback → Task 4 ✓
- R-peak / HR / PQRST / quality / spectrum → **P5b/P5c** (out of scope here; they sit on these filters)
- GUI SNR strip + display-filter backfill → **P5d** (out of scope here)

**2. Placeholder scan:** Tasks 1, 3 Step 3 describe the SciPy algorithm (spelled out concretely in the Global Constraints) rather than transcribing 200 lines of complex-arithmetic C++, because the algorithm IS the spec and the 1e-12/1e-6 golden fixtures are the authoritative gate. Every test body, every interface signature, the iirnotch closed form (Task 2), and the exact target coefficient values are concrete.

**3. Type consistency:** `Coeffs{b,a}` and `Zpk{z,p,k}` (Task 1) used by Tasks 2–4. `butter_bandpass/highpass/lowpass` (Task 1), `iirnotch` (Task 2), `lfilter`/`lfilter_zi` (Task 3) all consumed by `filtfilt`/`bandpass`/… (Task 4). The wrapper names + defaults match `signal_processing.py`.

**Risk notes for the executor:**
- The single hardest item is `butter` to 1e-12. Work it incrementally: first get `butter_lowpass` (order 2, simplest — no lp2bp doubling) matching, then `butter_highpass`, then `butter_bandpass` (lp2bp doubles to order 4). A wrong prewarp constant (`4·tan(π·Wn/2)`) or a `bilinear_zpk` gain term is the usual culprit.
- `filtfilt`'s odd padding must use `padlen = 3·(ntaps−1)` and SciPy's odd-extension formula exactly; an off-by-one in the extension shifts the whole edge.
- `lfilter_zi` is subtle — validate it standalone (Task 3's no-transient step test) BEFORE relying on it inside `filtfilt`.
- Keep everything in `double`; do not introduce `float` anywhere in the chain or the 1e-12 coefficient match will fail.
