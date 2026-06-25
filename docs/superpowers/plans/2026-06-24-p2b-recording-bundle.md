# P2b: recording_bundle Model + JSON Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the Python `recording_bundle` JSON as a golden fixture, then build the C++ model + serialization that reproduces it structurally (key-for-key, value-for-value) — including the SHA-1-based `event_id`, the 7 bundle sub-objects, and `build_recording_bundle`.

**Architecture:** `core` gains a pure-C++ SHA-1 (`Sha1`) and the event-id helpers (`event_id`, `event_sample_indices`, `slug`) that operate on `EventMarker`. `io` gains the bundle data structs (SessionMetadata, QualityGate, RecordingProcessingSettings, TestProtocol/ProtocolStep, AcquisitionProvenance) and their `nlohmann::json` serialization, plus `build_recording_bundle(...)` that assembles the full bundle. Parity is checked by comparing the C++-produced `nlohmann::json` against the committed golden bundle JSON (nlohmann object `==` is key-order-insensitive, so only keys+values must match).

**Tech Stack:** C++17, CMake, Catch2 + nlohmann/json (vendored), the existing Python oracle (`recording_bundle.py`, `events.py`, etc.) in the `sensor` conda env. SHA-1 is implemented in `core` (no external crypto dep), golden-tested against standard vectors.

## Global Constraints

- **C++17**; `core/` is pure portable C++ (stdlib only — including the SHA-1). `io/` MAY use `nlohmann/json` (header-only, pure C++). Neither uses Qt or OS APIs.
- **Layering**: `io → core`, `tests → io, core`. `core` depends on nothing.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test** (every C++ task): `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Python oracle** (Task 1 only): `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor`.
- **The committed golden `recording_bundle.json` is the authoritative spec.** Where this plan references long static content (channel_map entries, csv_columns descriptions, schema strings), the implementer copies the EXACT strings from the committed `tests/fixtures/golden/files/recording_bundle.json` — do not paraphrase.
- **Parity bar**: the C++ `build_recording_bundle(...)` output, serialized to `nlohmann::json`, must `==` the golden JSON (key-order-insensitive). Per-section tasks compare their sub-object against the corresponding golden section.
- **event_id algorithm (from `events.py`, verified):**
  - `seconds_to_sample_index(s, sr) = max(0, round(s * sr))` (round-half-to-even; the fixture values are exact, no halfway cases).
  - `event_sample_indices`: `start = idx(timestamp)`, `end = idx(end_seconds)`, `duration_samples = max(0, end - start)`.
  - `slug(s)`: lowercase, replace each run of chars not in `[a-z0-9]` with `-`, strip leading/trailing `-`, truncate to 32, or `"event"` if empty.
  - fingerprint = `start|end|type|label|notes` (pipe-joined; `type` is `"interval"` if normalized duration > 0 else `"point"`; `label`/`notes` are the NORMALIZED values).
  - `event_id = "evt-" + zero-pad(start,7) + "-" + zero-pad(end,7) + "-" + slug + "-" + sha1_hex(fingerprint)[:8]`.
  - Known goldens: fingerprint `10|10|point|touch|n1` → `c545bb80`; `20|35|interval|motion|n2` → `b06d78b7`.
- **SHA-1 standard test vectors**: `sha1("")` = `da39a3ee5e6b4b0d3255bfef95601890afd80709`; `sha1("abc")` = `a9993e364706816aba3e25717850c26c9cd0d89d`.

## File Structure

```
core/
  include/ads1292/crypto/Sha1.h          # sha1_hex(const std::string&) -> std::string (40 hex chars)
  src/crypto/Sha1.cpp
  include/ads1292/event/EventId.h        # event_id / event_sample_indices / slug on EventMarker
  src/event/EventId.cpp
io/
  include/ads1292/io/Bundle.h            # 7 structs + build_recording_bundle + to_json
  src/Bundle.cpp
tests/cpp/
  test_sha1.cpp
  test_event_id.cpp
  test_bundle_events.cpp
  test_bundle_sections.cpp
  test_bundle_assembly.cpp
scripts/ (Task 1, Python)
  gen_file_fixtures.py                   # modified: also write recording_bundle.json
  validate_golden_fixtures.py            # modified: register file_bundle
tests/fixtures/golden/files/
  recording_bundle.json                  # new committed golden (the full default bundle)
  recording_bundle_sidecar.json          # new sidecar (category file_bundle)
