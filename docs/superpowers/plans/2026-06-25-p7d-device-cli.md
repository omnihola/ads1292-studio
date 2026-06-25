# P7d: Device CLI (ports / firmware / stream) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the device-facing command line — a Qt-linked `ads1292_devcli` with `ports` (list ADS1x9x serial ports), `firmware` (query a connected device's firmware version), and `stream` (acquire samples from a device for N seconds → optional CSV) — porting the ADS port filter + `query_firmware`, and reusing the verified P3 device/framing layer + the simulators so the logic is testable without hardware.

**Architecture:** The ADS port FILTER (`is_ads_candidate_port`, vid/pid) is pure portable C++ (unit-testable); `list_ads_ports()` (QSerialPortInfo enumeration) is Qt (qt_runtime, smoke-tested — empty without a board). `query_firmware()` (write CMD 0x99 → read frames until a 0x99 response → "{major}.{minor}") is added to the P3 `AdsProtocolDevice` and tested against a `SimulatorByteTransport` with a canned firmware frame. The injectable `run_stream(out, IDeviceSource&, ...)` / `run_firmware(out, AdsProtocolDevice&)` / `run_ports(out)` functions take the device-source/transport by reference, so tests drive them with the `SimulatorDeviceSource`/`SimulatorByteTransport`; the `ads1292_devcli` binary opens a real `QSerialByteTransport`. The real-serial paths are smoke/hardware-only; the simulator/fake paths are fully tested.

**Tech Stack:** C++17, CMake, Catch2; Qt SerialPort (qt_runtime). Reuses P3 `AdsProtocolDevice`/`AdsFraming` (`build_cmd`/`read_frame`/`Frame`)/`IByteTransport`/`SimulatorByteTransport`/`SimulatorDeviceSource`/`IDeviceSource`, P2 `write_recording_csv`. Oracle: `device.py` (`list_ads_ports`/`_is_ads_candidate_port`/`query_firmware`), `cli.py` (`cmd_ports`/`cmd_firmware`/`cmd_stream`).

## Global Constraints

