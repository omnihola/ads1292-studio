# P2a: CSV I/O Parity (live + raw) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the Python raw-CSV oracle output as a golden fixture, then implement the portable C++ `io` CSV reader/writer (live + raw) so it reproduces the Python CSV formats byte-for-byte — verified by round-trip byte-identity against the committed golden CSV files plus an independent parsed-field check.

**Architecture:** A new `io/` static library (`ads1292_io`, pure C++17, depends on `core`, no Qt/OS) holds the CSV format constants and the four functions `write_recording_csv` / `read_recording_csv` (live) and `write_raw_recording_csv` / `read_raw_recording_csv` (raw). A small `Calibration` model is added to `core` (the raw CSV's calibration-derived columns need it). The first task is Python-only: it extends the existing fixture generator to freeze a raw-CSV golden file (P-1 only froze the live CSV). C++ parity tests load the committed golden CSVs and prove read→write round-trips to byte-identical output.

**Tech Stack:** C++17, CMake, Catch2 + nlohmann/json (already vendored), the existing Python `ads1292_studio` oracle (`csv_io.py`, `calibration.py`) run in the `sensor` conda env. No new third-party deps.

## Global Constraints

- **C++17**; `core/` and `io/` are pure portable C++ — only the C++ standard library, no Qt, no OS APIs. (`io` MAY use third-party libs in later phases, but CSV needs none.)
- **Layering**: `io → core`, `tests → io, core`. `core` depends on nothing.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored — never commit it.
- **Build/test command** (every C++ task):
  ```bash
  CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
  cmake --build build -j
  ctest --test-dir build --output-on-failure
  ```
- **Python oracle command** (Task 1 only): `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor`.
- **CSV byte-format parity is the bar.** The committed golden CSVs were written by Python `csv.writer` (`newline=""`), so they use **`\r\n` (CRLF) line endings**, comma delimiter, and no quoting (all fields are numbers or the bareword `raw_adc_24bit` / `ADS1292 default`, none of which need quoting). The C++ writer MUST emit `\r\n` and identical value formatting:
  - live timestamp: `%.6f` (6 fixed decimals); live ints: plain decimal.
  - raw timestamp: `%.6f`; raw `ch1_uv`/`ch2_uv`: `%.17g`; `vref_mv`/`pga_gain`: `%g`; `adc_bits`: int; `raw_lsb_uv_per_count`: `%.9f`; `acquisition_mode`: the literal `raw_adc_24bit`.
- **Exact column orders (verbatim from `csv_io.py`):**
  - `CANONICAL_HEADER` (live): `timestamp, sample_index, ch1_counts, ch2_counts, board_heart_rate, board_respiration_rate, status_byte, lead_off_bits`.
  - `RAW_HEADER` (raw): `timestamp, sample_index, ch1_raw24, ch2_raw24, ch1_uv, ch2_uv, status_byte, lead_off_bits, vref_mv, pga_gain, adc_bits, raw_lsb_uv_per_count, acquisition_mode`.
- **Calibration** (from `calibration.py`): fields `vref_mv=2420.0, pga_gain=6.0, adc_bits=24, label="ADS1292 default"`. `normalized()` clamps: `vref_mv>0 else 2420`, `pga_gain>0 else 6`, `adc_bits>=2 else 24`, `label.strip() or "ADS1292 default"`. `microvolts_per_count = normalized.vref_mv * 1000 / (normalized.pga_gain * 2^(normalized.adc_bits-1))`. For the default: `microvolts_per_count == 0.048081080…` (printed `%.9f` → `0.048081080`).
- **lead_off_bits = status_byte & 0x0F** (already in the model structs).

## File Structure

```
io/
  CMakeLists.txt                       # ads1292_io STATIC lib (depends on ads1292_core)
  include/ads1292/io/CsvIo.h
  src/CsvIo.cpp
core/
  include/ads1292/model/Calibration.h  # new
  src/model/Calibration.cpp            # new
  include/ads1292/model/RawSample.h    # modified: add optional ch1_uv/ch2_uv
CMakeLists.txt                         # modified: add_subdirectory(io)
tests/cpp/
  CMakeLists.txt                       # modified: link ads1292_io; add new test files
  test_calibration.cpp
  test_csv_live.cpp
  test_csv_raw.cpp
scripts/                               # Python (Task 1 only)
  gen_file_fixtures.py                 # modified: also write raw_recording.csv + sidecar
  validate_golden_fixtures.py          # modified: register file_csv_raw sidecar keys
tests/fixtures/golden/files/           # Task 1 output
  raw_recording.csv                    # new committed golden
  raw_recording_sidecar.json           # new committed sidecar
```

---

### Task 1: Freeze the raw-CSV golden fixture (Python, no C++)

**Files:**
- Modify: `scripts/gen_file_fixtures.py` (add a raw-CSV section to `generate`)
- Modify: `scripts/validate_golden_fixtures.py` (register `file_csv_raw` in `FILE_SIDECAR_KEYS`)
- Create (generated): `tests/fixtures/golden/files/raw_recording.csv`, `tests/fixtures/golden/files/raw_recording_sidecar.json`

**Interfaces:**
- Consumes: `ads1292_studio.csv_io.write_raw_recording_csv`, `ads1292_studio.models.RawSample`, `ads1292_studio.calibration.Calibration`.
- Produces: committed `raw_recording.csv` + `raw_recording_sidecar.json` (category `file_csv_raw`).

- [ ] **Step 1: Write the failing generator test**

In `tests/test_gen_file_fixtures.py`, add a new test (do not weaken the existing one):

```python
def test_freezes_raw_csv_semantic(tmp_path: Path):
    generate(tmp_path)
    files_dir = tmp_path / "files"
    assert (files_dir / "raw_recording.csv").exists()
    raw = load_fixture(files_dir / "raw_recording_sidecar.json")
    assert raw["category"] == "file_csv_raw"
    assert raw["csv_header"][0] == "timestamp"
    assert "ch1_raw24" in raw["csv_header"]
    assert raw["csv_header"][-1] == "acquisition_mode"
    assert raw["row_count"] == 50
    # the calibration-derived columns are constant per row
    assert raw["csv_first_rows"][0][-1] == "raw_adc_24bit"
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_file_fixtures.py::test_freezes_raw_csv_semantic -v`
Expected: FAIL (no `raw_recording.csv` produced yet).

- [ ] **Step 3: Add the raw-CSV section to the generator**

In `scripts/gen_file_fixtures.py`, add these imports near the existing imports:

```python
import csv as _csv
from ads1292_studio.csv_io import write_raw_recording_csv
from ads1292_studio.models import RawSample
from ads1292_studio.calibration import Calibration
```

Then, inside `generate(root)`, after the XLSX block and before `return written`, insert:

```python
    # --- raw CSV: freeze header + first/last rows (text level), default calibration ---
    raw_samples = tuple(
        RawSample(
            timestamp=round(i / SR, 6),
            sample_index=i,
            ch1_raw24=int(round(signal[i])) * 10,
            ch2_raw24=-int(round(signal[i])) * 5,
            status_byte=(i % 16),
        )
        for i in range(50)
    )
    raw_csv_path = out / "raw_recording.csv"
    write_raw_recording_csv(raw_csv_path, raw_samples, calibration=Calibration())
    with raw_csv_path.open() as fh:
        raw_rows = list(_csv.reader(fh))
    raw_sidecar = out / "raw_recording_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_csv_raw", "name": "raw_recording",
        "oracle": {"function": "ads1292_studio.csv_io.write_raw_recording_csv"},
        "csv_header": raw_rows[0],
        "csv_first_rows": raw_rows[1:6],
        "csv_last_row": raw_rows[-1],
        "row_count": len(raw_rows) - 1,
        "tolerance": {"kind": "text"},
        "notes": "raw CSV header + value formatting (CRLF, %.17g uv, %g vref/pga, %.9f lsb) frozen at text level; default Calibration",
    }, raw_sidecar)
    written += [raw_csv_path, raw_sidecar]
```

- [ ] **Step 4: Register the new sidecar category in the validator**

In `scripts/validate_golden_fixtures.py`, add a `file_csv_raw` entry to `FILE_SIDECAR_KEYS`:

```python
FILE_SIDECAR_KEYS = {
    "file_csv_live": ("csv_header", "csv_first_rows"),
    "file_csv_raw": ("csv_header", "csv_first_rows"),
    "file_hdf5": ("artifact", "datasets", "attrs"),
    "file_xlsx": ("artifact", "sheet_names", "events_header", "point_event_row",
                  "interval_event_row", "data_header", "data_first_row", "data_last_row"),
}
```

- [ ] **Step 5: Run the generator test + regenerate the committed tree + validate**

Run:
```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_file_fixtures.py -v
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m scripts.generate_golden_fixtures
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m scripts.validate_golden_fixtures tests/fixtures/golden
```
Expected: the new test passes; `all golden fixtures valid`. Verify the new file is CRLF: `tr -cd '\r' < tests/fixtures/golden/files/raw_recording.csv | wc -c` must be `51` (1 header + 50 rows).

- [ ] **Step 6: Commit**

```bash
git add scripts/gen_file_fixtures.py scripts/validate_golden_fixtures.py tests/test_gen_file_fixtures.py tests/fixtures/golden/files/raw_recording.csv tests/fixtures/golden/files/raw_recording_sidecar.json
git commit -m "feat: P2a freeze raw-CSV golden fixture + validator support"
```

---

### Task 2: Calibration model (core)

**Files:**
- Create: `core/include/ads1292/model/Calibration.h`, `core/src/model/Calibration.cpp`
- Modify: `core/CMakeLists.txt` (add `src/model/Calibration.cpp`)
- Create test: `tests/cpp/test_calibration.cpp`
- Modify: `tests/cpp/CMakeLists.txt` (add `test_calibration.cpp`)

**Interfaces:**
- Consumes: nothing.
- Produces: `struct ads1292::Calibration { double vref_mv=2420.0; double pga_gain=6.0; int adc_bits=24; std::string label="ADS1292 default"; Calibration normalized() const; double microvolts_per_count() const; }`.

- [ ] **Step 1: Write the failing test**

```cpp
// tests/cpp/test_calibration.cpp
#include "catch.hpp"
#include "ads1292/model/Calibration.h"

using ads1292::Calibration;

TEST_CASE("default Calibration microvolts_per_count matches the oracle", "[model]") {
  Calibration c;
  // 2420*1000 / (6 * 2^23) = 0.04808108..., printed %.9f -> 0.048081080
  REQUIRE(c.microvolts_per_count() == Approx(0.048081080).margin(1e-9));
}

TEST_CASE("Calibration normalized clamps invalid values", "[model]") {
  Calibration bad{-1.0, 0.0, 1, "   "};
  Calibration n = bad.normalized();
  REQUIRE(n.vref_mv == Approx(2420.0));
  REQUIRE(n.pga_gain == Approx(6.0));
  REQUIRE(n.adc_bits == 24);
  REQUIRE(n.label == "ADS1292 default");
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5`
Expected: build FAILS — `Calibration.h` not found / test not listed.

- [ ] **Step 3: Write the Calibration header**

```cpp
// core/include/ads1292/model/Calibration.h
#pragma once
#include <string>

namespace ads1292 {
struct Calibration {
  double vref_mv = 2420.0;
  double pga_gain = 6.0;
  int adc_bits = 24;
  std::string label = "ADS1292 default";

  Calibration normalized() const;
  double microvolts_per_count() const;
};
}  // namespace ads1292
```

- [ ] **Step 4: Write Calibration.cpp**

```cpp
// core/src/model/Calibration.cpp
#include "ads1292/model/Calibration.h"
#include <cctype>
#include <cmath>

namespace ads1292 {
namespace {
std::string strip(const std::string& s) {
  size_t b = 0, e = s.size();
  while (b < e && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
  while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) --e;
  return s.substr(b, e - b);
}
}  // namespace

Calibration Calibration::normalized() const {
  Calibration out;
  out.vref_mv = vref_mv > 0 ? vref_mv : 2420.0;
  out.pga_gain = pga_gain > 0 ? pga_gain : 6.0;
  out.adc_bits = adc_bits >= 2 ? adc_bits : 24;
  std::string trimmed = strip(label);
  out.label = trimmed.empty() ? "ADS1292 default" : trimmed;
  return out;
}

double Calibration::microvolts_per_count() const {
  Calibration n = normalized();
  double full_scale_counts = std::pow(2.0, static_cast<double>(n.adc_bits - 1));
  return n.vref_mv * 1000.0 / (n.pga_gain * full_scale_counts);
}
}  // namespace ads1292
```

- [ ] **Step 5: Wire CMake**

In `core/CMakeLists.txt`, add `src/model/Calibration.cpp` to the `ads1292_core` source list.
In `tests/cpp/CMakeLists.txt`, add `test_calibration.cpp` to the `ads1292_tests` source list.

- [ ] **Step 6: Build and run**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j && ctest --test-dir build --output-on-failure`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add core/include/ads1292/model/Calibration.h core/src/model/Calibration.cpp core/CMakeLists.txt tests/cpp/test_calibration.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P2a Calibration model (microvolts_per_count, normalized)"
```

---

### Task 3: io library + live CSV read/write + round-trip parity

**Files:**
- Create: `io/CMakeLists.txt`, `io/include/ads1292/io/CsvIo.h`, `io/src/CsvIo.cpp`
- Modify: `CMakeLists.txt` (add `add_subdirectory(io)` after `add_subdirectory(core)`)
- Modify: `tests/cpp/CMakeLists.txt` (link `ads1292_io`; add `test_csv_live.cpp`)
- Create test: `tests/cpp/test_csv_live.cpp`

**Interfaces:**
- Consumes: `ads1292::StreamSample`.
- Produces (in `namespace ads1292::io`):
  - `void write_recording_csv(const std::string& path, const std::vector<StreamSample>& samples)`.
  - `std::vector<StreamSample> read_recording_csv(const std::string& path)`.
  - `extern const std::vector<std::string> CANONICAL_HEADER;`

- [ ] **Step 1: Write the failing live-CSV parity test**

```cpp
// tests/cpp/test_csv_live.cpp
#include "catch.hpp"
#include "ads1292/io/CsvIo.h"
#include <fstream>
#include <sstream>
#include <string>

namespace {
std::string read_file(const std::string& path) {
  std::ifstream in(path, std::ios::binary);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}
const std::string kLiveCsv = std::string(FIXTURE_DIR) + "/files/live_recording.csv";
}  // namespace

TEST_CASE("read_recording_csv parses the golden live CSV", "[csv]") {
  auto samples = ads1292::io::read_recording_csv(kLiveCsv);
  REQUIRE(samples.size() == 50);
  // first data row of the golden file: timestamp 0.000000, sample_index 0
  REQUIRE(samples[0].timestamp == Approx(0.0).margin(1e-9));
  REQUIRE(samples[0].sample_index.has_value());
  REQUIRE(samples[0].sample_index.value() == 0);
}

TEST_CASE("live CSV round-trips to byte-identical output", "[csv]") {
  auto samples = ads1292::io::read_recording_csv(kLiveCsv);
  const std::string out = std::string(FIXTURE_DIR) + "/files/_rt_live.csv";
  ads1292::io::write_recording_csv(out, samples);
  REQUIRE(read_file(out) == read_file(kLiveCsv));
  std::remove(out.c_str());
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5`
Expected: build FAILS — `CsvIo.h` not found / `ads1292_io` target missing.

- [ ] **Step 3: Write the io header**

```cpp
// io/include/ads1292/io/CsvIo.h
#pragma once
#include <string>
#include <vector>
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/RawSample.h"
#include "ads1292/model/Calibration.h"

namespace ads1292 {
namespace io {

extern const std::vector<std::string> CANONICAL_HEADER;
extern const std::vector<std::string> RAW_HEADER;

void write_recording_csv(const std::string& path, const std::vector<StreamSample>& samples);
std::vector<StreamSample> read_recording_csv(const std::string& path);

void write_raw_recording_csv(const std::string& path, const std::vector<RawSample>& samples,
                             const Calibration& calibration);
std::vector<RawSample> read_raw_recording_csv(const std::string& path);

}  // namespace io
}  // namespace ads1292
```

- [ ] **Step 4: Write the io source (live functions now; raw functions are stubs filled in Task 4)**

```cpp
// io/src/CsvIo.cpp
#include "ads1292/io/CsvIo.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace ads1292 {
namespace io {

const std::vector<std::string> CANONICAL_HEADER = {
    "timestamp", "sample_index", "ch1_counts", "ch2_counts",
    "board_heart_rate", "board_respiration_rate", "status_byte", "lead_off_bits"};

const std::vector<std::string> RAW_HEADER = {
    "timestamp", "sample_index", "ch1_raw24", "ch2_raw24", "ch1_uv", "ch2_uv",
    "status_byte", "lead_off_bits", "vref_mv", "pga_gain", "adc_bits",
    "raw_lsb_uv_per_count", "acquisition_mode"};

namespace {
std::string fmt(const char* spec, double v) {
  char buf[64];
  std::snprintf(buf, sizeof(buf), spec, v);
  return std::string(buf);
}

std::vector<std::string> split_csv_line(const std::string& line) {
  // The golden CSVs never quote (all fields are numbers or barewords without
  // commas), so a plain comma split is exact. Trailing '\r' is stripped.
  std::vector<std::string> out;
  std::string field;
  std::istringstream ss(line);
  while (std::getline(ss, field, ',')) {
    if (!field.empty() && field.back() == '\r') field.pop_back();
    out.push_back(field);
  }
  return out;
}

int header_index(const std::vector<std::string>& header, const std::string& name) {
  for (size_t i = 0; i < header.size(); ++i)
    if (header[i] == name) return static_cast<int>(i);
  return -1;
}

std::string cell(const std::vector<std::string>& row, int idx) {
  return (idx >= 0 && idx < static_cast<int>(row.size())) ? row[idx] : std::string();
}
}  // namespace

void write_recording_csv(const std::string& path, const std::vector<StreamSample>& samples) {
  std::ofstream out(path, std::ios::binary);
  if (!out) throw std::runtime_error("cannot open for write: " + path);
  // header + CRLF
  for (size_t i = 0; i < CANONICAL_HEADER.size(); ++i) {
    out << CANONICAL_HEADER[i];
    if (i + 1 < CANONICAL_HEADER.size()) out << ',';
  }
  out << "\r\n";
  int row_index = 0;
  for (const auto& s : samples) {
    int idx = s.sample_index.has_value() ? s.sample_index.value() : row_index;
    out << fmt("%.6f", s.timestamp) << ','
        << idx << ','
        << s.ch1 << ','
        << s.ch2 << ','
        << s.board_heart_rate << ','
        << s.board_respiration_rate << ','
        << s.status_byte << ','
        << s.lead_off_bits() << "\r\n";
    ++row_index;
  }
}

std::vector<StreamSample> read_recording_csv(const std::string& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("cannot open for read: " + path);
  std::string line;
  if (!std::getline(in, line)) return {};
  std::vector<std::string> header = split_csv_line(line);
  int ts = header_index(header, "timestamp");
  int idx = header_index(header, "sample_index");
  int ch1 = header_index(header, "ch1_counts");
  int ch2 = header_index(header, "ch2_counts");
  int hr = header_index(header, "board_heart_rate");
  int rr = header_index(header, "board_respiration_rate");
  int status = header_index(header, "status_byte");
  int lead = header_index(header, "lead_off_bits");

  std::vector<StreamSample> samples;
  int row_index = 0;
  while (std::getline(in, line)) {
    if (line.empty() || line == "\r") continue;
    std::vector<std::string> row = split_csv_line(line);
    StreamSample s;
    s.timestamp = cell(row, ts).empty() ? 0.0 : std::stod(cell(row, ts));
    s.ch1 = cell(row, ch1).empty() ? 0 : static_cast<int>(std::stod(cell(row, ch1)));
    s.ch2 = cell(row, ch2).empty() ? 0 : static_cast<int>(std::stod(cell(row, ch2)));
    s.board_heart_rate = cell(row, hr).empty() ? 0 : static_cast<int>(std::stod(cell(row, hr)));
    s.board_respiration_rate = cell(row, rr).empty() ? 0 : static_cast<int>(std::stod(cell(row, rr)));
    int status_byte = cell(row, status).empty() ? 0 : static_cast<int>(std::stod(cell(row, status)));
    std::string lead_cell = cell(row, lead);
    if (!lead_cell.empty()) {
      status_byte = (status_byte & ~0x0F) | (static_cast<int>(std::stod(lead_cell)) & 0x0F);
    }
    s.status_byte = status_byte;
    std::string idx_cell = cell(row, idx);
    s.sample_index = idx_cell.empty() ? row_index : static_cast<int>(std::stod(idx_cell));
    samples.push_back(s);
    ++row_index;
  }
  return samples;
}

// --- raw CSV functions: implemented in Task 4 ---
void write_raw_recording_csv(const std::string&, const std::vector<RawSample>&, const Calibration&) {
  throw std::runtime_error("write_raw_recording_csv not implemented");
}
std::vector<RawSample> read_raw_recording_csv(const std::string&) {
  throw std::runtime_error("read_raw_recording_csv not implemented");
}

}  // namespace io
}  // namespace ads1292
```

- [ ] **Step 5: Write io/CMakeLists.txt and wire it in**

```cmake
# io/CMakeLists.txt
add_library(ads1292_io STATIC
  src/CsvIo.cpp)
target_include_directories(ads1292_io PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(ads1292_io PUBLIC ads1292_core)
```

In the top-level `CMakeLists.txt`, add `add_subdirectory(io)` immediately after `add_subdirectory(core)`.

In `tests/cpp/CMakeLists.txt`: add `ads1292_io` to the `target_link_libraries(ads1292_tests ...)` list, and add `test_csv_live.cpp` to the `add_executable` source list.

- [ ] **Step 6: Build and run**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j && ctest --test-dir build --output-on-failure`
Expected: PASS — the live CSV reads (50 samples) and round-trips byte-identical to the committed golden file.

- [ ] **Step 7: Commit**

```bash
git add io CMakeLists.txt tests/cpp/CMakeLists.txt tests/cpp/test_csv_live.cpp
git commit -m "feat: P2a io library + live CSV read/write with round-trip parity"
```

---

### Task 4: Raw CSV read/write + round-trip parity

**Files:**
- Modify: `core/include/ads1292/model/RawSample.h` (add optional `ch1_uv`/`ch2_uv`)
- Modify: `io/src/CsvIo.cpp` (replace the two raw stubs with real implementations)
- Create test: `tests/cpp/test_csv_raw.cpp`
- Modify: `tests/cpp/CMakeLists.txt` (add `test_csv_raw.cpp`)

**Interfaces:**
- Consumes: `ads1292::RawSample` (now with optional uv fields), `ads1292::Calibration`.
- Produces: working `ads1292::io::write_raw_recording_csv` / `read_raw_recording_csv`.

- [ ] **Step 1: Write the failing raw-CSV parity test**

```cpp
// tests/cpp/test_csv_raw.cpp
#include "catch.hpp"
#include "ads1292/io/CsvIo.h"
#include "ads1292/model/Calibration.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {
std::string read_file(const std::string& path) {
  std::ifstream in(path, std::ios::binary);
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}
const std::string kRawCsv = std::string(FIXTURE_DIR) + "/files/raw_recording.csv";
}  // namespace