```

---

### Task 1: Freeze the recording_bundle golden fixture (Python, no C++)

**Files:**
- Modify: `scripts/gen_file_fixtures.py` (add a bundle section to `generate`)
- Modify: `scripts/validate_golden_fixtures.py` (register `file_bundle` in `FILE_SIDECAR_KEYS`)
- Create (generated): `tests/fixtures/golden/files/recording_bundle.json`, `tests/fixtures/golden/files/recording_bundle_sidecar.json`

**Interfaces:**
- Consumes: `ads1292_studio.recording_bundle.build_recording_bundle` and the bundle dataclasses.
- Produces: committed `recording_bundle.json` (the full bundle dict, sorted keys) + a sidecar (category `file_bundle`).

- [ ] **Step 1: Write the failing generator test**

In `tests/test_gen_file_fixtures.py`, add (don't weaken existing tests):

```python
def test_freezes_recording_bundle(tmp_path: Path):
    generate(tmp_path)
    files_dir = tmp_path / "files"
    assert (files_dir / "recording_bundle.json").exists()
    sc = load_fixture(files_dir / "recording_bundle_sidecar.json")
    assert sc["category"] == "file_bundle"
    bundle = load_fixture(files_dir / "recording_bundle.json")
    assert set(bundle.keys()) >= {
        "acquisition", "calibration", "created_at", "csv_name",
        "events", "metadata", "processing", "protocol", "quality_gate", "schema"}
    assert bundle["events"]["events"][0]["event_id"].endswith("c545bb80")
    assert bundle["events"]["events"][1]["event_id"].endswith("b06d78b7")
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_file_fixtures.py::test_freezes_recording_bundle -v`
Expected: FAIL (no `recording_bundle.json`).

- [ ] **Step 3: Add the bundle section to the generator**

In `scripts/gen_file_fixtures.py`, add imports:

```python
from ads1292_studio.recording_bundle import build_recording_bundle, RecordingProcessingSettings
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.acquisition import AcquisitionProvenance
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality_gate import QualityGate
```

(`Calibration` and `EventMarker` are already imported by earlier sections; `dump_fixture` writes canonical sorted JSON.)

Inside `generate(root)`, before `return written`, insert:

```python
    # --- recording bundle: freeze the full default bundle JSON (the C++ parity target) ---
    bundle = build_recording_bundle(
        csv_path="rec.csv",
        metadata=SessionMetadata(operator="fixture", subject_id="p1"),
        events=(EventMarker(0.02, "touch", "n1", 0.0), EventMarker(0.04, "motion", "n2", 0.03)),
        calibration=Calibration(),
        acquisition=AcquisitionProvenance(),
        protocol=TestProtocol(),
        quality_gate=QualityGate(),
        processing=RecordingProcessingSettings(),
        sample_rate_hz=500.0,
        created_at="",
    )
    bundle_path = out / "recording_bundle.json"
    dump_fixture(bundle, bundle_path)
    bundle_sidecar = out / "recording_bundle_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_bundle", "name": "recording_bundle",
        "oracle": {"function": "ads1292_studio.recording_bundle.build_recording_bundle"},
        "artifact": "recording_bundle.json",
        "top_keys": sorted(bundle.keys()),
        "tolerance": {"kind": "structure"},
        "notes": "full default recording bundle; C++ build_recording_bundle must reproduce key-for-key",
    }, bundle_sidecar)
    written += [bundle_path, bundle_sidecar]
```

- [ ] **Step 4: Register the new category in the validator**

In `scripts/validate_golden_fixtures.py`, add to `FILE_SIDECAR_KEYS`:

```python
    "file_bundle": ("artifact", "top_keys"),
```

- [ ] **Step 5: Run the test, regenerate, validate, restore churned binaries**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_file_fixtures.py -v
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m scripts.generate_golden_fixtures
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m scripts.validate_golden_fixtures tests/fixtures/golden
git checkout -- tests/fixtures/golden/files/recording.xlsx tests/fixtures/golden/files/recording.h5 tests/fixtures/golden/oracle.json 2>/dev/null || true
git status --porcelain
```
Expected: tests pass; `all golden fixtures valid`; after restoring the churned binaries, `git status` shows only the new bundle files + the modified scripts/test.

- [ ] **Step 6: Commit**

```bash
git add scripts/gen_file_fixtures.py scripts/validate_golden_fixtures.py tests/test_gen_file_fixtures.py tests/fixtures/golden/files/recording_bundle.json tests/fixtures/golden/files/recording_bundle_sidecar.json
git commit -m "feat: P2b freeze recording_bundle golden fixture + validator support"
```

---

### Task 2: SHA-1 in core (golden-tested)

**Files:**
- Create: `core/include/ads1292/crypto/Sha1.h`, `core/src/crypto/Sha1.cpp`
- Modify: `core/CMakeLists.txt` (add `src/crypto/Sha1.cpp`)
- Create test: `tests/cpp/test_sha1.cpp`; Modify: `tests/cpp/CMakeLists.txt`