- **C++17**; the port FILTER + `query_firmware` are portable (core/qt_runtime, no GUI); the enumeration + the devcli binary use Qt SerialPort. NOT Qt-free (unlike `ads1292_cli`) — device IO needs Qt.
- **Layering**: filter/query_firmware in core/qt_runtime; the devcli binary links `ads1292_qt_runtime` (QSerialPort) + `ads1292_core` (AdsProtocolDevice/simulators) + `ads1292_io` (CsvIo).
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`. (Port enumeration runs without a display; no offscreen platform needed for these non-widget Qt tests, but harmless if set.)
- **Parity gates:** `is_ads_candidate_port` (vid==0x2047 && pid==0x0300) unit-tested; `query_firmware` tested against a canned 0x99 frame ("1.12"); `run_stream` tested via the simulator (samples=N to a CSV); the real-serial paths are smoke/hardware-only (documented).
- **Constants (device.py):** `VID_TI=0x2047`, `PID_ADS1X9X=0x0300`, `CMD_QUERY_FIRMWARE_VERSION=0x99`. `AdsPort{ std::string device, description, hwid; }`.
- **`is_ads_candidate_port(int vid, int pid)` (device.py `_is_ads_candidate_port`):** `return vid == 0x2047 && pid == 0x0300;`. (Read `_is_ads_candidate_port` for any additional conditions; it's `vid==VID_TI && pid==PID_ADS1X9X`.)
- **`list_ads_ports()` (device.py):** enumerate `QSerialPortInfo::availablePorts()`; for each with `hasVendorIdentifier() && hasProductIdentifier() && is_ads_candidate_port(vid, pid)` → `AdsPort{ portName(), description(), <hwid e.g. "VID:PID=2047:0300" or systemLocation()> }`. (The macOS USB fallback in device.py is optional — port the pyserial-equivalent VID/PID filter; document the fallback as deferred if awkward.)
- **`query_firmware()` (device.py + AdsProtocolDevice):** `t_.write(ads1292::acq::build_cmd(0x99, 0, 0));` then loop (bounded — e.g. up to N frames / a frame-count budget since there's no wall clock in the test): `auto f = ads1292::acq::read_frame(t_); if (!f.ok) break/continue; if (f.type == 0x99) { if (f.payload.size() >= 2) return std::to_string(f.payload[0]) + "." + std::to_string(f.payload[1]); }`. If no firmware frame within the budget → return `"no firmware response"` (match device.py's fallback string format reasonably — read it). (Use a frame-count budget instead of `time.monotonic()` so it's deterministic + testable.)
- **`cmd_ports` (cli.py):** `auto ports = list_ads_ports(); if (ports.empty()) { out << "No ADS1x9x ports found\n"; return 1; } for (p) out << p.device << "\t" << p.description << "\t" << p.hwid << "\n"; return 0;`.
- **`cmd_firmware` (cli.py):** open the port → `AdsProtocolDevice` → `out << query_firmware() << "\n"; return 0;`.
- **`cmd_stream` (cli.py):** open device → start_stream → acquire samples until the budget (Python uses N seconds wall-clock; the C++ `run_stream` testable form takes a **max-sample budget** OR a duration — for the simulator test use a sample budget; the binary may use a duration via a steady clock) → optionally `write_recording_csv` → `out << "samples=" << count << "\n"; return 0;`.

## File Structure

```
qt_runtime/include/ads1292/qt/AdsPorts.h     # AdsPort, is_ads_candidate_port (pure), list_ads_ports (Qt)
qt_runtime/src/AdsPorts.cpp
core/include/ads1292/acq/AdsProtocolDevice.h  # MODIFY: add query_firmware()
core/src/acq/AdsProtocolDevice.cpp            # MODIFY: implement query_firmware
devcli/include/ads1292/devcli/DevCli.h        # run_ports/run_firmware/run_stream (injectable)
devcli/src/DevCli.cpp
devcli/src/main.cpp                           # argv dispatch (opens QSerialByteTransport)
devcli/CMakeLists.txt                         # ads1292_devcli_lib + ads1292_devcli (Qt-linked)
tests/cpp/test_ads_ports.cpp                  # is_ads_candidate_port + list_ads_ports smoke
tests/cpp/test_query_firmware.cpp             # query_firmware via SimulatorByteTransport
tests/cpp/test_devcli.cpp                     # run_stream via SimulatorDeviceSource, run_ports
```

---

### Task 1: ADS port filter + enumeration

**Files:** Create `qt_runtime/include/ads1292/qt/AdsPorts.h` + `qt_runtime/src/AdsPorts.cpp`; Modify qt_runtime CMake; Create `tests/cpp/test_ads_ports.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (namespace `ads1292::qt`): `struct AdsPort { std::string device, description, hwid; };`, `bool is_ads_candidate_port(int vid, int pid);` (pure), `std::vector<AdsPort> list_ads_ports();` (QSerialPortInfo).

- [ ] **Step 1: Write the failing test** (filter unit + enumeration smoke)

```cpp
// tests/cpp/test_ads_ports.cpp
#include "catch.hpp"
#include "ads1292/qt/AdsPorts.h"
using namespace ads1292::qt;
TEST_CASE("is_ads_candidate_port matches TI VID + ADS1x9x PID", "[device]") {
  REQUIRE(is_ads_candidate_port(0x2047, 0x0300));
  REQUIRE_FALSE(is_ads_candidate_port(0x2047, 0x0301));
  REQUIRE_FALSE(is_ads_candidate_port(0x1234, 0x0300));
}
TEST_CASE("list_ads_ports runs without a board (likely empty in CI)", "[device]") {
  auto ports = list_ads_ports();   // no crash; empty when no ADS device attached
  REQUIRE(ports.size() >= 0);
  for (const auto& p : ports) { REQUIRE(!p.device.empty()); }
}
```

- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement** `is_ads_candidate_port` (pure: `vid==0x2047 && pid==0x0300`) + `list_ads_ports` (QSerialPortInfo::availablePorts, filter by hasVendorIdentifier/hasProductIdentifier + is_ads_candidate_port, build AdsPort{portName, description, "VID:PID=%04X:%04X" or systemLocation}). Link Qt::SerialPort in qt_runtime if not already.
- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.
- [ ] **Step 5: Commit** `git commit -m "feat: P7d ADS port filter + list_ads_ports"`

---

### Task 2: query_firmware on AdsProtocolDevice

