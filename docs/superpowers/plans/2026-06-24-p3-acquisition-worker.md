# P3: Acquisition Worker (simulator first, then QSerialPort) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the P1 frame parsers into a portable acquisition pipeline — a byte-transport-driven ADS1x9x protocol device, a sample queue, and an acquisition engine (live + raw) that enqueues samples and writes the CSV journal — proven end-to-end with a deterministic simulator; then add the Qt runtime layer (QSerialPort transport + a QThread worker) that runs the same engine against a real board.

**Architecture:** Portable core (`core`/`io`, no Qt): `IByteTransport` (raw byte read/write) with a `SimulatorByteTransport`; a portable `AdsProtocolDevice` that implements `IDeviceSource` (start/stop stream, read stream batch, acquire raw) over a transport by re-using P1's `parse_stream_payload`/`parse_acquire_payload`; a thread-safe `SampleQueue`; and an `AcquisitionEngine` that drives an `IDeviceSource` in live or raw mode, pushing samples to the queue and the CSV journal (P2a `CsvIo`). The Qt runtime (`qt_runtime`) adds `QSerialByteTransport` (QSerialPort) and `AcquisitionWorker` (a QThread that runs the engine). The portable parts are unit-tested with simulators; the Qt parts compile and pass a headless smoke driven by the simulator.

**Tech Stack:** C++17, CMake, Qt6 (Widgets + SerialPort), Catch2 (vendored). Re-uses P1 (`AdsParser`), P2a (`CsvIo`), the model structs. No numeric parity fixtures — correctness is structural/behavioral, mirroring Python `workers.py`'s FakeDevice-injected tests.

## Global Constraints

- **C++17**; `core/` and `io/` stay pure portable C++ (the protocol device, simulator, queue, and engine are portable — NO Qt). Only the new `qt_runtime` layer uses Qt (`QSerialPort`, `QThread`).
- **New layer `qt_runtime/`**: depends on `io` + `core` + Qt. Layering: `gui → qt_runtime → io → core`, `qt_runtime → core`. Add `qt_runtime` to the build after `io`.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test command** (HDF5 + Qt on the prefix path):
  ```bash
  CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
  cmake --build build -j
  ctest --test-dir build --output-on-failure
  ```
- **ADS1x9x protocol facts (from `device.py`, verbatim):**
  - `START=0x02`, `END=0x03`. `write_cmd(cmd,p0,p1)` packet = `{START, cmd&0xFF, p0&0xFF, p1&0xFF, END, END, 0x0A}` (7 bytes).
  - Command bytes: `CMD_DATA_STREAMING=0x93`, `CMD_ACQUIRE_DATA=0x94`, `CMD_REG_READ=0x92`, `CMD_QUERY_FIRMWARE_VERSION=0x99`.
  - `read_frame`: read bytes until one equals `START`; the next byte is `frame_type`; then read a payload whose length depends on the type — `0x93`→61, `0x92`/`0x99`→5, `0x94`→51, otherwise→1.
  - Stream: `start_stream()` sends `write_cmd(0x93,0,0)`; `read_stream_sample_batch()` does `read_frame()`, and if `frame_type==0x93 && payload.size()>=61` returns `parse_stream_payload(payload, t0, sr, running_index)` (advancing `running_index` by 14), else returns empty. `stop_stream()` re-sends `write_cmd(0x93,0,0)` (it is a toggle).
  - Raw: `acquire_raw_samples(count)` requires `count>0 && count%8==0`; sends `write_cmd(0x94, count>>8, count&0xFF)`; reads an ACK frame (`frame_type==0x94`, payload≥2, `(payload[0]<<8)|payload[1] == count`); then loops `read_frame()`, and for each `0x94` frame appends `parse_acquire_payload(payload, t0, sr, samples_so_far)` until it has `count` samples.
