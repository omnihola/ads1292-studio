# P0 + P1: C++ Skeleton + Core Model + Device Parser — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the C++/Qt build skeleton (CMake + Catch2 + vendored deps + an empty black-theme Qt window) and the first portable `core` code — the data model, byte decoders, and the ADS1x9x device frame parsers — verified bit-for-bit against the frozen `device_parser` golden fixtures.

**Architecture:** A CMake project rooted at the repo top (coexisting with the existing Python package). A `core/` static library holds pure-C++17 model structs (`StreamSample`/`RawSample`/`EventMarker`), byte decoders, and the frame parsers (`parse_stream_payload`/`parse_acquire_payload`) — zero Qt, zero OS APIs. A `gui/` Qt Widgets executable renders an empty dark window. C++ unit tests (Catch2) live in `tests/cpp/` and load the JSON golden fixtures (via vendored nlohmann/json) to prove the parsers reproduce the Python oracle exactly.

**Tech Stack:** C++17, CMake (≥3.21; installed 4.3.4), Catch2 v2.13.10 (vendored single header), nlohmann/json v3.11.3 (vendored single header), Qt6 Widgets (Homebrew at `/opt/homebrew/opt/qt`). Apple clang.

## Global Constraints

- **C++17**, no compiler extensions: `set(CMAKE_CXX_STANDARD 17)` + `CMAKE_CXX_STANDARD_REQUIRED ON` + `CMAKE_CXX_EXTENSIONS OFF`.
- **`core/` is pure portable C++**: it MUST NOT include any Qt header, any `<QtCore>`/`<QtWidgets>`, or any macOS/POSIX-only API. Only the C++ standard library. (This keeps it cross-compilable to embedded later.)
- **Layering**: `gui → core`, `tests → core`. `core` depends on nothing but libc++.
- **Vendored single-header deps only** under `third_party/`: `catch2/catch.hpp` (v2.13.10), `nlohmann/json.hpp` (v3.11.3). No network fetch at configure/build time.
- **Qt discovery**: builds set `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt`. Qt is found via `find_package(Qt6 REQUIRED COMPONENTS Widgets)`.
- **Build dir** is `build/` (already in `.gitignore`). Never commit build artifacts.
- **Fixture parity is the acceptance bar** for the parsers: integer sample fields and `lead_off_bits` compare with EXACT equality; the `double` `timestamp` compares within abs `1e-9` (the fixtures' `tolerance.kind == "exact"` targets the integer fields; floating timestamps use a 1e-9 margin which is exact in practice). Error fixtures (`output.raises == "ValueError"`) must make the C++ parser THROW with a message containing `output.message_contains`.
- **Single canonical build/test command** (used in every task's verify step):
  ```bash
  CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
  cmake --build build -j
  ctest --test-dir build --output-on-failure
  ```
- **Oracle behavior copied verbatim** from `src/ads1292_studio/device.py` and `models.py`/`events.py` — the C++ must match these semantics:
  - stream payload: `len >= 61`; trailer = last 2 bytes ∈ {`03 03`, `03 0A`}; header bytes `[hr, resp, status]`; 14 samples at offset `3 + i*4`, `ch1=int16_le(b[base],b[base+1])`, `ch2=int16_le(b[base+2],b[base+3])`; `timestamp = round(start_ts + (start_index+i)/sr, 6)`; stream samples leave `sample_index` UNSET.
  - acquire payload: `len >= 51`; trailer = last byte `== 0x03`; `status_byte = (b[0]<<8)|b[1]` (16-bit word); 8 samples at offset `2 + i*6`, `ch1_raw24=int24_be(b[base..base+2])`, `ch2_raw24=int24_be(b[base+3..base+5])`; `sample_index = start_index + i`; `timestamp = round(start_ts + sample_index/sr, 6)`.
  - `int16_le(lo,hi)`: `v=(hi<<8)|lo; if v&0x8000: v-=0x10000`.
  - `int24_be(b0,b1,b2)`: `v=(b0<<16)|(b1<<8)|b2; if v&0x800000: v-=0x1000000`.
  - `lead_off_bits = status_byte & 0x0F`.
  - `EventMarker.normalized()`: `timestamp=max(0,ts)`, `duration=max(0,dur)`, `label=strip(label) or "event"`, `notes=strip(notes)`. `end_seconds = normalized.timestamp + normalized.duration`.

---

## File Structure

```
CMakeLists.txt                      # top-level: project, std, options, subdirs
third_party/
  CMakeLists.txt                    # INTERFACE targets: catch2, nlohmann_json
  catch2/catch.hpp                  # vendored Catch2 v2.13.10 single header
  nlohmann/json.hpp                 # vendored nlohmann/json v3.11.3 single header
core/
  CMakeLists.txt                    # ads1292_core STATIC lib
  include/ads1292/model/StreamSample.h
  include/ads1292/model/RawSample.h
  include/ads1292/model/EventMarker.h
  include/ads1292/device/ByteDecode.h
  include/ads1292/device/AdsParser.h
  include/ads1292/core_version.h
  src/core_version.cpp
  src/model/EventMarker.cpp
  src/device/AdsParser.cpp
gui/
  CMakeLists.txt                    # ads1292_gui executable (Qt Widgets)
  src/main.cpp
  src/MainWindow.h
  src/MainWindow.cpp
  resources/resources.qrc
  resources/dark.qss
tests/cpp/
  CMakeLists.txt                    # ads1292_tests executable
  test_main.cpp                     # the ONE TU with CATCH_CONFIG_MAIN
  test_smoke.cpp
  FixtureLoader.h
  FixtureLoader.cpp
  test_event_marker.cpp
  test_byte_decode.cpp
  test_device_parser_stream.cpp
  test_device_parser_acquire.cpp
scripts/
  cpp-build-test.sh                 # configure + build + ctest
```

The existing Python `tests/` and `src/` are untouched. The C++ tests read the committed fixtures under `tests/fixtures/golden/` via a compile-time `FIXTURE_DIR` define.

---

### Task 1: CMake skeleton + vendored deps + Catch2 smoke

**Files:**
- Create: `CMakeLists.txt`
- Create: `third_party/CMakeLists.txt`
- Create (vendored, downloaded): `third_party/catch2/catch.hpp`, `third_party/nlohmann/json.hpp`
- Create: `core/CMakeLists.txt`, `core/include/ads1292/core_version.h`, `core/src/core_version.cpp`
- Create: `tests/cpp/CMakeLists.txt`, `tests/cpp/test_main.cpp`, `tests/cpp/test_smoke.cpp`
- Create: `scripts/cpp-build-test.sh`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - CMake targets `ads1292_core` (STATIC), `catch2` (INTERFACE), `nlohmann_json` (INTERFACE), `ads1292_tests` (executable + ctest `ads1292_tests`).
  - `ads1292::core_version() -> const char*` returning `"0.1.0"`.
  - Compile define `FIXTURE_DIR` available to `ads1292_tests` = absolute path to `tests/fixtures/golden`.

- [ ] **Step 1: Vendor the two single-header dependencies**

```bash
mkdir -p third_party/catch2 third_party/nlohmann
curl -fsSL https://github.com/catchorg/Catch2/releases/download/v2.13.10/catch.hpp -o third_party/catch2/catch.hpp
curl -fsSL https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp -o third_party/nlohmann/json.hpp
# sanity: both files are large single headers
wc -l third_party/catch2/catch.hpp third_party/nlohmann/json.hpp
```
Expected: `catch.hpp` ~17k lines, `json.hpp` ~24k lines. If either is tiny (an HTML error page), the download failed — retry.

- [ ] **Step 2: Write the top-level CMakeLists.txt**

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.21)
project(ads1292_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(ADS1292_BUILD_GUI "Build the Qt GUI" ON)
option(ADS1292_BUILD_TESTS "Build C++ tests" ON)

add_subdirectory(third_party)
add_subdirectory(core)

if(ADS1292_BUILD_GUI)
  add_subdirectory(gui)
endif()

if(ADS1292_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests/cpp)
endif()
```

- [ ] **Step 3: Write third_party/CMakeLists.txt**

```cmake
# third_party/CMakeLists.txt
add_library(catch2 INTERFACE)
target_include_directories(catch2 INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/catch2)

add_library(nlohmann_json INTERFACE)
target_include_directories(nlohmann_json INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})
```

- [ ] **Step 4: Write the core library skeleton**

```cpp
// core/include/ads1292/core_version.h
#pragma once
namespace ads1292 {
const char* core_version();
}
```

```cpp
// core/src/core_version.cpp
#include "ads1292/core_version.h"
namespace ads1292 {
const char* core_version() { return "0.1.0"; }
}
```

```cmake
# core/CMakeLists.txt
add_library(ads1292_core STATIC
  src/core_version.cpp)
target_include_directories(ads1292_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
```

- [ ] **Step 5: Write the Catch2 main TU and a smoke test**

```cpp
// tests/cpp/test_main.cpp
#define CATCH_CONFIG_MAIN
#include "catch.hpp"
```

```cpp
// tests/cpp/test_smoke.cpp
#include "catch.hpp"
#include "ads1292/core_version.h"
#include "nlohmann/json.hpp"

TEST_CASE("core links and reports its version", "[smoke]") {
    REQUIRE(std::string(ads1292::core_version()) == "0.1.0");
}

TEST_CASE("nlohmann json is available", "[smoke]") {
    auto j = nlohmann::json::parse("{\"a\":1}");
    REQUIRE(j.at("a").get<int>() == 1);
}
```

```cmake
# tests/cpp/CMakeLists.txt
add_executable(ads1292_tests
  test_main.cpp
  test_smoke.cpp)
target_link_libraries(ads1292_tests PRIVATE ads1292_core catch2 nlohmann_json)
target_compile_definitions(ads1292_tests PRIVATE
  FIXTURE_DIR="${CMAKE_SOURCE_DIR}/tests/fixtures/golden")
add_test(NAME ads1292_tests COMMAND ads1292_tests)
```

- [ ] **Step 6: Write the build script**

```bash
# scripts/cpp-build-test.sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CMAKE_PREFIX_PATH="${CMAKE_PREFIX_PATH:-/opt/homebrew/opt/qt}"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j
ctest --test-dir build --output-on-failure
```

```bash
chmod +x scripts/cpp-build-test.sh
```

- [ ] **Step 7: Configure, build, and run the smoke tests**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j
ctest --test-dir build --output-on-failure
```
Expected: configure succeeds, `ads1292_tests` builds, ctest reports `100% tests passed, 0 tests failed out of 1` (the Catch2 binary is one ctest test running 2 assertions-cases).

- [ ] **Step 8: Commit**

```bash
git add CMakeLists.txt third_party core/CMakeLists.txt core/include core/src tests/cpp scripts/cpp-build-test.sh
git commit -m "feat: P0 C++ build skeleton (CMake + Catch2 + nlohmann) with core smoke test"
```

---

### Task 2: Empty Qt black-theme window

**Files:**
- Create: `gui/CMakeLists.txt`, `gui/src/main.cpp`, `gui/src/MainWindow.h`, `gui/src/MainWindow.cpp`, `gui/resources/resources.qrc`, `gui/resources/dark.qss`

**Interfaces:**
- Consumes: nothing (the empty window does not yet use `core`).
- Produces: executable `ads1292_gui`; accepts a `--smoke` flag that quits immediately after construction (so it can be checked headlessly with `QT_QPA_PLATFORM=offscreen`).

- [ ] **Step 1: Write the dark stylesheet and resource file**

```css
/* gui/resources/dark.qss */
QWidget { background-color: #0d0d0f; color: #e6e6e6; font-size: 13px; }
QMainWindow { background-color: #0d0d0f; }
QLabel#TitleLabel { color: #e6e6e6; font-size: 20px; font-weight: 600; }
```

```xml
<!-- gui/resources/resources.qrc -->
<RCC>
  <qresource prefix="/">
    <file>dark.qss</file>
  </qresource>
</RCC>
```

- [ ] **Step 2: Write the MainWindow**

```cpp
// gui/src/MainWindow.h
#pragma once
#include <QMainWindow>

namespace ads1292 {
class MainWindow : public QMainWindow {
  Q_OBJECT
public:
  explicit MainWindow(QWidget* parent = nullptr);
};
}  // namespace ads1292
```

```cpp
// gui/src/MainWindow.cpp
#include "MainWindow.h"
#include <QLabel>

namespace ads1292 {
MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {
  setWindowTitle("ADS1292 Studio");
  resize(1100, 700);
  auto* title = new QLabel("ADS1292 Studio", this);
  title->setObjectName("TitleLabel");
  title->setAlignment(Qt::AlignCenter);
  setCentralWidget(title);
}
}  // namespace ads1292
```

- [ ] **Step 3: Write main.cpp with a headless --smoke path**

```cpp
// gui/src/main.cpp
#include <QApplication>
#include <QFile>
#include <QString>
#include <QTimer>
#include "MainWindow.h"

static QString loadStyle() {
  QFile f(":/dark.qss");
  if (f.open(QFile::ReadOnly | QFile::Text)) {
    return QString::fromUtf8(f.readAll());
  }
  return QString();
}

int main(int argc, char** argv) {
  QApplication app(argc, argv);
  app.setStyleSheet(loadStyle());

  ads1292::MainWindow window;
  window.show();

  bool smoke = false;
  for (int i = 1; i < argc; ++i) {
    if (QString::fromLocal8Bit(argv[i]) == QStringLiteral("--smoke")) {
      smoke = true;
    }
  }
  if (smoke) {
    QTimer::singleShot(0, &app, &QApplication::quit);
  }
  return app.exec();
}
```

- [ ] **Step 4: Write gui/CMakeLists.txt**

```cmake
# gui/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Widgets)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)

add_executable(ads1292_gui
  src/main.cpp
  src/MainWindow.cpp
  src/MainWindow.h
  resources/resources.qrc)
target_link_libraries(ads1292_gui PRIVATE Qt6::Widgets)
```

- [ ] **Step 5: Build and headlessly smoke-test the window**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j
QT_QPA_PLATFORM=offscreen ./build/gui/ads1292_gui --smoke ; echo "exit=$?"
```
Expected: builds; the `--smoke` run constructs the window offscreen and exits with `exit=0` (no display needed). Without `--smoke` and on a real display it would show a black window titled "ADS1292 Studio".

- [ ] **Step 6: Commit**

```bash
git add gui CMakeLists.txt
git commit -m "feat: P0 empty Qt Widgets black-theme main window with headless smoke flag"
```

---

### Task 3: Core model structs + EventMarker behavior

**Files:**
- Create: `core/include/ads1292/model/StreamSample.h`, `core/include/ads1292/model/RawSample.h`, `core/include/ads1292/model/EventMarker.h`, `core/src/model/EventMarker.cpp`
- Modify: `core/CMakeLists.txt` (add `src/model/EventMarker.cpp`)
- Create test: `tests/cpp/test_event_marker.cpp`
- Modify: `tests/cpp/CMakeLists.txt` (add `test_event_marker.cpp`)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `struct ads1292::StreamSample { double timestamp; int ch1, ch2, board_heart_rate, board_respiration_rate, status_byte; std::optional<int> sample_index; int lead_off_bits() const; }`
  - `struct ads1292::RawSample { double timestamp; int sample_index; int ch1_raw24, ch2_raw24, status_byte; int lead_off_bits() const; }`
  - `struct ads1292::EventMarker { double timestamp_seconds; std::string label; std::string notes; double duration_seconds; EventMarker normalized() const; double end_seconds() const; bool is_interval() const; }`

- [ ] **Step 1: Write the failing EventMarker test**

```cpp
// tests/cpp/test_event_marker.cpp
#include "catch.hpp"
#include "ads1292/model/EventMarker.h"

using ads1292::EventMarker;

TEST_CASE("EventMarker normalizes negatives, trims, and defaults label", "[model]") {
  EventMarker e{-1.0, "  ", "  hi  ", -2.0};
  EventMarker n = e.normalized();
  REQUIRE(n.timestamp_seconds == Approx(0.0));
  REQUIRE(n.duration_seconds == Approx(0.0));
  REQUIRE(n.label == "event");   // empty/whitespace label -> "event"
  REQUIRE(n.notes == "hi");      // notes trimmed
}

TEST_CASE("EventMarker end_seconds and is_interval", "[model]") {
  EventMarker point{2.0, "touch", "", 0.0};
  REQUIRE(point.end_seconds() == Approx(2.0));
  REQUIRE_FALSE(point.is_interval());

  EventMarker range{2.0, "motion", "", 0.5};
  REQUIRE(range.end_seconds() == Approx(2.5));
  REQUIRE(range.is_interval());
}
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5
```
Expected: build FAILS — `tests/cpp/CMakeLists.txt` doesn't yet list `test_event_marker.cpp` and `EventMarker.h` doesn't exist. (After Step 3–4 wire-up it will compile.)

- [ ] **Step 3: Write the model headers**

```cpp
// core/include/ads1292/model/StreamSample.h
#pragma once
#include <optional>

namespace ads1292 {
struct StreamSample {
  double timestamp = 0.0;
  int ch1 = 0;
  int ch2 = 0;
  int board_heart_rate = 0;
  int board_respiration_rate = 0;
  int status_byte = 0;
  std::optional<int> sample_index;  // unset for stream frames (matches Python)
  int lead_off_bits() const { return status_byte & 0x0F; }
};
}  // namespace ads1292
```

```cpp
// core/include/ads1292/model/RawSample.h
#pragma once

namespace ads1292 {
struct RawSample {
  double timestamp = 0.0;
  int sample_index = 0;
  int ch1_raw24 = 0;
  int ch2_raw24 = 0;
  int status_byte = 0;
  int lead_off_bits() const { return status_byte & 0x0F; }
};
}  // namespace ads1292
```

```cpp
// core/include/ads1292/model/EventMarker.h
#pragma once
#include <string>

namespace ads1292 {
struct EventMarker {
  double timestamp_seconds = 0.0;
  std::string label = "event";
  std::string notes;
  double duration_seconds = 0.0;

  EventMarker normalized() const;
  double end_seconds() const;
  bool is_interval() const;
};
}  // namespace ads1292
```

- [ ] **Step 4: Write EventMarker.cpp**

```cpp
// core/src/model/EventMarker.cpp
#include "ads1292/model/EventMarker.h"
#include <algorithm>
#include <cctype>

namespace ads1292 {
namespace {
std::string strip(const std::string& s) {
  size_t b = 0, e = s.size();
  while (b < e && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
  while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) --e;
  return s.substr(b, e - b);
}
}  // namespace

EventMarker EventMarker::normalized() const {
  EventMarker out;
  out.timestamp_seconds = std::max(0.0, timestamp_seconds);
  out.duration_seconds = std::max(0.0, duration_seconds);
  std::string trimmed_label = strip(label);
  out.label = trimmed_label.empty() ? "event" : trimmed_label;
  out.notes = strip(notes);
  return out;
}

double EventMarker::end_seconds() const {
  EventMarker n = normalized();
  return n.timestamp_seconds + n.duration_seconds;
}

bool EventMarker::is_interval() const {
  return normalized().duration_seconds > 0.0;
}
}  // namespace ads1292
```

- [ ] **Step 5: Wire the new sources into CMake**

In `core/CMakeLists.txt`, change the `add_library` source list to:
```cmake
add_library(ads1292_core STATIC
  src/core_version.cpp
  src/model/EventMarker.cpp)
```

In `tests/cpp/CMakeLists.txt`, change the `add_executable` source list to:
```cmake
add_executable(ads1292_tests
  test_main.cpp
  test_smoke.cpp
  test_event_marker.cpp)
```

- [ ] **Step 6: Build and run tests**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j
ctest --test-dir build --output-on-failure
```
Expected: PASS (the `[model]` cases pass alongside the smoke cases).

- [ ] **Step 7: Commit**

```bash
git add core/include/ads1292/model core/src/model core/CMakeLists.txt tests/cpp/test_event_marker.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P1 core model structs and EventMarker normalization"
```

---

### Task 4: Byte decoders (int16 LE / int24 BE)

**Files:**
- Create: `core/include/ads1292/device/ByteDecode.h`
- Create test: `tests/cpp/test_byte_decode.cpp`
- Modify: `tests/cpp/CMakeLists.txt` (add `test_byte_decode.cpp`)

**Interfaces:**
- Consumes: nothing.
- Produces (header-only, `inline`):
  - `int ads1292::int16_le(uint8_t lo, uint8_t hi)` — signed 16-bit little-endian.
  - `int ads1292::int24_be(uint8_t b0, uint8_t b1, uint8_t b2)` — signed 24-bit big-endian.

- [ ] **Step 1: Write the failing decoder test**

```cpp
// tests/cpp/test_byte_decode.cpp
#include "catch.hpp"
#include "ads1292/device/ByteDecode.h"

using ads1292::int16_le;
using ads1292::int24_be;

TEST_CASE("int16_le decodes signed little-endian", "[decode]") {
  REQUIRE(int16_le(0x64, 0x00) == 100);      // 0x0064
  REQUIRE(int16_le(0x38, 0xFF) == -200);     // 0xFF38 -> -200
  REQUIRE(int16_le(0x00, 0x80) == -32768);   // most-negative
  REQUIRE(int16_le(0xFF, 0x7F) == 32767);    // most-positive
}

TEST_CASE("int24_be decodes signed big-endian", "[decode]") {
  REQUIRE(int24_be(0x00, 0x03, 0xE8) == 1000);     // 0x0003E8
  REQUIRE(int24_be(0xFF, 0xF8, 0x30) == -2000);    // 0xFFF830 -> -2000
  REQUIRE(int24_be(0x80, 0x00, 0x00) == -8388608); // most-negative
  REQUIRE(int24_be(0x7F, 0xFF, 0xFF) == 8388607);  // most-positive
}
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5
```
Expected: build FAILS — `ByteDecode.h` not found / `test_byte_decode.cpp` not yet listed.

- [ ] **Step 3: Write the decoders**

```cpp
// core/include/ads1292/device/ByteDecode.h
#pragma once
#include <cstdint>

namespace ads1292 {
// Signed 16-bit little-endian from (lo, hi). Mirrors Python device._int16_le.
inline int int16_le(uint8_t lo, uint8_t hi) {
  int value = (static_cast<int>(hi) << 8) | static_cast<int>(lo);
  if (value & 0x8000) value -= 0x10000;
  return value;
}

// Signed 24-bit big-endian from (b0, b1, b2). Mirrors Python device._int24_be.
inline int int24_be(uint8_t b0, uint8_t b1, uint8_t b2) {
  int value = (static_cast<int>(b0) << 16) | (static_cast<int>(b1) << 8) |
              static_cast<int>(b2);
  if (value & 0x800000) value -= 0x1000000;
  return value;
}
}  // namespace ads1292
```

- [ ] **Step 4: Wire test into CMake**

In `tests/cpp/CMakeLists.txt`, add `test_byte_decode.cpp` to the `add_executable` source list:
```cmake
add_executable(ads1292_tests
  test_main.cpp
  test_smoke.cpp
  test_event_marker.cpp
  test_byte_decode.cpp)
```

- [ ] **Step 5: Build and run tests**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j
ctest --test-dir build --output-on-failure
```
Expected: PASS (the `[decode]` cases pass).

- [ ] **Step 6: Commit**

```bash
git add core/include/ads1292/device/ByteDecode.h tests/cpp/test_byte_decode.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P1 signed int16-LE / int24-BE byte decoders"
```

---

### Task 5: JSON device-fixture loader

**Files:**
- Create: `tests/cpp/FixtureLoader.h`, `tests/cpp/FixtureLoader.cpp`
- Create test: (assertions added into `test_smoke.cpp` is NOT allowed; create) `tests/cpp/test_fixture_loader.cpp`
- Modify: `tests/cpp/CMakeLists.txt` (add `FixtureLoader.cpp`, `test_fixture_loader.cpp`)

**Interfaces:**
- Consumes: `nlohmann/json.hpp`, compile define `FIXTURE_DIR`.
- Produces:
  - `std::vector<uint8_t> ads1292test::hex_to_bytes(const std::string& hex)`.
  - `struct ads1292test::DeviceFixture { std::string name; std::vector<uint8_t> payload; double start_timestamp; double sample_rate_hz; int start_index; bool expects_error; std::string error_message_contains; nlohmann::json expected_samples; };`
  - `DeviceFixture ads1292test::load_device_fixture(const std::string& relpath)` — `relpath` is relative to `FIXTURE_DIR` (e.g. `"device_parser/stream_payload_nominal.json"`).

- [ ] **Step 1: Write the failing loader test**

```cpp
// tests/cpp/test_fixture_loader.cpp
#include "catch.hpp"
#include "FixtureLoader.h"

using ads1292test::hex_to_bytes;
using ads1292test::load_device_fixture;

TEST_CASE("hex_to_bytes parses byte pairs", "[fixture]") {
  auto b = hex_to_bytes("0293ff");
  REQUIRE(b.size() == 3);
  REQUIRE(b[0] == 0x02);
  REQUIRE(b[1] == 0x93);
  REQUIRE(b[2] == 0xff);
}

TEST_CASE("loads a nominal stream device fixture", "[fixture]") {
  auto fx = load_device_fixture("device_parser/stream_payload_nominal.json");
  REQUIRE(fx.name == "stream_payload_nominal");
  REQUIRE(fx.payload.size() == 61);
  REQUIRE(fx.sample_rate_hz == Approx(500.0));
  REQUIRE(fx.start_index == 0);
  REQUIRE_FALSE(fx.expects_error);
  REQUIRE(fx.expected_samples.size() == 14);
}

TEST_CASE("loads an error device fixture", "[fixture]") {
  auto fx = load_device_fixture("device_parser/stream_bad_trailer.json");
  REQUIRE(fx.expects_error);
  REQUIRE(fx.error_message_contains == "trailer");
}
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5
```
Expected: build FAILS — `FixtureLoader.h` not found.

- [ ] **Step 3: Write the loader header**

```cpp
// tests/cpp/FixtureLoader.h
#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "nlohmann/json.hpp"

namespace ads1292test {

std::vector<uint8_t> hex_to_bytes(const std::string& hex);

struct DeviceFixture {
  std::string name;
  std::vector<uint8_t> payload;
  double start_timestamp = 0.0;
  double sample_rate_hz = 0.0;
  int start_index = 0;
  bool expects_error = false;
  std::string error_message_contains;
  nlohmann::json expected_samples;  // JSON array; empty when expects_error
};

// relpath is relative to FIXTURE_DIR, e.g. "device_parser/stream_payload_nominal.json".
DeviceFixture load_device_fixture(const std::string& relpath);

}  // namespace ads1292test
```

- [ ] **Step 4: Write the loader implementation**

```cpp
// tests/cpp/FixtureLoader.cpp
#include "FixtureLoader.h"
#include <fstream>
#include <stdexcept>

namespace ads1292test {

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
  if (hex.size() % 2 != 0) {
    throw std::invalid_argument("hex string has odd length");
  }
  std::vector<uint8_t> out;
  out.reserve(hex.size() / 2);
  for (size_t i = 0; i < hex.size(); i += 2) {
    out.push_back(static_cast<uint8_t>(std::stoul(hex.substr(i, 2), nullptr, 16)));
  }
  return out;
}

DeviceFixture load_device_fixture(const std::string& relpath) {
  std::string full = std::string(FIXTURE_DIR) + "/" + relpath;
  std::ifstream in(full);
  if (!in) {
    throw std::runtime_error("cannot open fixture: " + full);
  }
  nlohmann::json j;
  in >> j;

  DeviceFixture fx;
  fx.name = j.at("name").get<std::string>();
  const auto& input = j.at("input");
  fx.payload = hex_to_bytes(input.at("payload_hex").get<std::string>());
  fx.start_timestamp = input.at("start_timestamp").get<double>();
  fx.sample_rate_hz = input.at("sample_rate_hz").get<double>();
  fx.start_index = input.at("start_index").get<int>();

  const auto& output = j.at("output");
  if (output.contains("raises")) {
    fx.expects_error = true;
    fx.error_message_contains = output.at("message_contains").get<std::string>();
  } else {
    fx.expects_error = false;
    fx.expected_samples = output.at("samples");
  }
  return fx;
}

}  // namespace ads1292test
```

- [ ] **Step 5: Wire into CMake**

In `tests/cpp/CMakeLists.txt`, add `FixtureLoader.cpp` and `test_fixture_loader.cpp` to the `add_executable` source list:
```cmake
add_executable(ads1292_tests
  test_main.cpp
  test_smoke.cpp
  test_event_marker.cpp
  test_byte_decode.cpp
  FixtureLoader.cpp
  test_fixture_loader.cpp)
```

- [ ] **Step 6: Build and run tests**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j
ctest --test-dir build --output-on-failure
```
Expected: PASS (the `[fixture]` cases load the committed golden fixtures via `FIXTURE_DIR`).

- [ ] **Step 7: Commit**

```bash
git add tests/cpp/FixtureLoader.h tests/cpp/FixtureLoader.cpp tests/cpp/test_fixture_loader.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P1 JSON golden device-fixture loader for C++ parity tests"
```

---

### Task 6: parse_stream_payload + stream fixture parity

**Files:**
- Create: `core/include/ads1292/device/AdsParser.h`, `core/src/device/AdsParser.cpp`
- Modify: `core/CMakeLists.txt` (add `src/device/AdsParser.cpp`)
- Create test: `tests/cpp/test_device_parser_stream.cpp`
- Modify: `tests/cpp/CMakeLists.txt` (add `test_device_parser_stream.cpp`)

**Interfaces:**
- Consumes: `ByteDecode.h`, `StreamSample.h`, `RawSample.h`, `FixtureLoader.h`.
- Produces:
  - `struct ads1292::AdsParseError : std::invalid_argument` (carries the message).
  - `std::vector<ads1292::StreamSample> ads1292::parse_stream_payload(const std::vector<uint8_t>& payload, double start_timestamp, double sample_rate_hz, int start_index)`.
  - (Declared now, implemented in Task 7) `std::vector<ads1292::RawSample> ads1292::parse_acquire_payload(const std::vector<uint8_t>& payload, double start_timestamp, double sample_rate_hz, int start_index)`.

- [ ] **Step 1: Write the failing stream-parity test**

```cpp
// tests/cpp/test_device_parser_stream.cpp
#include "catch.hpp"
#include "ads1292/device/AdsParser.h"
#include "FixtureLoader.h"

using ads1292::parse_stream_payload;
using ads1292::AdsParseError;
using ads1292test::load_device_fixture;

namespace {
void check_stream_against_fixture(const std::string& relpath) {
  auto fx = load_device_fixture(relpath);
  auto got = parse_stream_payload(fx.payload, fx.start_timestamp,
                                  fx.sample_rate_hz, fx.start_index);
  REQUIRE(got.size() == fx.expected_samples.size());
  for (size_t i = 0; i < got.size(); ++i) {
    const auto& exp = fx.expected_samples[i];
    INFO("sample " << i << " in " << relpath);
    CHECK(got[i].ch1 == exp.at("ch1").get<int>());
    CHECK(got[i].ch2 == exp.at("ch2").get<int>());
    CHECK(got[i].board_heart_rate == exp.at("board_heart_rate").get<int>());
    CHECK(got[i].board_respiration_rate == exp.at("board_respiration_rate").get<int>());
    CHECK(got[i].status_byte == exp.at("status_byte").get<int>());
    CHECK(got[i].lead_off_bits() == exp.at("lead_off_bits").get<int>());
    CHECK(got[i].timestamp == Approx(exp.at("timestamp").get<double>()).margin(1e-9));
    CHECK(exp.at("sample_index").is_null());
    CHECK_FALSE(got[i].sample_index.has_value());
  }
}
}  // namespace

TEST_CASE("parse_stream_payload reproduces the nominal stream fixture", "[parser]") {
  check_stream_against_fixture("device_parser/stream_payload_nominal.json");
}

TEST_CASE("parse_stream_payload throws on a bad trailer", "[parser]") {
  auto fx = load_device_fixture("device_parser/stream_bad_trailer.json");
  REQUIRE(fx.expects_error);
  REQUIRE_THROWS_WITH(
      parse_stream_payload(fx.payload, fx.start_timestamp, fx.sample_rate_hz, fx.start_index),
      Catch::Contains(fx.error_message_contains));
}

TEST_CASE("parse_stream_payload throws on a too-short payload", "[parser]") {
  auto fx = load_device_fixture("device_parser/stream_too_short.json");
  REQUIRE(fx.expects_error);
  REQUIRE_THROWS_WITH(
      parse_stream_payload(fx.payload, fx.start_timestamp, fx.sample_rate_hz, fx.start_index),
      Catch::Contains(fx.error_message_contains));
}
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5
```
Expected: build FAILS — `AdsParser.h` not found.

- [ ] **Step 3: Write the parser header**

```cpp
// core/include/ads1292/device/AdsParser.h
#pragma once
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
#include "ads1292/model/StreamSample.h"
#include "ads1292/model/RawSample.h"

namespace ads1292 {

// Thrown for malformed frames (mirrors Python's ValueError on bad payloads).
struct AdsParseError : std::invalid_argument {
  explicit AdsParseError(const std::string& msg) : std::invalid_argument(msg) {}
};

std::vector<StreamSample> parse_stream_payload(const std::vector<uint8_t>& payload,
                                               double start_timestamp,
                                               double sample_rate_hz,
                                               int start_index);

std::vector<RawSample> parse_acquire_payload(const std::vector<uint8_t>& payload,
                                             double start_timestamp,
                                             double sample_rate_hz,
                                             int start_index);

}  // namespace ads1292
```

- [ ] **Step 4: Write parse_stream_payload (and a stub for parse_acquire_payload)**

```cpp
// core/src/device/AdsParser.cpp
#include "ads1292/device/AdsParser.h"
#include <cmath>
#include "ads1292/device/ByteDecode.h"

namespace ads1292 {
namespace {
constexpr uint8_t kEnd = 0x03;
constexpr uint8_t kStreamTrailerLf = 0x0A;

// round-half-to-even-ish at 6 decimals; matches Python round(x, 6) for the
// exact decimal timestamps produced here (no halfway cases at 1e-6).
double round6(double x) { return std::round(x * 1e6) / 1e6; }
}  // namespace

std::vector<StreamSample> parse_stream_payload(const std::vector<uint8_t>& payload,
                                               double start_timestamp,
                                               double sample_rate_hz,
                                               int start_index) {
  if (payload.size() < 61) {
    throw AdsParseError("stream payload too short: " + std::to_string(payload.size()) +
                        " bytes");
  }
  uint8_t t0 = payload[payload.size() - 2];
  uint8_t t1 = payload[payload.size() - 1];
  bool trailer_ok = (t0 == kEnd && t1 == kEnd) || (t0 == kEnd && t1 == kStreamTrailerLf);
  if (!trailer_ok) {
    throw AdsParseError("bad stream trailer");
  }
  const int board_heart_rate = payload[0];
  const int board_respiration_rate = payload[1];
  const int status_byte = payload[2];

  std::vector<StreamSample> samples;
  samples.reserve(14);
  for (int i = 0; i < 14; ++i) {
    const size_t base = 3 + static_cast<size_t>(i) * 4;
    StreamSample s;
    s.timestamp = round6(start_timestamp +
                         static_cast<double>(start_index + i) / sample_rate_hz);
    s.ch1 = int16_le(payload[base], payload[base + 1]);
    s.ch2 = int16_le(payload[base + 2], payload[base + 3]);
    s.board_heart_rate = board_heart_rate;
    s.board_respiration_rate = board_respiration_rate;
    s.status_byte = status_byte;
    // sample_index intentionally left unset (matches Python stream parser)
    samples.push_back(s);
  }
  return samples;
}

std::vector<RawSample> parse_acquire_payload(const std::vector<uint8_t>& /*payload*/,
                                             double /*start_timestamp*/,
                                             double /*sample_rate_hz*/,
                                             int /*start_index*/) {
  // Implemented in Task 7.
  throw AdsParseError("parse_acquire_payload not implemented");
}

}  // namespace ads1292
```

> Note on the trailer message: the Python message is `f"bad stream trailer: {hex}"`; the fixture only requires the substring `"trailer"`, so the shorter C++ message `"bad stream trailer"` satisfies parity. Likewise `"stream payload too short: N bytes"` contains `"too short"`.

- [ ] **Step 5: Wire into CMake**

In `core/CMakeLists.txt`, add `src/device/AdsParser.cpp`:
```cmake
add_library(ads1292_core STATIC
  src/core_version.cpp
  src/model/EventMarker.cpp
  src/device/AdsParser.cpp)
```

In `tests/cpp/CMakeLists.txt`, add `test_device_parser_stream.cpp`:
```cmake
add_executable(ads1292_tests
  test_main.cpp
  test_smoke.cpp
  test_event_marker.cpp
  test_byte_decode.cpp
  FixtureLoader.cpp
  test_fixture_loader.cpp
  test_device_parser_stream.cpp)
```

- [ ] **Step 6: Build and run tests**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j
ctest --test-dir build --output-on-failure
```
Expected: PASS — the stream nominal fixture's 14 samples match field-for-field, and both error fixtures throw with the expected substring.

- [ ] **Step 7: Commit**

```bash
git add core/include/ads1292/device/AdsParser.h core/src/device/AdsParser.cpp core/CMakeLists.txt tests/cpp/test_device_parser_stream.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P1 parse_stream_payload with golden stream-fixture parity"
```

---

### Task 7: parse_acquire_payload + acquire fixture parity

**Files:**
- Modify: `core/src/device/AdsParser.cpp` (replace the `parse_acquire_payload` stub with the real implementation)
- Create test: `tests/cpp/test_device_parser_acquire.cpp`
- Modify: `tests/cpp/CMakeLists.txt` (add `test_device_parser_acquire.cpp`)

**Interfaces:**
- Consumes: `ByteDecode.h`, `RawSample.h`, `FixtureLoader.h`, `AdsParseError`.
- Produces: a working `ads1292::parse_acquire_payload` returning `std::vector<RawSample>`.

- [ ] **Step 1: Write the failing acquire-parity test**

```cpp
// tests/cpp/test_device_parser_acquire.cpp
#include "catch.hpp"
#include "ads1292/device/AdsParser.h"
#include "FixtureLoader.h"

using ads1292::parse_acquire_payload;
using ads1292test::load_device_fixture;

TEST_CASE("parse_acquire_payload reproduces the nominal acquire fixture", "[parser]") {
  auto fx = load_device_fixture("device_parser/acquire_payload_nominal.json");
  auto got = parse_acquire_payload(fx.payload, fx.start_timestamp,
                                   fx.sample_rate_hz, fx.start_index);
  REQUIRE(got.size() == fx.expected_samples.size());  // 8 raw samples
  for (size_t i = 0; i < got.size(); ++i) {
    const auto& exp = fx.expected_samples[i];
    INFO("raw sample " << i);
    CHECK(got[i].ch1_raw24 == exp.at("ch1_raw24").get<int>());
    CHECK(got[i].ch2_raw24 == exp.at("ch2_raw24").get<int>());
    CHECK(got[i].status_byte == exp.at("status_byte").get<int>());
    CHECK(got[i].lead_off_bits() == exp.at("lead_off_bits").get<int>());
    CHECK(got[i].sample_index == exp.at("sample_index").get<int>());
    CHECK(got[i].timestamp == Approx(exp.at("timestamp").get<double>()).margin(1e-9));
  }
}

TEST_CASE("parse_acquire_payload throws on a bad trailer", "[parser]") {
  auto fx = load_device_fixture("device_parser/acquire_bad_trailer.json");
  REQUIRE(fx.expects_error);
  REQUIRE_THROWS_WITH(
      parse_acquire_payload(fx.payload, fx.start_timestamp, fx.sample_rate_hz, fx.start_index),
      Catch::Contains(fx.error_message_contains));
}
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j && ctest --test-dir build --output-on-failure 2>&1 | tail -15
```
Expected: the nominal acquire case FAILS — the stub throws `"parse_acquire_payload not implemented"`, so `REQUIRE(got.size()...)` is never reached and the test reports a thrown exception. (The bad-trailer case may accidentally pass against the stub; the nominal case is the real RED.)

- [ ] **Step 3: Implement parse_acquire_payload**

In `core/src/device/AdsParser.cpp`, replace the stub body with:

```cpp
std::vector<RawSample> parse_acquire_payload(const std::vector<uint8_t>& payload,
                                             double start_timestamp,
                                             double sample_rate_hz,
                                             int start_index) {
  if (payload.size() < 51) {
    throw AdsParseError("acquire payload too short: " + std::to_string(payload.size()) +
                        " bytes");
  }
  if (payload.back() != kEnd) {
    throw AdsParseError("bad acquire trailer");
  }
  const int status_byte = (static_cast<int>(payload[0]) << 8) | static_cast<int>(payload[1]);

  std::vector<RawSample> samples;
  samples.reserve(8);
  for (int i = 0; i < 8; ++i) {
    const int sample_index = start_index + i;
    const size_t base = 2 + static_cast<size_t>(i) * 6;
    RawSample s;
    s.timestamp = round6(start_timestamp + static_cast<double>(sample_index) / sample_rate_hz);
    s.sample_index = sample_index;
    s.ch1_raw24 = int24_be(payload[base], payload[base + 1], payload[base + 2]);
    s.ch2_raw24 = int24_be(payload[base + 3], payload[base + 4], payload[base + 5]);
    s.status_byte = status_byte;
    samples.push_back(s);
  }
  return samples;
}
```

(The stub's `#include`s and the `round6`/`kEnd` helpers already exist at the top of the file from Task 6 — no new includes are needed.)

- [ ] **Step 4: Wire test into CMake**

In `tests/cpp/CMakeLists.txt`, add `test_device_parser_acquire.cpp`:
```cmake
add_executable(ads1292_tests
  test_main.cpp
  test_smoke.cpp
  test_event_marker.cpp
  test_byte_decode.cpp
  FixtureLoader.cpp
  test_fixture_loader.cpp
  test_device_parser_stream.cpp
  test_device_parser_acquire.cpp)
```

- [ ] **Step 5: Build and run the full C++ suite**

Run:
```bash
CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j
ctest --test-dir build --output-on-failure
```
Expected: PASS — all five `device_parser` golden fixtures (2 nominal + 3 error) reproduce the Python oracle; the full Catch2 binary is green.

- [ ] **Step 6: Commit**

```bash
git add core/src/device/AdsParser.cpp tests/cpp/test_device_parser_acquire.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P1 parse_acquire_payload with golden acquire-fixture parity"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P0 + P1 acceptance):
- P0 CMake skeleton + Catch2 + empty Qt black window → Tasks 1 (build+Catch2) and 2 (Qt window) ✓
- P1 `parse_stream_payload` parity → Task 6 ✓
- P1 `parse_acquire_payload` parity → Task 7 ✓
- P1 lead-off bits parity → covered in the per-sample checks (`lead_off_bits()`), Tasks 6 & 7 ✓
- P1 malformed / bad-trailer / too-short parity → Tasks 6 (stream bad_trailer, too_short) & 7 (acquire bad_trailer) ✓
- P1 model (`StreamSample`/`RawSample`/`EventMarker`) → Task 3 ✓
- P1 "serialization (JSON·CSV)" parity → **deferred**: there are no P-1 serialization fixtures yet (CSV/JSON serialization belongs with P2 file I/O, where the `file_csv_live`/HDF5 fixtures live). Flagged here; not in scope for P0+P1. The byte-level parse parity (the actual risk for the device layer) IS covered.

**2. Placeholder scan:** No "TBD/TODO/handle edge cases". The Task-6 `parse_acquire_payload` stub is an intentional, explicit TDD RED step (it throws a named error) that Task 7 replaces — its body is shown, not elided.

**3. Type consistency:** `parse_stream_payload`/`parse_acquire_payload` signatures are identical across the header (Task 6), the stub (Task 6), and the implementation (Task 7). `StreamSample`/`RawSample`/`EventMarker` field names match between Task 3 definitions and the Task 6/7 test field accesses (`ch1`, `ch2`, `board_heart_rate`, `board_respiration_rate`, `status_byte`, `lead_off_bits()`, `sample_index`, `ch1_raw24`, `ch2_raw24`). `FixtureLoader` API (`hex_to_bytes`, `DeviceFixture`, `load_device_fixture`) matches between Task 5 definition and Task 6/7 usage. `int16_le`/`int24_be` match between Task 4 and the Task 6/7 parser.

**Known follow-up for the executor:**
- `parse_acquire_payload`'s `acquire_too_short` case has no dedicated fixture in P-1 (only `acquire_bad_trailer` exists); the `len < 51` guard is implemented and unit-coverable but is not asserted by a golden fixture. If desired, add an `acquire_too_short` fixture in a P-1 follow-up; not blocking P0+P1.