**Files:** Modify `core/include/ads1292/acq/AdsProtocolDevice.h` + `core/src/acq/AdsProtocolDevice.cpp`; Create `tests/cpp/test_query_firmware.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: `ads1292::acq::build_cmd`/`read_frame`/`Frame` (AdsFraming), `IByteTransport`, `SimulatorByteTransport`.
- Produces: `std::string AdsProtocolDevice::query_firmware();` (new method; `max_frames` budget param optional, default e.g. 64).

- [ ] **Step 1: Write the failing test** (canned 0x99 frame via SimulatorByteTransport)

```cpp
// tests/cpp/test_query_firmware.cpp
#include "catch.hpp"
#include "ads1292/acq/AdsProtocolDevice.h"
#include "ads1292/acq/SimulatorByteTransport.h"
#include "ads1292/acq/AdsFraming.h"
using namespace ads1292::acq;
TEST_CASE("query_firmware reads a 0x99 frame -> major.minor", "[device]") {
  // Build a canned inbound byte stream containing a firmware-response frame
  // (type 0x99, payload {1, 12}) in the wire format read_frame expects.
  // READ AdsFraming.cpp's read_frame to construct the exact frame bytes
  // (kStart 0x02 ... type ... payload ... kEnd 0x03), OR reuse a frame-encode helper.
  std::vector<uint8_t> inbound = /* a valid 0x99 frame with payload {1,12} */;
  SimulatorByteTransport t(inbound);
  AdsProtocolDevice dev(t, 500.0);
  REQUIRE(dev.query_firmware() == "1.12");
  // confirm the command 0x99 was written
  REQUIRE(t.last_written() == build_cmd(0x99, 0, 0));
}
TEST_CASE("query_firmware with no response returns the fallback", "[device]") {
  SimulatorByteTransport t({});   // empty inbound -> read_frame yields no 0x99
  AdsProtocolDevice dev(t, 500.0);
  REQUIRE(dev.query_firmware().rfind("no firmware response", 0) == 0);  // starts with the fallback
}
```
(Read `AdsFraming.cpp::read_frame` to construct the canned 0x99 frame bytes correctly — that's the load-bearing detail.)

- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement** `query_firmware`: `t_.write(build_cmd(0x99,0,0));` then loop up to `max_frames`: `auto f = read_frame(t_); if (!f.ok) { /* no more / bad */ if exhausted break; continue; } if (f.type == 0x99 && f.payload.size() >= 2) return to_string(p0)+"."+to_string(p1);`. On exhaustion → `"no firmware response"` (+ optional last-frame detail, match device.py reasonably). Read `read_frame`'s end-of-input behavior (Frame.ok=false) to bound the loop deterministically.
- [ ] **Step 4: Wire CMake, build, run.** Iterate until both cases pass.
- [ ] **Step 5: Commit** `git commit -m "feat: P7d AdsProtocolDevice::query_firmware (CMD 0x99)"`

---

### Task 3: device CLI binary (ports / firmware / stream)

**Files:** Create `devcli/include/ads1292/devcli/DevCli.h`, `devcli/src/DevCli.cpp`, `devcli/src/main.cpp`, `devcli/CMakeLists.txt`; Modify top CMake (`add_subdirectory(devcli)`); Create `tests/cpp/test_devcli.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (namespace `ads1292::devcli`):
  - `int run_ports(std::ostream& out);` (calls `list_ads_ports`; print device/desc/hwid; 1 if none else 0).
  - `int run_firmware(std::ostream& out, ads1292::acq::AdsProtocolDevice& dev);` (print `dev.query_firmware()`; return 0).
  - `struct StreamOptions { int max_samples = 0; std::string csv_path; };` and `int run_stream(std::ostream& out, ads1292::acq::IDeviceSource& dev, const StreamOptions& opt);` (start_stream; read_stream_batch loops collecting samples until `>= max_samples` (or the source is exhausted); optionally `write_recording_csv(csv_path, samples)`; `out << "samples=" << count << "\n"`; stop_stream; return 0).
- `main.cpp`: `ads1292_devcli ports` → run_ports; `ads1292_devcli firmware --port <p>` → open `QSerialByteTransport(p)` → `AdsProtocolDevice` → run_firmware; `ads1292_devcli stream --port <p> --seconds <n> [--csv <f>]` → open device → run_stream (the binary converts seconds→a sample budget via sample_rate, or uses a steady-clock loop; document). Real-serial open errors → clean message + non-zero exit.

- [ ] **Step 1: Write the failing devcli test** (run_stream via simulator + run_ports)