- **`AcquisitionMode`**: `Live` (stream) and `Raw` (acquire). Mirrors `workers.AcquisitionMode`.
- **No hidden numeric parity** — the device parser numbers were frozen in P1; this phase tests the *plumbing*: frame framing, sample ordering/indices, queue, and CSV journal.

## File Structure

```
core/
  include/ads1292/acq/IByteTransport.h       # read/write raw bytes (abstract)
  include/ads1292/acq/SimulatorByteTransport.h
  src/acq/SimulatorByteTransport.cpp
  include/ads1292/acq/IDeviceSource.h         # start/stop stream, read batch, acquire raw
  include/ads1292/acq/AdsProtocolDevice.h     # IDeviceSource over IByteTransport
  src/acq/AdsProtocolDevice.cpp
  include/ads1292/acq/SimulatorDeviceSource.h
  src/acq/SimulatorDeviceSource.cpp
  include/ads1292/acq/SampleQueue.h           # thread-safe queue (header-only)
io/
  include/ads1292/io/AcquisitionEngine.h      # drives an IDeviceSource -> queue + CSV journal
  src/AcquisitionEngine.cpp
qt_runtime/
  CMakeLists.txt                              # ads1292_qt_runtime static lib (Qt SerialPort + Core)
  include/ads1292/qt/QSerialByteTransport.h
  src/QSerialByteTransport.cpp
  include/ads1292/qt/AcquisitionWorker.h
  src/AcquisitionWorker.cpp
CMakeLists.txt                                # add_subdirectory(qt_runtime)
tests/cpp/
  test_ads_protocol.cpp        # framing: simulator byte transport -> frames/samples
  test_acquisition_engine.cpp  # simulator device -> queue + CSV journal round-trip
  test_acq_worker_smoke.cpp    # qt worker headless smoke (simulator source)
```

---

### Task 1: IByteTransport + SimulatorByteTransport + ADS framing

**Files:**
- Create: `core/include/ads1292/acq/IByteTransport.h`, `core/include/ads1292/acq/SimulatorByteTransport.h`, `core/src/acq/SimulatorByteTransport.cpp`
- Create: `core/include/ads1292/acq/AdsFraming.h`, `core/src/acq/AdsFraming.cpp` (the `write_cmd` packet builder + `read_frame`)
- Modify: `core/CMakeLists.txt`; Create test `tests/cpp/test_ads_protocol.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (in `namespace ads1292::acq`):
  - `class IByteTransport { public: virtual ~IByteTransport()=default; virtual void write(const std::vector<uint8_t>&)=0; virtual std::vector<uint8_t> read(size_t n)=0; };` (`read` returns up to `n` bytes, fewer at end-of-input)
  - `class SimulatorByteTransport : public IByteTransport` — constructed with a canned `std::vector<uint8_t>` of inbound bytes; `read(n)` serves them sequentially, `write` records the last command for assertions (`std::vector<uint8_t> last_written() const`).
  - `std::vector<uint8_t> build_cmd(uint8_t cmd, uint8_t p0, uint8_t p1);` → the 7-byte packet.
  - `struct Frame { uint8_t type; std::vector<uint8_t> payload; bool ok; };`
  - `Frame read_frame(IByteTransport& t);` → scans for `START`, reads type + length-by-type payload; `ok=false` if the stream ends before a full frame.

- [ ] **Step 1: Write the failing framing test**

```cpp
// tests/cpp/test_ads_protocol.cpp
#include "catch.hpp"
#include "ads1292/acq/AdsFraming.h"
#include "ads1292/acq/SimulatorByteTransport.h"
#include "ads1292/device/AdsParser.h"
#include <vector>

using namespace ads1292;
using namespace ads1292::acq;

namespace {
// a valid 61-byte stream payload: 3 header + 14*4 + trailer {0x03,0x03}
std::vector<uint8_t> stream_payload() {
  std::vector<uint8_t> p = {72, 18, 0x05};
  for (int i = 0; i < 14; ++i) { p.push_back(100 + i); p.push_back(0); p.push_back(0x38); p.push_back(0xFF); }
  p.push_back(0x03); p.push_back(0x03);
  return p;
}
}  // namespace