**Interfaces:**
- Produces: `std::string ads1292::sha1_hex(const std::string& data)` — lowercase 40-hex-char SHA-1 digest.

- [ ] **Step 1: Write the failing test (standard vectors + event fingerprints)**

```cpp
// tests/cpp/test_sha1.cpp
#include "catch.hpp"
#include "ads1292/crypto/Sha1.h"

using ads1292::sha1_hex;

TEST_CASE("sha1 standard test vectors", "[crypto]") {
  REQUIRE(sha1_hex("") == "da39a3ee5e6b4b0d3255bfef95601890afd80709");
  REQUIRE(sha1_hex("abc") == "a9993e364706816aba3e25717850c26c9cd0d89d");
}

TEST_CASE("sha1 reproduces the event fingerprint digests", "[crypto]") {
  REQUIRE(sha1_hex("10|10|point|touch|n1").substr(0, 8) == "c545bb80");
  REQUIRE(sha1_hex("20|35|interval|motion|n2").substr(0, 8) == "b06d78b7");
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5`
Expected: build FAILS — `Sha1.h` not found.

- [ ] **Step 3: Write the SHA-1 header**

```cpp
// core/include/ads1292/crypto/Sha1.h
#pragma once
#include <string>

namespace ads1292 {
// Lowercase 40-hex-char SHA-1 of the input bytes. Pure C++17, no external deps.
std::string sha1_hex(const std::string& data);
}  // namespace ads1292
```

- [ ] **Step 4: Write the SHA-1 implementation**

```cpp
// core/src/crypto/Sha1.cpp
#include "ads1292/crypto/Sha1.h"
#include <cstdint>
#include <cstdio>
#include <vector>

namespace ads1292 {
namespace {
inline uint32_t rotl(uint32_t v, int n) { return (v << n) | (v >> (32 - n)); }
}  // namespace

std::string sha1_hex(const std::string& data) {
  uint32_t h0 = 0x67452301, h1 = 0xEFCDAB89, h2 = 0x98BADCFE, h3 = 0x10325476, h4 = 0xC3D2E1F0;

  std::vector<uint8_t> msg(data.begin(), data.end());
  const uint64_t bit_len = static_cast<uint64_t>(msg.size()) * 8u;
  msg.push_back(0x80);
  while (msg.size() % 64 != 56) msg.push_back(0x00);
  for (int i = 7; i >= 0; --i) msg.push_back(static_cast<uint8_t>((bit_len >> (i * 8)) & 0xFF));

  for (size_t chunk = 0; chunk < msg.size(); chunk += 64) {
    uint32_t w[80];
    for (int i = 0; i < 16; ++i) {
      w[i] = (static_cast<uint32_t>(msg[chunk + i * 4]) << 24) |
             (static_cast<uint32_t>(msg[chunk + i * 4 + 1]) << 16) |
             (static_cast<uint32_t>(msg[chunk + i * 4 + 2]) << 8) |
             (static_cast<uint32_t>(msg[chunk + i * 4 + 3]));
    }
    for (int i = 16; i < 80; ++i) w[i] = rotl(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);

    uint32_t a = h0, b = h1, c = h2, d = h3, e = h4;
    for (int i = 0; i < 80; ++i) {
      uint32_t f, k;
      if (i < 20) { f = (b & c) | ((~b) & d); k = 0x5A827999; }
      else if (i < 40) { f = b ^ c ^ d; k = 0x6ED9EBA1; }
      else if (i < 60) { f = (b & c) | (b & d) | (c & d); k = 0x8F1BBCDC; }
      else { f = b ^ c ^ d; k = 0xCA62C1D6; }
      uint32_t tmp = rotl(a, 5) + f + e + k + w[i];
      e = d; d = c; c = rotl(b, 30); b = a; a = tmp;
    }
    h0 += a; h1 += b; h2 += c; h3 += d; h4 += e;
  }

  char out[41];
  std::snprintf(out, sizeof(out), "%08x%08x%08x%08x%08x", h0, h1, h2, h3, h4);
  return std::string(out, 40);
}
}  // namespace ads1292
```

- [ ] **Step 5: Wire CMake, build, run**

Add `src/crypto/Sha1.cpp` to `core/CMakeLists.txt`; add `test_sha1.cpp` to `tests/cpp/CMakeLists.txt`. Then build + ctest. Expected: PASS (standard vectors + both event digests).

- [ ] **Step 6: Commit**