```cpp
// tests/cpp/test_devcli.cpp
#include "catch.hpp"
#include "ads1292/devcli/DevCli.h"
#include "ads1292/acq/SimulatorDeviceSource.h"
#include <sstream>
using namespace ads1292;
TEST_CASE("run_stream collects samples from the simulator into a count", "[device]") {
  acq::SimulatorDeviceSource sim(/*stream_batches*/ 10, /*raw_count*/ 0);  // 10*14 = 140 samples
  devcli::StreamOptions opt; opt.max_samples = 100;
  std::ostringstream out;
  int code = devcli::run_stream(out, sim, opt);
  REQUIRE(code == 0);
  REQUIRE(out.str().find("samples=") != std::string::npos);
  // collected at least max_samples (or all the simulator produced)
}
TEST_CASE("run_ports prints a diagnostic when no board attached", "[device]") {
  std::ostringstream out;
  int code = devcli::run_ports(out);   // CI: no ADS device -> "No ADS1x9x ports found", exit 1
  // either 0 (a device is attached) or 1 (none) — assert it ran + produced output
  REQUIRE((code == 0 || code == 1));
}
```

- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement** `DevCli.{h,cpp}` (run_ports/run_firmware/run_stream) + `main.cpp` (open QSerialByteTransport for firmware/stream; ports needs no port) + `devcli/CMakeLists.txt` (`ads1292_devcli_lib` STATIC linking `ads1292_qt_runtime ads1292_core ads1292_io` + Qt::SerialPort; `ads1292_devcli` exe). Add `add_subdirectory(devcli)` to the top CMake. `run_stream`: loop `read_stream_batch()`; append; stop when count >= max_samples or a batch returns empty (source exhausted).
- [ ] **Step 4: Wire tests CMake (link ads1292_devcli_lib), build, run.** Expected PASS. Confirm `build/devcli/ads1292_devcli` builds.
- [ ] **Step 5: Commit** `git commit -m "feat: P7d device CLI (ports/firmware/stream)"`

---

## Self-Review

**1. Spec coverage:** ports (filter + enumerate) → Task 1 ✓; firmware (query_firmware) → Task 2 ✓; stream + the devcli binary → Task 3 ✓. The macOS USB fallback in list_ads_ports → optional/deferred (documented). The Python wall-clock `--seconds` → the binary maps to a sample budget / steady-clock; the testable `run_stream` takes a sample budget.

**2. Placeholder scan:** the constants (VID/PID/CMD 0x99), the filter, the query_firmware protocol (build_cmd 0x99 + read_frame until 0x99), and the cmd output formats are spelled out; the tests are concrete. The ONE load-bearing detail referenced to the source: the exact 0x99 frame wire format for the canned test inbound (the executor reads `AdsFraming.cpp::read_frame`). The real-serial paths are smoke/hardware-only, called out explicitly.

**3. Type consistency:** `AdsPort`/`is_ads_candidate_port`/`list_ads_ports` (Task 1) used by run_ports (Task 3); `query_firmware` (Task 2) on AdsProtocolDevice used by run_firmware (Task 3); `run_stream` takes `IDeviceSource&` (tested via SimulatorDeviceSource, real via AdsProtocolDevice). Reuses P3 `build_cmd`/`read_frame`/`IByteTransport`/`SimulatorByteTransport`/`SimulatorDeviceSource`, P2 `write_recording_csv`.

**Risk notes for the executor:**
- The devcli binary needs Qt (QSerialPort) — it is NOT Qt-free. Link `ads1292_qt_runtime` + Qt::SerialPort.
- The LOAD-BEARING test detail is the canned 0x99 firmware frame bytes — READ `core/src/acq/AdsFraming.cpp::read_frame` to construct a frame the parser accepts (kStart 0x02, type, payload, kEnd 0x03, …). If there's no response-frame encoder, hand-build the bytes from the parser's expectations. If you cannot construct a valid frame, report BLOCKED with the read_frame format.
- `query_firmware` must use a FRAME-COUNT budget (not wall-clock) so the test is deterministic; bound the loop on `read_frame` returning `ok=false` (end of input) + a max_frames cap.
- `run_stream` is tested via the simulator with a sample budget; the real `--seconds` path (binary) maps seconds→samples via the rate or a steady-clock loop — document the mapping.
- The real-serial `ports`/`firmware`/`stream` over a live board can't be CI-tested — the simulator/fake-transport tests cover the logic; the enumeration is a no-crash smoke.