TEST_CASE("build_cmd produces the 7-byte packet", "[acq]") {
  auto pkt = build_cmd(0x93, 0, 0);
  REQUIRE(pkt == std::vector<uint8_t>{0x02, 0x93, 0x00, 0x00, 0x03, 0x03, 0x0A});
}

TEST_CASE("read_frame extracts a stream frame after START", "[acq]") {
  std::vector<uint8_t> bytes = {0xAA, 0x02, 0x93};  // junk, START, type
  auto pl = stream_payload();
  bytes.insert(bytes.end(), pl.begin(), pl.end());
  SimulatorByteTransport t(bytes);
  Frame f = read_frame(t);
  REQUIRE(f.ok);
  REQUIRE(f.type == 0x93);
  REQUIRE(f.payload.size() == 61);
  auto samples = parse_stream_payload(f.payload, 0.0, 500.0, 0);
  REQUIRE(samples.size() == 14);
  REQUIRE(samples[0].ch1 == 100);
}
```

- [ ] **Step 2: Run to verify it fails** — build FAILS (headers missing).

- [ ] **Step 3: Write the transport + framing**

```cpp
// core/include/ads1292/acq/IByteTransport.h
#pragma once
#include <cstdint>
#include <vector>
namespace ads1292 { namespace acq {
class IByteTransport {
 public:
  virtual ~IByteTransport() = default;
  virtual void write(const std::vector<uint8_t>& bytes) = 0;
  virtual std::vector<uint8_t> read(std::size_t n) = 0;  // up to n bytes; fewer at end-of-input
};
}}  // namespace ads1292::acq
```

```cpp
// core/include/ads1292/acq/SimulatorByteTransport.h
#pragma once
#include "ads1292/acq/IByteTransport.h"
namespace ads1292 { namespace acq {
class SimulatorByteTransport : public IByteTransport {
 public:
  explicit SimulatorByteTransport(std::vector<uint8_t> inbound) : inbound_(std::move(inbound)) {}
  void write(const std::vector<uint8_t>& bytes) override { last_written_ = bytes; }
  std::vector<uint8_t> read(std::size_t n) override;
  const std::vector<uint8_t>& last_written() const { return last_written_; }
 private:
  std::vector<uint8_t> inbound_;
  std::size_t pos_ = 0;
  std::vector<uint8_t> last_written_;
};
}}  // namespace ads1292::acq
```

```cpp
// core/src/acq/SimulatorByteTransport.cpp
#include "ads1292/acq/SimulatorByteTransport.h"
namespace ads1292 { namespace acq {
std::vector<uint8_t> SimulatorByteTransport::read(std::size_t n) {
  std::vector<uint8_t> out;
  while (out.size() < n && pos_ < inbound_.size()) out.push_back(inbound_[pos_++]);
  return out;
}
}}  // namespace ads1292::acq
```

```cpp
// core/include/ads1292/acq/AdsFraming.h
#pragma once
#include <cstdint>
#include <vector>
#include "ads1292/acq/IByteTransport.h"
namespace ads1292 { namespace acq {
constexpr uint8_t kStart = 0x02, kEnd = 0x03;
std::vector<uint8_t> build_cmd(uint8_t cmd, uint8_t p0, uint8_t p1);
struct Frame { uint8_t type = 0; std::vector<uint8_t> payload; bool ok = false; };
Frame read_frame(IByteTransport& transport);
}}  // namespace ads1292::acq
```

```cpp
// core/src/acq/AdsFraming.cpp
#include "ads1292/acq/AdsFraming.h"
namespace ads1292 { namespace acq {
namespace {
std::size_t payload_len(uint8_t type) {
  switch (type) { case 0x93: return 61; case 0x92: case 0x99: return 5; case 0x94: return 51; default: return 1; }
}
bool read_one(IByteTransport& t, uint8_t& out) { auto b = t.read(1); if (b.empty()) return false; out = b[0]; return true; }
}  // namespace

std::vector<uint8_t> build_cmd(uint8_t cmd, uint8_t p0, uint8_t p1) {
  return {kStart, cmd, p0, p1, kEnd, kEnd, 0x0A};
}

Frame read_frame(IByteTransport& transport) {
  Frame f;
  uint8_t byte = 0;
  // scan to START
  for (;;) { if (!read_one(transport, byte)) return f; if (byte == kStart) break; }
  if (!read_one(transport, f.type)) return f;
  std::size_t need = payload_len(f.type);
  std::vector<uint8_t> payload = transport.read(need);
  if (payload.size() != need) return f;  // ok stays false on a short read
  f.payload = std::move(payload);
  f.ok = true;
  return f;
}
}}  // namespace ads1292::acq
```

- [ ] **Step 4: Wire CMake (add the 2 sources to core, add the test), build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/acq core/src/acq core/CMakeLists.txt tests/cpp/test_ads_protocol.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P3 ADS byte transport + frame framing (simulator-tested)"
```