TEST_CASE("read_raw_recording_csv parses the golden raw CSV", "[csv]") {
  auto samples = ads1292::io::read_raw_recording_csv(kRawCsv);
  REQUIRE(samples.size() == 50);
  REQUIRE(samples[0].sample_index == 0);
  REQUIRE(samples[0].ch1_uv.has_value());
}

TEST_CASE("raw CSV round-trips to byte-identical output", "[csv]") {
  auto samples = ads1292::io::read_raw_recording_csv(kRawCsv);
  const std::string out = std::string(FIXTURE_DIR) + "/files/_rt_raw.csv";
  ads1292::io::write_raw_recording_csv(out, samples, ads1292::Calibration());
  REQUIRE(read_file(out) == read_file(kRawCsv));
  std::remove(out.c_str());
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j && ctest --test-dir build --output-on-failure 2>&1 | tail -15`
Expected: the raw cases FAIL — the stubs throw `not implemented`.

- [ ] **Step 3: Add optional uv fields to RawSample**

Replace `core/include/ads1292/model/RawSample.h` with:

```cpp
// core/include/ads1292/model/RawSample.h
#pragma once
#include <optional>

namespace ads1292 {
struct RawSample {
  double timestamp = 0.0;
  int sample_index = 0;
  int ch1_raw24 = 0;
  int ch2_raw24 = 0;
  int status_byte = 0;
  std::optional<double> ch1_uv;
  std::optional<double> ch2_uv;
  int lead_off_bits() const { return status_byte & 0x0F; }
};
}  // namespace ads1292
```

(The device acquire parser from P1 sets `ch1_raw24`/`ch2_raw24`/`status_byte`/`sample_index`/`timestamp` and leaves the new optionals unset — no parser change needed; `std::optional` defaults to empty.)

- [ ] **Step 4: Implement the raw CSV functions**

In `io/src/CsvIo.cpp`, replace the two raw stub functions with:

```cpp
void write_raw_recording_csv(const std::string& path, const std::vector<RawSample>& samples,
                             const Calibration& calibration) {
  std::ofstream out(path, std::ios::binary);
  if (!out) throw std::runtime_error("cannot open for write: " + path);
  for (size_t i = 0; i < RAW_HEADER.size(); ++i) {
    out << RAW_HEADER[i];
    if (i + 1 < RAW_HEADER.size()) out << ',';
  }
  out << "\r\n";
  Calibration n = calibration.normalized();
  double scale = n.microvolts_per_count();
  for (const auto& s : samples) {
    double ch1_uv = s.ch1_uv.has_value() ? s.ch1_uv.value() : s.ch1_raw24 * scale;
    double ch2_uv = s.ch2_uv.has_value() ? s.ch2_uv.value() : s.ch2_raw24 * scale;
    out << fmt("%.6f", s.timestamp) << ','
        << s.sample_index << ','
        << s.ch1_raw24 << ','
        << s.ch2_raw24 << ','
        << fmt("%.17g", ch1_uv) << ','
        << fmt("%.17g", ch2_uv) << ','
        << s.status_byte << ','
        << s.lead_off_bits() << ','
        << fmt("%g", n.vref_mv) << ','
        << fmt("%g", n.pga_gain) << ','
        << n.adc_bits << ','
        << fmt("%.9f", n.microvolts_per_count()) << ','
        << "raw_adc_24bit" << "\r\n";
  }
}

std::vector<RawSample> read_raw_recording_csv(const std::string& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("cannot open for read: " + path);
  std::string line;
  if (!std::getline(in, line)) return {};
  std::vector<std::string> header = split_csv_line(line);
  int ts = header_index(header, "timestamp");
  int idx = header_index(header, "sample_index");
  int ch1 = header_index(header, "ch1_raw24");
  int ch2 = header_index(header, "ch2_raw24");
  int ch1uv = header_index(header, "ch1_uv");
  int ch2uv = header_index(header, "ch2_uv");
  int status = header_index(header, "status_byte");
  int lead = header_index(header, "lead_off_bits");

  std::vector<RawSample> samples;
  while (std::getline(in, line)) {
    if (line.empty() || line == "\r") continue;
    std::vector<std::string> row = split_csv_line(line);
    RawSample s;
    s.timestamp = cell(row, ts).empty() ? 0.0 : std::stod(cell(row, ts));
    s.sample_index = cell(row, idx).empty() ? 0 : static_cast<int>(std::stod(cell(row, idx)));
    s.ch1_raw24 = cell(row, ch1).empty() ? 0 : static_cast<int>(std::stod(cell(row, ch1)));
    s.ch2_raw24 = cell(row, ch2).empty() ? 0 : static_cast<int>(std::stod(cell(row, ch2)));
    if (!cell(row, ch1uv).empty()) s.ch1_uv = std::stod(cell(row, ch1uv));
    if (!cell(row, ch2uv).empty()) s.ch2_uv = std::stod(cell(row, ch2uv));
    int status_byte = cell(row, status).empty() ? 0 : static_cast<int>(std::stod(cell(row, status)));
    std::string lead_cell = cell(row, lead);
    if (!lead_cell.empty()) {
      status_byte = (status_byte & 0xFFF0) | (static_cast<int>(std::stod(lead_cell)) & 0x0F);
    }
    s.status_byte = status_byte;
    samples.push_back(s);
  }
  return samples;
}
```

- [ ] **Step 5: Wire the test into CMake**

In `tests/cpp/CMakeLists.txt`, add `test_csv_raw.cpp` to the `add_executable` source list.

- [ ] **Step 6: Build and run the full suite**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j && ctest --test-dir build --output-on-failure`
Expected: PASS — raw CSV reads 50 samples and round-trips byte-identical to the committed golden file (the `%.17g` / `%g` / `%.9f` formatting reproduces Python's exactly).

- [ ] **Step 7: Commit**

```bash
git add core/include/ads1292/model/RawSample.h io/src/CsvIo.cpp tests/cpp/CMakeLists.txt tests/cpp/test_csv_raw.cpp
git commit -m "feat: P2a raw CSV read/write with byte-identical round-trip parity"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P2 CSV scope):
- live CSV read/write parity → Task 3 ✓
- raw CSV read/write parity → Task 4 ✓ (needs the Task 1 fixture)
- raw-CSV golden fixture (P-1 deferred it) → Task 1 ✓
- Calibration (raw CSV calibration columns) → Task 2 ✓
- HDF5 + recording_bundle → **out of scope here** (P2b/P2c, per the agreed P2 decomposition). Flagged, not built.

**2. Placeholder scan:** No "TBD/handle edge cases". The raw-CSV stubs in Task 3 are an explicit TDD RED bridge (they throw a named error) replaced in Task 4 — bodies shown, not elided.

**3. Type consistency:** `ads1292::io::{write,read}_recording_csv` and `{write,read}_raw_recording_csv` signatures match between the Task 3 header and the Task 3/4 implementations and tests. `Calibration` (Task 2) field/method names (`vref_mv`, `pga_gain`, `adc_bits`, `normalized()`, `microvolts_per_count()`) match the Task 4 raw writer usage. `RawSample.ch1_uv/ch2_uv` (Task 4 model change) match the Task 4 reader/writer.

**Risk note for the executor:**
- Byte-identity of the raw CSV hinges on C++ `snprintf("%.17g"/"%g"/"%.9f", …)` producing the same strings as Python's `f"{x:.17g}"` / `f"{x:g}"` / `f"{x:.9f}"`. These share C `printf` semantics and should match for IEEE-754 doubles; the round-trip test (read the exact double Python wrote, reformat) is what proves it. If a mismatch appears, diff the two files to find the offending column/format and report it — do NOT relax the test to a parsed comparison.