```bash
git add core/include/ads1292/crypto core/src/crypto core/CMakeLists.txt tests/cpp/test_sha1.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P2b SHA-1 in core (golden-tested against standard vectors + event digests)"
```

---

### Task 3: event_id / sample indices / slug (core)

**Files:**
- Create: `core/include/ads1292/event/EventId.h`, `core/src/event/EventId.cpp`
- Modify: `core/CMakeLists.txt`; Create test `tests/cpp/test_event_id.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: `ads1292::EventMarker`, `ads1292::sha1_hex`.
- Produces (in `namespace ads1292`):
  - `struct EventSampleIndices { int start_sample_index; int end_sample_index; int duration_samples; };`
  - `int seconds_to_sample_index(double seconds, double sample_rate_hz);`
  - `EventSampleIndices event_sample_indices(const EventMarker& e, double sample_rate_hz);`
  - `std::string slug(const std::string& value);`
  - `std::string event_id(const EventMarker& e, double sample_rate_hz);`

- [ ] **Step 1: Write the failing test**

```cpp
// tests/cpp/test_event_id.cpp
#include "catch.hpp"
#include "ads1292/event/EventId.h"
#include "ads1292/model/EventMarker.h"

using namespace ads1292;

TEST_CASE("sample indices round timestamp*rate", "[event]") {
  EventSampleIndices p = event_sample_indices(EventMarker{0.02, "touch", "n1", 0.0}, 500.0);
  REQUIRE(p.start_sample_index == 10);
  REQUIRE(p.end_sample_index == 10);
  REQUIRE(p.duration_samples == 0);
  EventSampleIndices r = event_sample_indices(EventMarker{0.04, "motion", "n2", 0.03}, 500.0);
  REQUIRE(r.start_sample_index == 20);
  REQUIRE(r.end_sample_index == 35);
  REQUIRE(r.duration_samples == 15);
}

TEST_CASE("slug normalizes labels", "[event]") {
  REQUIRE(slug("Touch Electrode!") == "touch-electrode");
  REQUIRE(slug("   ") == "event");
}