---

### Task 2: IDeviceSource + AdsProtocolDevice + SimulatorDeviceSource

**Files:**
- Create: `core/include/ads1292/acq/IDeviceSource.h`, `core/include/ads1292/acq/AdsProtocolDevice.h`, `core/src/acq/AdsProtocolDevice.cpp`, `core/include/ads1292/acq/SimulatorDeviceSource.h`, `core/src/acq/SimulatorDeviceSource.cpp`
- Modify: `core/CMakeLists.txt`; extend `tests/cpp/test_ads_protocol.cpp` (device-level cases); Modify tests CMake if needed.

**Interfaces:**
- Produces (in `namespace ads1292::acq`):
  - `class IDeviceSource { public: virtual ~IDeviceSource()=default; virtual void start_stream()=0; virtual void stop_stream()=0; virtual std::vector<StreamSample> read_stream_batch()=0; virtual std::vector<RawSample> acquire_raw(int count)=0; };`
  - `class AdsProtocolDevice : public IDeviceSource` — ctor `(IByteTransport& t, double sample_rate_hz)`; implements the protocol from the Global Constraints (start/stop via `build_cmd(0x93,...)`; `read_stream_batch` = `read_frame` + `parse_stream_payload` advancing a running index; `acquire_raw` = command + ACK + frame loop + `parse_acquire_payload`).
  - `class SimulatorDeviceSource : public IDeviceSource` — ctor takes the number of stream batches and raw count to emit; `read_stream_batch()` returns a deterministic 14-sample batch (indices advance) until exhausted then empty; `acquire_raw(count)` returns `count` deterministic RawSamples.

- [ ] **Step 1: Write the failing device-level test**

```cpp
// append to tests/cpp/test_ads_protocol.cpp
#include "ads1292/acq/AdsProtocolDevice.h"
#include "ads1292/acq/SimulatorDeviceSource.h"

TEST_CASE("AdsProtocolDevice reads a stream batch from a transport", "[acq]") {
  std::vector<uint8_t> bytes = {0x02, 0x93};
  // reuse the helper stream_payload() from earlier in this file
  auto pl = stream_payload();
  bytes.insert(bytes.end(), pl.begin(), pl.end());
  SimulatorByteTransport t(bytes);
  AdsProtocolDevice dev(t, 500.0);
  dev.start_stream();
  auto batch = dev.read_stream_batch();
  REQUIRE(batch.size() == 14);
  REQUIRE(batch[0].ch1 == 100);
  // start_stream wrote the streaming command
  REQUIRE(t.last_written() == build_cmd(0x93, 0, 0));
}

TEST_CASE("SimulatorDeviceSource yields deterministic batches", "[acq]") {
  SimulatorDeviceSource sim(/*stream_batches=*/3, /*raw_count=*/16);
  int total = 0;
  for (int i = 0; i < 3; ++i) total += static_cast<int>(sim.read_stream_batch().size());
  REQUIRE(total == 42);                 // 3 * 14
  REQUIRE(sim.read_stream_batch().empty());  // exhausted
  REQUIRE(sim.acquire_raw(16).size() == 16);
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Write the interfaces + implementations**

`IDeviceSource.h`, `AdsProtocolDevice.{h,cpp}` (using `AdsFraming`'s `read_frame`/`build_cmd` and `parse_stream_payload`/`parse_acquire_payload`; keep a running `stream_index_` advanced by 14 per non-empty batch and `t0_` set on the first batch), and `SimulatorDeviceSource.{h,cpp}` (deterministic: stream batch `k` has `ch1 = 100 + 14*k + i`, etc.; raw uses `parse`-shaped values). The acquire loop in `AdsProtocolDevice` reads the ACK frame, validates `ack_count == count`, then collects frames until `count` samples (or a short read → throw `AdsParseError` "acquire underrun").

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/acq core/src/acq core/CMakeLists.txt tests/cpp/test_ads_protocol.cpp
git commit -m "feat: P3 AdsProtocolDevice + SimulatorDeviceSource (IDeviceSource)"
```

---

### Task 3: SampleQueue + AcquisitionEngine (live + raw → queue + CSV journal)

**Files:**
- Create: `core/include/ads1292/acq/SampleQueue.h` (header-only, thread-safe)
- Create: `io/include/ads1292/io/AcquisitionEngine.h`, `io/src/AcquisitionEngine.cpp`
- Modify: `io/CMakeLists.txt`; Create test `tests/cpp/test_acquisition_engine.cpp`; Modify tests CMake.

**Interfaces:**
- Produces:
  - `template<class T> class ads1292::acq::SampleQueue` — `push(T)`, `bool try_pop(T&)`, `size()`, mutex-guarded.
  - `namespace ads1292::io`: `struct AcquisitionResult { int sample_count; std::string csv_path; };`
    - `AcquisitionResult run_live(acq::IDeviceSource& dev, acq::SampleQueue<StreamSample>& queue, const std::string& csv_path, std::function<bool()> should_continue);` — calls `start_stream`, loops `read_stream_batch` while `should_continue()` and batches arrive, pushing each sample to `queue` and (if `csv_path` non-empty) the live CSV journal; calls `stop_stream`; returns the count + path.
    - `AcquisitionResult run_raw(acq::IDeviceSource& dev, acq::SampleQueue<RawSample>& queue, const std::string& csv_path, int total_samples, int chunk);` — loops `acquire_raw(chunk)` until `total_samples` collected, pushing to `queue` and the raw CSV journal (default `Calibration`), reindexing samples sequentially.

- [ ] **Step 1: Write the failing engine test**