TEST_CASE("event_id matches the golden format + digest", "[event]") {
  REQUIRE(event_id(EventMarker{0.02, "touch", "n1", 0.0}, 500.0) ==
          "evt-0000010-0000010-touch-c545bb80");
  REQUIRE(event_id(EventMarker{0.04, "motion", "n2", 0.03}, 500.0) ==
          "evt-0000020-0000035-motion-b06d78b7");
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5`
Expected: build FAILS — `EventId.h` not found.

- [ ] **Step 3: Write the header**

```cpp
// core/include/ads1292/event/EventId.h
#pragma once
#include <string>
#include "ads1292/model/EventMarker.h"

namespace ads1292 {
struct EventSampleIndices {
  int start_sample_index = 0;
  int end_sample_index = 0;
  int duration_samples = 0;
};

int seconds_to_sample_index(double seconds, double sample_rate_hz);
EventSampleIndices event_sample_indices(const EventMarker& e, double sample_rate_hz);
std::string slug(const std::string& value);
std::string event_id(const EventMarker& e, double sample_rate_hz);
}  // namespace ads1292
```

- [ ] **Step 4: Write the implementation**

```cpp
// core/src/event/EventId.cpp
#include "ads1292/event/EventId.h"
#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include "ads1292/crypto/Sha1.h"

namespace ads1292 {
namespace {
double normalized_rate(double sr) { return sr > 0 ? sr : 500.0; }
}  // namespace

int seconds_to_sample_index(double seconds, double sample_rate_hz) {
  double idx = std::nearbyint(seconds * sample_rate_hz);  // round-half-to-even, matches Python round
  int v = static_cast<int>(idx);
  return v > 0 ? v : 0;
}

EventSampleIndices event_sample_indices(const EventMarker& e, double sample_rate_hz) {
  double sr = normalized_rate(sample_rate_hz);
  EventMarker m = e.normalized();
  EventSampleIndices out;
  out.start_sample_index = seconds_to_sample_index(m.timestamp_seconds, sr);
  out.end_sample_index = seconds_to_sample_index(m.end_seconds(), sr);
  out.duration_samples = std::max(0, out.end_sample_index - out.start_sample_index);
  return out;
}

std::string slug(const std::string& value) {
  std::string lower;
  for (char ch : value) lower.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
  // replace each run of non-[a-z0-9] with a single '-'
  std::string collapsed;
  bool in_run = false;
  for (char ch : lower) {
    bool keep = (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9');
    if (keep) { collapsed.push_back(ch); in_run = false; }
    else if (!in_run) { collapsed.push_back('-'); in_run = true; }
  }
  size_t b = collapsed.find_first_not_of('-');
  size_t e = collapsed.find_last_not_of('-');
  std::string trimmed = (b == std::string::npos) ? "" : collapsed.substr(b, e - b + 1);
  if (trimmed.size() > 32) trimmed = trimmed.substr(0, 32);
  return trimmed.empty() ? "event" : trimmed;
}

std::string event_id(const EventMarker& e, double sample_rate_hz) {
  double sr = normalized_rate(sample_rate_hz);
  EventMarker m = e.normalized();
  EventSampleIndices idx = event_sample_indices(m, sr);
  std::string type = m.is_interval() ? "interval" : "point";
  std::string fingerprint = std::to_string(idx.start_sample_index) + "|" +
                            std::to_string(idx.end_sample_index) + "|" + type + "|" +
                            m.label + "|" + m.notes;
  std::string digest = sha1_hex(fingerprint).substr(0, 8);
  char head[64];
  std::snprintf(head, sizeof(head), "evt-%07d-%07d-", idx.start_sample_index, idx.end_sample_index);
  return std::string(head) + slug(m.label) + "-" + digest;
}
}  // namespace ads1292
```

- [ ] **Step 5: Wire CMake, build, run**

Add `src/event/EventId.cpp` to `core/CMakeLists.txt`; add `test_event_id.cpp` to tests CMake. Build + ctest. Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/include/ads1292/event core/src/event core/CMakeLists.txt tests/cpp/test_event_id.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P2b event_id / sample-index / slug helpers (core)"
```

---

### Task 4: Events bundle section (io) — JSON parity

**Files:**
- Create: `io/include/ads1292/io/Bundle.h`, `io/src/Bundle.cpp`
- Modify: `io/CMakeLists.txt` (add `src/Bundle.cpp`; link `nlohmann_json`)
- Modify: `tests/cpp/CMakeLists.txt`; Create test `tests/cpp/test_bundle_events.cpp`

**Interfaces:**
- Consumes: `ads1292::EventMarker`, `ads1292::event_id`, `ads1292::event_sample_indices`, `nlohmann::json`.
- Produces (in `namespace ads1292::io`):
  - `nlohmann::json events_payload(const std::vector<EventMarker>& events, double sample_rate_hz);`

- [ ] **Step 1: Write the failing test (compare to the golden events section)**

```cpp
// tests/cpp/test_bundle_events.cpp
#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/model/EventMarker.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;

namespace {
json load_golden() {
  std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
  json j; in >> j; return j;
}
}  // namespace

TEST_CASE("events_payload reproduces the golden events section", "[bundle]") {
  std::vector<ads1292::EventMarker> events = {
      {0.02, "touch", "n1", 0.0}, {0.04, "motion", "n2", 0.03}};
  json got = ads1292::io::events_payload(events, 500.0);
  REQUIRE(got == load_golden().at("events"));
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5`
Expected: build FAILS — `Bundle.h` not found.

- [ ] **Step 3: Write Bundle.h (events portion now; the rest is added in Tasks 5–6)**

```cpp
// io/include/ads1292/io/Bundle.h
#pragma once
#include <vector>
#include "nlohmann/json.hpp"
#include "ads1292/model/EventMarker.h"

namespace ads1292 {
namespace io {
nlohmann::json events_payload(const std::vector<EventMarker>& events, double sample_rate_hz);
}  // namespace io
}  // namespace ads1292
```

- [ ] **Step 4: Write Bundle.cpp (events portion)**

Read the golden `events` section in `tests/fixtures/golden/files/recording_bundle.json` and copy the exact constant strings (`schema`, `timestamp_reference`, `sample_index_reference`).

```cpp
// io/src/Bundle.cpp
#include "ads1292/io/Bundle.h"
#include "ads1292/event/EventId.h"

namespace ads1292 {
namespace io {

static nlohmann::json event_entry(const EventMarker& event, double sample_rate_hz) {
  EventMarker m = event.normalized();
  EventSampleIndices idx = event_sample_indices(m, sample_rate_hz);
  std::string type = m.is_interval() ? "interval" : "point";
  return {
      {"event_id", event_id(m, sample_rate_hz)},
      {"timestamp_seconds", m.timestamp_seconds},
      {"start_seconds", m.timestamp_seconds},
      {"end_seconds", m.end_seconds()},
      {"duration_seconds", m.duration_seconds},
      {"start_sample_index", idx.start_sample_index},
      {"end_sample_index", idx.end_sample_index},
      {"duration_samples", idx.duration_samples},
      {"event_type", type},
      {"label", m.label},
      {"notes", m.notes},
  };
}

nlohmann::json events_payload(const std::vector<EventMarker>& events, double sample_rate_hz) {
  double sr = sample_rate_hz > 0 ? sample_rate_hz : 500.0;
  nlohmann::json entries = nlohmann::json::array();
  for (const auto& e : events) entries.push_back(event_entry(e, sr));
  return {
      {"schema", "ads1292-event-annotations-v1"},
      {"timestamp_reference", "relative_seconds_from_recording_start"},
      {"sample_index_reference", "zero_based_sample_index_at_recording_sample_rate"},
      {"sample_rate_hz", sr},
      {"events", entries},
  };
}

}  // namespace io
}  // namespace ads1292
```

> The implementer MUST verify the three constant strings against the golden `events` section and adjust if they differ (the golden is authoritative).

- [ ] **Step 5: Wire CMake, build, run**

In `io/CMakeLists.txt`: add `src/Bundle.cpp` to `ads1292_io`, and `target_link_libraries(ads1292_io PUBLIC ads1292_core nlohmann_json)`. In `tests/cpp/CMakeLists.txt`: add `test_bundle_events.cpp`. Build + ctest. Expected: PASS — `got == golden["events"]`.

- [ ] **Step 6: Commit**

```bash
git add io/include/ads1292/io/Bundle.h io/src/Bundle.cpp io/CMakeLists.txt tests/cpp/test_bundle_events.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P2b events bundle section with golden JSON parity"
```

---

### Task 5: Bundle sub-objects (metadata, calibration, quality_gate, processing, protocol, acquisition) — JSON parity

**Files:**
- Modify: `io/include/ads1292/io/Bundle.h` (add the 6 structs + their `to_json`), `io/src/Bundle.cpp`
- Create test: `tests/cpp/test_bundle_sections.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (in `namespace ads1292::io`): structs `SessionMetadata`, `QualityGate`, `RecordingProcessingSettings`, `TestProtocol` (+ `ProtocolStep`), `AcquisitionProvenance`, each with defaults matching the golden, plus free functions returning each section's `nlohmann::json`:
  - `nlohmann::json metadata_payload(const SessionMetadata&);`
  - `nlohmann::json calibration_payload(const Calibration&);`
  - `nlohmann::json quality_gate_payload(const QualityGate&);`
  - `nlohmann::json processing_payload(const RecordingProcessingSettings&);`
  - `nlohmann::json protocol_payload(const TestProtocol&);`
  - `nlohmann::json acquisition_payload(const AcquisitionProvenance&, double sample_rate_hz);`

**This is the largest task. The committed golden `recording_bundle.json` is the authoritative spec for every key, value, and default** — the implementer copies the exact static strings (channel_map's 4 entries, csv_columns' 8 `{name,unit,description}` objects, all `schema` strings, `acquisition_mode`, `timestamp_reference`, etc.) verbatim from the golden file's corresponding sections. `quality_gate`'s `max_baseline_drift_counts` / `max_noise_rms_counts` / `max_peak_to_peak_counts` are `null` in the golden → model them as `std::optional<double>` and serialize an unset optional as `nullptr` (JSON null).

- [ ] **Step 1: Write the failing test (each section vs the golden)**

```cpp
// tests/cpp/test_bundle_sections.cpp
#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/model/Calibration.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;
using namespace ads1292;
using namespace ads1292::io;

namespace {
json golden() {
  std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
  json j; in >> j; return j;
}
}  // namespace

TEST_CASE("each bundle sub-object reproduces its golden section", "[bundle]") {
  json g = golden();
  REQUIRE(metadata_payload(SessionMetadata{"fixture", "p1"}) == g.at("metadata"));
  REQUIRE(calibration_payload(Calibration{}) == g.at("calibration"));
  REQUIRE(quality_gate_payload(QualityGate{}) == g.at("quality_gate"));
  REQUIRE(processing_payload(RecordingProcessingSettings{}) == g.at("processing"));
  REQUIRE(protocol_payload(TestProtocol{}) == g.at("protocol"));
  REQUIRE(acquisition_payload(AcquisitionProvenance{}, 500.0) == g.at("acquisition"));
}
```

- [ ] **Step 2: Run to verify it fails**

Run: `CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt cmake -S . -B build && cmake --build build -j 2>&1 | tail -5`
Expected: build FAILS — the new types/functions don't exist.

- [ ] **Step 3: Add the structs to Bundle.h**

Add to `namespace ads1292::io` in `Bundle.h` (constructors must default exactly to the golden values — copy them from the golden file):

```cpp
struct SessionMetadata {
  std::string operator_ = "";          // serialized as "operator"
  std::string subject_id = "untitled"; // (golden uses "p1" when set; default per metadata.py)
  // NOTE: copy the remaining fields + exact defaults (session_id, montage, electrode,
  // acquisition_mode, notes) from the golden "metadata" section.
};
struct QualityGate {
  double min_duration_seconds = 8.0;
  double min_contact_ok_percent = 95.0;
  int min_r_peaks = 5;
  double min_hr_bpm = 35.0;
  double max_hr_bpm = 180.0;
  bool require_qrs_clear = true;
  std::optional<double> max_baseline_drift_counts;   // null in golden
  std::optional<double> max_noise_rms_counts;        // null
  std::optional<double> max_peak_to_peak_counts;     // null
  // NOTE: copy any remaining keys + defaults from the golden "quality_gate" section.
};
struct ProtocolStep { /* fields per golden protocol.steps entries (empty list in default) */ };
struct TestProtocol {
  std::string name = "ADS1292 validation protocol";
  std::string objective = "";
  std::string operator_instructions = "Follow the listed protocol steps.";
  std::string acceptance_notes = "Review quality gate and artifacts before accepting the run.";
  std::vector<ProtocolStep> steps;
};
struct RecordingProcessingSettings {
  // display{gain,sweep_speed_mm_s,time_window_seconds}, software_filters{...7...},
  // ecg_inverted, smoothing_window, processing_notes, sample_rate_hz, schema.
  // Copy exact defaults from the golden "processing" section.
};
struct AcquisitionProvenance {
  // acquisition_mode, channel_map{4}, completion{7}, csv_columns[8], csv_name, csv_schema,
  // live_calibration{}, port, raw_adc{}, sample_rate_hz, schema, started_at, timestamp_reference.
  // Copy exact constant content from the golden "acquisition" section.
};
```

Declare the six `*_payload` free functions (signatures in the Interfaces block above).

- [ ] **Step 4: Implement the `*_payload` functions in Bundle.cpp**

Implement each to build the `nlohmann::json` for its section, copying the exact static strings/structure from the golden file. For `quality_gate`, an unset `std::optional<double>` serializes as `nullptr`:

```cpp
// pattern for nullable fields:
j["max_baseline_drift_counts"] = gate.max_baseline_drift_counts.has_value()
    ? nlohmann::json(gate.max_baseline_drift_counts.value()) : nlohmann::json(nullptr);
```

Build each section's JSON object literally mirroring the golden (channel_map, csv_columns array of 8 objects, completion object, software_filters object, display object, etc.). The test (`== g.at(section)`) is the exact-match gate.

- [ ] **Step 5: Wire CMake, build, run**

Add `test_bundle_sections.cpp` to tests CMake. Build + ctest. Iterate until every `== g.at(section)` passes (diff the mismatching section with the golden to find the offending key/value).

- [ ] **Step 6: Commit**

```bash
git add io/include/ads1292/io/Bundle.h io/src/Bundle.cpp tests/cpp/test_bundle_sections.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P2b bundle sub-objects (metadata/calibration/quality_gate/processing/protocol/acquisition) JSON parity"
```

---

### Task 6: build_recording_bundle assembly — full-bundle JSON parity

**Files:**
- Modify: `io/include/ads1292/io/Bundle.h` (add `build_recording_bundle`), `io/src/Bundle.cpp`
- Create test: `tests/cpp/test_bundle_assembly.cpp`; Modify tests CMake.

**Interfaces:**
- Produces:
  ```cpp
  nlohmann::json build_recording_bundle(
      const std::string& csv_name, const SessionMetadata& metadata,
      const std::vector<EventMarker>& events, const Calibration& calibration,
      const AcquisitionProvenance& acquisition, const TestProtocol& protocol,
      const QualityGate& quality_gate, const RecordingProcessingSettings& processing,
      double sample_rate_hz, const std::string& created_at);
  ```

- [ ] **Step 1: Write the failing full-bundle test**

```cpp
// tests/cpp/test_bundle_assembly.cpp
#include "catch.hpp"
#include "ads1292/io/Bundle.h"
#include "ads1292/model/Calibration.h"
#include "ads1292/model/EventMarker.h"
#include "nlohmann/json.hpp"
#include <fstream>

using nlohmann::json;
using namespace ads1292;
using namespace ads1292::io;

TEST_CASE("build_recording_bundle reproduces the full golden bundle", "[bundle]") {
  std::ifstream in(std::string(FIXTURE_DIR) + "/files/recording_bundle.json");
  json golden; in >> golden;

  json got = build_recording_bundle(
      "rec.csv", SessionMetadata{"fixture", "p1"},
      {{0.02, "touch", "n1", 0.0}, {0.04, "motion", "n2", 0.03}},
      Calibration{}, AcquisitionProvenance{}, TestProtocol{}, QualityGate{},
      RecordingProcessingSettings{}, 500.0, "");
  REQUIRE(got == golden);
}
```

- [ ] **Step 2: Run to verify it fails**

Run: build — FAILS (`build_recording_bundle` not declared).

- [ ] **Step 3: Implement build_recording_bundle**

In `Bundle.cpp`, assemble the top-level object from the section payloads. Copy the exact top-level constants (`schema`, the top-level `csv_name`) from the golden:

```cpp
nlohmann::json build_recording_bundle(
    const std::string& csv_name, const SessionMetadata& metadata,
    const std::vector<EventMarker>& events, const Calibration& calibration,
    const AcquisitionProvenance& acquisition, const TestProtocol& protocol,
    const QualityGate& quality_gate, const RecordingProcessingSettings& processing,
    double sample_rate_hz, const std::string& created_at) {
  nlohmann::json bundle;
  bundle["schema"] = /* copy the golden top-level "schema" string */;
  bundle["created_at"] = created_at;
  bundle["csv_name"] = csv_name;
  bundle["metadata"] = metadata_payload(metadata);
  bundle["calibration"] = calibration_payload(calibration);
  bundle["events"] = events_payload(events, sample_rate_hz);
  bundle["acquisition"] = acquisition_payload(acquisition, sample_rate_hz);
  bundle["protocol"] = protocol_payload(protocol);
  bundle["quality_gate"] = quality_gate_payload(quality_gate);
  bundle["processing"] = processing_payload(processing);
  return bundle;
}
```

> If the golden's top-level `csv_name` differs from the `acquisition.csv_name` (the golden shows top-level `csv_name = "rec.csv"` but `acquisition.csv_name = ""`), keep them distinct exactly as the golden has them.

- [ ] **Step 4: Wire CMake, build, run the full suite**

Add `test_bundle_assembly.cpp` to tests CMake. Build + ctest. Expected: `got == golden` — the full bundle matches key-for-key.

- [ ] **Step 5: Commit**

```bash
git add io/include/ads1292/io/Bundle.h io/src/Bundle.cpp tests/cpp/test_bundle_assembly.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P2b build_recording_bundle full-bundle JSON parity"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's P2 bundle scope):
- recording_bundle 7-part structure → Tasks 4 (events), 5 (6 sub-objects), 6 (assembly) ✓
- event_id (SHA-1) parity → Tasks 2 (SHA-1) + 3 (event_id) ✓
- bundle golden fixture (none existed) → Task 1 ✓
- HDF5 bundle_json embedding → **P2c** (out of scope here; P2c writes this same bundle JSON into the .h5).

**2. Placeholder scan:** Tasks 5 and 6 deliberately reference "copy the exact strings from the committed golden `recording_bundle.json`" for the large static content (channel_map, csv_columns, schemas). This is a precise source reference, not a placeholder — the golden file is committed in Task 1 and is the authoritative, byte-exact spec. The struct field lists in Task 5 Step 3 are sketched with `NOTE: copy … from golden`; the implementer fills exact defaults from the golden, and the `== g.at(section)` test is the gate that proves completeness. This is the one acceptable deviation from full inline code, justified by the volume of static data and the existence of an authoritative committed source.

**3. Type consistency:** `events_payload` (Task 4) signature matches its Task 6 use. `event_id`/`event_sample_indices`/`slug`/`sha1_hex` names match across Tasks 2/3 and their callers. The six `*_payload` functions (Task 5) match their Task 6 assembly calls. `SessionMetadata`/`QualityGate`/`TestProtocol`/`RecordingProcessingSettings`/`AcquisitionProvenance` names match between Task 5 definition and Task 6 usage.

**Risk notes for the executor:**
- The biggest risk is Task 5's volume of exact static content. Work section-by-section: implement one `*_payload`, run the test, diff its section against the golden until it matches, then move to the next. Do NOT try to write all six at once.
- `seconds_to_sample_index` uses `std::nearbyint` (round-half-to-even) to mirror Python `round`; the fixture timestamps are exact (no halfway cases), so `std::round` would also pass here — but `nearbyint` is the faithful choice for arbitrary inputs.
- nlohmann `json` number serialization: integers vs doubles must match the golden (e.g. `sample_rate_hz: 500.0` is a double, `min_r_peaks: 5` an int, `sweep_speed_mm_s: 25` an int). Ensure the C++ literal types match (use `500.0` not `500`, `25` not `25.0`) so nlohmann emits the same JSON number form and `==` holds.