```cpp
// tests/cpp/test_acquisition_engine.cpp
#include "catch.hpp"
#include "ads1292/io/AcquisitionEngine.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include "ads1292/acq/SampleQueue.h"
#include <cstdio>

using namespace ads1292;

TEST_CASE("run_live drains the simulator into the queue + CSV journal", "[engine]") {
  acq::SimulatorDeviceSource sim(/*stream_batches=*/5, /*raw_count=*/0);
  acq::SampleQueue<StreamSample> q;
  const std::string csv = std::string(FIXTURE_DIR) + "/files/_acq_live.csv";
  auto res = io::run_live(sim, q, csv, [] { return true; });

  REQUIRE(res.sample_count == 70);          // 5 * 14
  REQUIRE(q.size() == 70);
  // the CSV journal round-trips to 70 samples via the P2a reader
  auto reread = io::read_recording_csv(csv);
  REQUIRE(reread.size() == 70);
  // sample indices are sequential 0..69 in the queue
  StreamSample s; int i = 0;
  while (q.try_pop(s)) { REQUIRE(s.sample_index.value_or(-1) == i); ++i; }
  std::remove(csv.c_str());
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Write `SampleQueue.h`, `AcquisitionEngine.{h,cpp}`**

`SampleQueue`: `std::deque<T>` + `std::mutex`. `run_live`: open a `CsvIo` live-journal writer incrementally (or buffer all samples then `write_recording_csv` at the end — buffering is fine for P3 since the simulator is finite; assign `sample_index = running counter`), push each to the queue, stop on `!should_continue()` or an empty batch. `run_raw`: similar with `write_raw_recording_csv`. (The Python worker writes incrementally for crash-safety; for the portable engine + finite simulator, writing the accumulated samples once at stop is acceptable and keeps the engine testable — note this difference in the report.)

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS — 70 samples queued + CSV round-trips.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/acq/SampleQueue.h io/include/ads1292/io/AcquisitionEngine.h io/src/AcquisitionEngine.cpp io/CMakeLists.txt tests/cpp/test_acquisition_engine.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P3 SampleQueue + AcquisitionEngine (live/raw -> queue + CSV journal)"
```

---

### Task 4: qt_runtime — QSerialByteTransport + AcquisitionWorker (QThread) + headless smoke

**Files:**
- Create: `qt_runtime/CMakeLists.txt`, `qt_runtime/include/ads1292/qt/QSerialByteTransport.h`, `qt_runtime/src/QSerialByteTransport.cpp`, `qt_runtime/include/ads1292/qt/AcquisitionWorker.h`, `qt_runtime/src/AcquisitionWorker.cpp`
- Modify: top `CMakeLists.txt` (`add_subdirectory(qt_runtime)`), `tests/cpp/CMakeLists.txt` (link qt_runtime; add the smoke test)
- Create test: `tests/cpp/test_acq_worker_smoke.cpp`

**Interfaces:**
- Produces:
  - `class ads1292::qt::QSerialByteTransport : public acq::IByteTransport` — wraps a `QSerialPort` (opened on a port string at 9600 8N1, timeout); `read(n)` blocks up to a timeout via `waitForReadyRead`, `write` sends + `waitForBytesWritten`. (Compiles; exercised against a real board only.)
  - `class ads1292::qt::AcquisitionWorker : public QObject` — `start(IDeviceSource* dev, mode, csv_path)` moves work to an internal `QThread` that runs `io::run_live`/`run_raw` with a `should_continue` bound to an atomic stop flag; `stop()` sets the flag and joins; samples are exposed via a `SampleQueue` the GUI drains. Emits `finished(int sampleCount)`.

- [ ] **Step 1: Write the failing headless worker smoke test**

```cpp
// tests/cpp/test_acq_worker_smoke.cpp
#include "catch.hpp"
#include "ads1292/qt/AcquisitionWorker.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include <QCoreApplication>

TEST_CASE("AcquisitionWorker runs the simulator to completion headlessly", "[worker]") {
  int argc = 0; char** argv = nullptr;
  QCoreApplication app(argc, argv);
  ads1292::acq::SimulatorDeviceSource sim(/*stream_batches=*/4, /*raw_count=*/0);
  ads1292::qt::AcquisitionWorker worker;
  int produced = worker.run_to_completion(&sim, ads1292::acq::AcquisitionMode::Live, "");
  REQUIRE(produced == 56);  // 4 * 14
}
```

> `run_to_completion` is a synchronous helper (runs the engine on a worker thread and joins) so the smoke is deterministic and needs no event-loop spin. The async `start()/stop()` path is also provided for the GUI; the smoke covers the engine-on-a-thread plumbing.

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Write `qt_runtime/CMakeLists.txt`**

```cmake
# qt_runtime/CMakeLists.txt
find_package(Qt6 REQUIRED COMPONENTS Core SerialPort)
set(CMAKE_AUTOMOC ON)
add_library(ads1292_qt_runtime STATIC
  src/QSerialByteTransport.cpp
  src/AcquisitionWorker.cpp)
target_include_directories(ads1292_qt_runtime PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(ads1292_qt_runtime PUBLIC ads1292_io ads1292_core Qt6::Core Qt6::SerialPort)
```
Add `add_subdirectory(qt_runtime)` to the top `CMakeLists.txt` after `add_subdirectory(io)`.

- [ ] **Step 4: Write the transport + worker**

`QSerialByteTransport`: ctor opens a `QSerialPort` (port, 9600, 8N1, read/write timeouts); `read(n)` accumulates via `waitForReadyRead(timeout)` + `read`; `write` sends + flush. `AcquisitionWorker`: holds a `SampleQueue`, an `std::atomic<bool> stop_`, and `run_to_completion(dev, mode, csv)` that runs `io::run_live(*dev, queue_, csv, [this]{return !stop_;})` (or `run_raw`) on a `std::thread`/`QThread` and joins, returning the sample count. The async `start()` posts the same onto a `QThread`; `stop()` sets `stop_=true`.

- [ ] **Step 5: Wire tests CMake (link qt_runtime; add smoke), build, run.** Expected PASS — 56 samples produced headlessly.

- [ ] **Step 6: Commit**

```bash
git add qt_runtime CMakeLists.txt tests/cpp/CMakeLists.txt tests/cpp/test_acq_worker_smoke.cpp
git commit -m "feat: P3 qt_runtime QSerialByteTransport + AcquisitionWorker with headless smoke"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P3 scope):
- simulator-driven acquisition → samples + CSV journal → Tasks 2 (simulator source) + 3 (engine) ✓
- live + raw modes → Task 3 (`run_live`/`run_raw`) ✓
- real QSerialPort path → Task 4 (`QSerialByteTransport` + `AdsProtocolDevice` over it) ✓ (compiles; real-board acquisition needs hardware)
- frame framing (read_frame) — not covered by P1; now unit-tested → Task 1 ✓
- QThread worker → Task 4 ✓

**2. Placeholder scan:** Tasks 2/3/4 Step 3 give prose descriptions of the implementation bodies (the protocol loop, the engine loop, the worker thread) rather than fully transcribed code, because these are integration bodies whose exact shape is constrained by the cited interfaces + the test gate. Every interface signature, every test body, and the framing code (Task 1) are concrete. This is the acceptable deviation for an integration-heavy phase; the unit tests are the authoritative gate.

**3. Type consistency:** `IByteTransport`/`SimulatorByteTransport`/`build_cmd`/`read_frame`/`Frame` (Task 1) match their Task 2 use. `IDeviceSource`/`AdsProtocolDevice`/`SimulatorDeviceSource` (Task 2) match Tasks 3/4. `SampleQueue`/`run_live`/`run_raw`/`AcquisitionResult` (Task 3) match Task 4's worker. `AcquisitionMode` is referenced in Tasks 3/4 — define it in `core/include/ads1292/acq/IDeviceSource.h` as `enum class AcquisitionMode { Live, Raw };` (add to the Task 2 header).

**Risk notes for the executor:**
- The portable engine writing the CSV journal once at stop (vs Python's incremental crash-safe writes) is a deliberate simplification for the finite simulator; the GUI's real-time path (P4) can switch to incremental writing. Note it in the report; it does not affect the round-trip parity.
- `QSerialByteTransport` cannot be unit-tested without a board; Task 4's smoke uses the simulator device source, so the worker/engine/thread plumbing is covered while the serial transport is compile-only. Do not attempt to fake a serial port.
- Threading: prefer `std::thread` inside `run_to_completion` for a deterministic join in the smoke; the async `start()/stop()` may use `QThread`. Either is fine as long as the smoke joins synchronously.
