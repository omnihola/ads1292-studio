# P7b-1: Core Sidecar JSON (metadata / calibration / events) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the three most-reused recording sidecar JSON modules — `metadata`, `calibration`, and `events` (read/write/template) — to C++, verified by reading the committed Python-generated golden sidecars and by C++ write→read round-trips.

**Architecture:** New pure-C++ model structs (`SessionMetadata`, `Calibration`) with `normalized()` live in `core/model`; the JSON read/write/template functions live in `io/` (which already links nlohmann/json). The events JSON reuses the existing `EventMarker` model + the golden-tested `EventId` (`event_id`, `event_sample_indices`). Parity is **semantic/structural** (round-trip + read the Python golden), NOT byte-identical formatting — consistent with the P2 sidecar-compatibility decision. This is the first slice of P7b; `acquisition`/`processing`/`protocol` sidecars + `session_index` + `batch` follow in later P7b slices.

**Tech Stack:** C++17, CMake, Catch2 + nlohmann/json (already vendored + linked in `io`). Oracle: `metadata.py`, `calibration.py`, `events.py`. Golden: `tests/fixtures/golden/sidecar/{metadata,calibration,calibration_custom,events}.json` (committed, Python-generated).

## Global Constraints

- **C++17**; `core/model` structs are pure portable C++ (stdlib only, no Qt/OS). The JSON read/write lives in `io/` (links nlohmann/json — already a dep).
- **Layering**: `core/model` (structs + normalized) ← `io/` (JSON read/write, uses nlohmann/json + the model + `EventId`). No Qt.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Parity gates:** SEMANTIC — (1) reading the committed Python golden sidecar yields the expected field values; (2) C++ `write→read` round-trips to an equal (normalized) object. Byte-identical JSON formatting is NOT required (use `nlohmann::ordered_json` + `dump(2)` + trailing `"\n"` to stay close, but do not gate on it).
- **`SessionMetadata` (metadata.py):** fields (in this order) `std::string session_id="", subject_id="anonymous", electrode="", montage="RA/LA/RL torso", operator_=""` (note: `operator` is a C++ keyword — name the field `operator_` or `operator_name` and map it to the JSON key `"operator"`), `notes="", acquisition_mode="live_stream"`. `normalized()`: `_clean(v, fallback)` = trimmed value or fallback if empty — session_id→"untitled-session", subject_id→"anonymous", electrode→"unspecified electrode", montage→"unspecified montage", operator→"unspecified operator", acquisition_mode→"live_stream"; `notes` = trimmed (no fallback). `read_metadata_json`: parse object, keep only allowed keys, construct + normalize (ignore unknown keys; the JSON key is `"operator"`). `write_metadata_json`: write `asdict(normalized)` (keys in field order, JSON key `"operator"`). `metadata_template()`: `session_id="YYYYMMDD-run-001", subject_id="anonymous", electrode="commercial Ag/AgCl control or MOTAC gel + Ag/AgCl", montage="RA/LA/RL torso", operator="", notes="posture, movement condition, skin prep, gel formulation, electrode placement"` (acquisition_mode default). (When the template is normalized for writing, `operator=""`→`"unspecified operator"`.)
- **`Calibration` (calibration.py):** `double vref_mv=2420.0, pga_gain=6.0; int adc_bits=24; std::string label="ADS1292 default"`. `normalized()`: `vref_mv = vref_mv>0 ? vref_mv : 2420.0`; `pga_gain = pga_gain>0 ? pga_gain : 6.0`; `adc_bits = adc_bits>=2 ? adc_bits : 24`; `label = trim(label) or "ADS1292 default"`. `microvolts_per_count()`: `n=normalized(); full_scale=2^(n.adc_bits-1); return n.vref_mv * 1000.0 / (n.pga_gain * full_scale)`. `read_calibration_json` (filter allowed keys + construct + normalize), `write_calibration_json` (asdict normalized), `calibration_template()` = `Calibration{}` (defaults).
- **`events` JSON (events.py):** schema constants — `EVENT_ANNOTATIONS_SCHEMA="ads1292-event-annotations-v1"`, `EVENT_TIMESTAMP_REFERENCE="relative_seconds_from_recording_start"`, `EVENT_SAMPLE_INDEX_REFERENCE="zero_based_sample_index_at_recording_sample_rate"`, `DEFAULT_EVENT_SAMPLE_RATE_HZ=500.0`. `write_events_json(path, events, sample_rate_hz=500.0)`: `sr=normalized_sample_rate(sample_rate_hz)` (if `!finite||<=0` → 500.0); payload object `{ "schema": SCHEMA, "timestamp_reference": REF, "sample_rate_hz": sr, "sample_index_reference": IDX_REF, "events": [ entry per event ] }`; each entry (via `EventId`, all already in C++): `{ "event_id": event_id(marker, sr), "timestamp_seconds": ts, "start_seconds": ts, "end_seconds": end_seconds(marker), "duration_seconds": dur, "start_sample_index": idx.start, "end_sample_index": idx.end, "duration_samples": idx.duration, "event_type": marker.is_interval() ? "interval" : "point", "label": label, "notes": notes }` where `marker=event.normalized()`, `idx=event_sample_indices(marker, sr)`. `read_events_json(path)`: parse; if the root is an object take its `"events"` array (else the root IS the array); for each object item → `EventMarker` via: `timestamp = item.timestamp_seconds ?? item.start_seconds ?? 0`; `duration = item.duration_seconds`; if duration null/empty → `start=item.start_seconds ?? timestamp; end=item.end_seconds ?? start; duration=max(0,end-start); timestamp=start`; build `EventMarker{timestamp, label=item.label ?? "", notes=item.notes ?? "", duration}.normalized()`. `event_template()` = `{ EventMarker{5.0, "motion", "subject moved arm", 3.0}, ... }` (read the full template tuple from events.py).

## File Structure

```
core/
  include/ads1292/model/SessionMetadata.h     # struct + normalized
  src/model/SessionMetadata.cpp
  include/ads1292/model/Calibration.h          # struct + normalized + microvolts_per_count
  src/model/Calibration.cpp
io/
  include/ads1292/io/MetadataIo.h              # read/write/template
  src/MetadataIo.cpp
  include/ads1292/io/CalibrationIo.h
  src/CalibrationIo.cpp
  include/ads1292/io/EventsIo.h                # read/write/template (reuses EventId)
  src/EventsIo.cpp
tests/cpp/
  test_metadata_io.cpp
  test_calibration_io.cpp
  test_events_io.cpp
```

---

### Task 1: metadata sidecar (SessionMetadata + JSON)

**Files:**
- Create: `core/include/ads1292/model/SessionMetadata.h`, `core/src/model/SessionMetadata.cpp`; `io/include/ads1292/io/MetadataIo.h`, `io/src/MetadataIo.cpp`.
- Modify: `core/CMakeLists.txt`, `io/CMakeLists.txt`; Create `tests/cpp/test_metadata_io.cpp`; Modify tests CMake.

**Interfaces:**
- Produces: `ads1292::SessionMetadata { std::string session_id, subject_id, electrode, montage, operator_, notes, acquisition_mode; SessionMetadata normalized() const; };` (defaults per Global Constraints). `ads1292::io::SessionMetadata read_metadata_json(const std::string& path);`, `void write_metadata_json(const std::string& path, const SessionMetadata& m);`, `SessionMetadata metadata_template();`.

- [ ] **Step 1: Write the failing test** (read the golden + round-trip)

```cpp
// tests/cpp/test_metadata_io.cpp
#include "catch.hpp"
#include "ads1292/io/MetadataIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }

TEST_CASE("read golden metadata.json", "[sidecar]") {
  auto m = io::read_metadata_json(fx("metadata.json"));
  REQUIRE(m.session_id == "YYYYMMDD-run-001");
  REQUIRE(m.subject_id == "anonymous");
  REQUIRE(m.montage == "RA/LA/RL torso");
  REQUIRE(m.operator_ == "unspecified operator");   // template's "" normalized to fallback
  REQUIRE(m.acquisition_mode == "live_stream");
}
TEST_CASE("metadata round-trips", "[sidecar]") {
  SessionMetadata m; m.session_id="s1"; m.subject_id="subj"; m.electrode="e"; m.operator_="op"; m.notes="  n  ";
  auto p = (std::filesystem::temp_directory_path() / "p7b_meta.json").string();
  io::write_metadata_json(p, m);
  auto back = io::read_metadata_json(p);
  REQUIRE(back.session_id == "s1");
  REQUIRE(back.notes == "n");                        // trimmed
  REQUIRE(back.operator_ == "op");
  REQUIRE(back.montage == "RA/LA/RL torso");
}
TEST_CASE("metadata_template normalizes operator", "[sidecar]") {
  auto t = io::metadata_template();
  REQUIRE(io::read_metadata_json([&]{ auto p=(std::filesystem::temp_directory_path()/"p7b_tmpl.json").string(); io::write_metadata_json(p,t); return p; }()).operator_ == "unspecified operator");
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `SessionMetadata` + `normalized` (core), and `MetadataIo` (io) using `nlohmann::ordered_json`: read = parse object, for each known key set the field (JSON key `"operator"` → `operator_`), then `normalized()`; write = build an ordered_json with keys in field order (`"operator"` for `operator_`), `dump(2)` + `"\n"`; template per Global Constraints. Unknown keys are ignored on read; missing keys keep defaults.

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/model/SessionMetadata.h core/src/model/SessionMetadata.cpp io/include/ads1292/io/MetadataIo.h io/src/MetadataIo.cpp core/CMakeLists.txt io/CMakeLists.txt tests/cpp/test_metadata_io.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P7b metadata sidecar (SessionMetadata + JSON read/write/template)"
```

---

### Task 2: calibration sidecar (Calibration + JSON)

**Files:**
- Create: `core/include/ads1292/model/Calibration.h`, `core/src/model/Calibration.cpp`; `io/include/ads1292/io/CalibrationIo.h`, `io/src/CalibrationIo.cpp`.
- Modify: `core/CMakeLists.txt`, `io/CMakeLists.txt`; Create `tests/cpp/test_calibration_io.cpp`; Modify tests CMake.

**Interfaces:**
- Produces: `ads1292::Calibration { double vref_mv, pga_gain; int adc_bits; std::string label; Calibration normalized() const; double microvolts_per_count() const; };`. `ads1292::io::Calibration read_calibration_json(const std::string&);`, `void write_calibration_json(const std::string&, const Calibration&);`, `Calibration calibration_template();`.

- [ ] **Step 1: Write the failing test**

```cpp
// tests/cpp/test_calibration_io.cpp
#include "catch.hpp"
#include "ads1292/io/CalibrationIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }

TEST_CASE("read golden calibration.json (defaults)", "[sidecar]") {
  auto c = io::read_calibration_json(fx("calibration.json"));
  REQUIRE(c.vref_mv == Approx(2420.0)); REQUIRE(c.pga_gain == Approx(6.0));
  REQUIRE(c.adc_bits == 24); REQUIRE(c.label == "ADS1292 default");
}
TEST_CASE("read golden calibration_custom.json", "[sidecar]") {
  auto c = io::read_calibration_json(fx("calibration_custom.json"));
  REQUIRE(c.vref_mv == Approx(2400.0)); REQUIRE(c.pga_gain == Approx(12.0)); REQUIRE(c.label == "custom");
}
TEST_CASE("microvolts_per_count matches the datasheet formula", "[sidecar]") {
  Calibration c;  // defaults: 2420 mV, gain 6, 24 bits
  // vref_mv*1000 / (gain * 2^23) = 2420000 / (6 * 8388608)
  REQUIRE(c.microvolts_per_count() == Approx(2420.0*1000.0/(6.0*8388608.0)));
}
TEST_CASE("calibration normalizes invalid values + round-trips", "[sidecar]") {
  Calibration c; c.vref_mv=-1; c.pga_gain=0; c.adc_bits=1; c.label="  ";
  auto n = c.normalized();
  REQUIRE(n.vref_mv == Approx(2420.0)); REQUIRE(n.pga_gain == Approx(6.0)); REQUIRE(n.adc_bits == 24); REQUIRE(n.label == "ADS1292 default");
  auto p = (std::filesystem::temp_directory_path() / "p7b_cal.json").string();
  io::write_calibration_json(p, Calibration{2400.0, 12.0, 24, "x"});
  REQUIRE(io::read_calibration_json(p).label == "x");
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `Calibration` + `normalized` + `microvolts_per_count` (core) and `CalibrationIo` (io) per the Global Constraints.

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit**

```bash
git add core/include/ads1292/model/Calibration.h core/src/model/Calibration.cpp io/include/ads1292/io/CalibrationIo.h io/src/CalibrationIo.cpp core/CMakeLists.txt io/CMakeLists.txt tests/cpp/test_calibration_io.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P7b calibration sidecar (Calibration + JSON + microvolts_per_count)"
```

---

### Task 3: events sidecar JSON (read/write/template)

**Files:**
- Create: `io/include/ads1292/io/EventsIo.h`, `io/src/EventsIo.cpp`.
- Modify: `io/CMakeLists.txt`; Create `tests/cpp/test_events_io.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: `ads1292::EventMarker` (core/model), `ads1292::event::event_id`/`event_sample_indices` (core/event — already golden-tested).
- Produces: `ads1292::io::std::vector<ads1292::EventMarker> read_events_json(const std::string& path);`, `void write_events_json(const std::string& path, const std::vector<ads1292::EventMarker>& events, double sample_rate_hz = 500.0);`, `std::vector<ads1292::EventMarker> event_template();`.

- [ ] **Step 1: Write the failing test** (read the golden payload + round-trip)

```cpp
// tests/cpp/test_events_io.cpp
#include "catch.hpp"
#include "ads1292/io/EventsIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }

TEST_CASE("read golden events.json", "[sidecar]") {
  auto evs = io::read_events_json(fx("events.json"));
  REQUIRE(evs.size() >= 1);
  REQUIRE(evs[0].label == "motion");
  REQUIRE(evs[0].timestamp_seconds == Approx(5.0));
  REQUIRE(evs[0].duration_seconds == Approx(3.0));     // interval 5..8
  REQUIRE(evs[0].notes == "subject moved arm");
}
TEST_CASE("events round-trip preserves markers", "[sidecar]") {
  std::vector<EventMarker> in = { EventMarker{2.0,"a","n1",0.0}, EventMarker{4.0,"b","",1.5} };
  auto p = (std::filesystem::temp_directory_path() / "p7b_events.json").string();
  io::write_events_json(p, in, 500.0);
  auto back = io::read_events_json(p);
  REQUIRE(back.size() == 2);
  REQUIRE(back[0].label == "a"); REQUIRE(back[0].timestamp_seconds == Approx(2.0));
  REQUIRE(back[1].duration_seconds == Approx(1.5));
}
TEST_CASE("written events.json carries the schema + event_id", "[sidecar]") {
  std::vector<EventMarker> in = { EventMarker{5.0,"motion","subject moved arm",3.0} };
  auto p = (std::filesystem::temp_directory_path() / "p7b_events_schema.json").string();
  io::write_events_json(p, in, 500.0);
  std::ifstream f(p); std::string s((std::istreambuf_iterator<char>(f)), {});
  REQUIRE(s.find("ads1292-event-annotations-v1") != std::string::npos);
  REQUIRE(s.find("evt-0002500-0004000-motion-") != std::string::npos);   // event_id prefix from P4 EventId
  REQUIRE(s.find("\"event_type\": \"interval\"") != std::string::npos);
}
```
(Include `<fstream>`, `<iterator>`.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `EventsIo` per the Global Constraints: `write_events_json` builds the schema payload + per-event entries (reusing `event_id` + `event_sample_indices`); `read_events_json` parses the `"events"` array (or a bare array) with the forgiving timestamp/start/end/duration fallback logic; `event_template` returns the template markers (read the full tuple from `events.py`).

- [ ] **Step 4: Wire CMake, build, run.** Iterate until the golden read + round-trip + schema/event_id checks pass.

- [ ] **Step 5: Commit**

```bash
git add io/include/ads1292/io/EventsIo.h io/src/EventsIo.cpp io/CMakeLists.txt tests/cpp/test_events_io.cpp tests/cpp/CMakeLists.txt
git commit -m "feat: P7b events sidecar JSON (read/write/template, reuses EventId)"
```

---

## Self-Review

**1. Spec coverage** (against the P7b-1 slice — core sidecar JSON):
- metadata sidecar (struct + normalized + read/write/template) → Task 1 ✓
- calibration sidecar (struct + normalized + microvolts_per_count + read/write/template) → Task 2 ✓
- events sidecar JSON (read/write/template, schema payload + event_id) → Task 3 ✓
- acquisition / processing / protocol sidecars → later P7b slice (out of scope)
- session_index + batch → later P7b slice (out of scope)

**2. Placeholder scan:** The struct fields + normalized rules + JSON payload shapes are spelled out concretely; every test body is concrete; the golden fixtures are committed (`tests/fixtures/golden/sidecar/`). The events template tuple + the events.py forgiving-read logic are referenced to the oracle for the exact remaining entries — the executor reads them from `events.py`. Parity is semantic (read golden + round-trip), explicitly NOT byte-identical.

**3. Type consistency:** `SessionMetadata` (Task 1) + `Calibration` (Task 2) are independent core structs; `EventMarker`/`event_id`/`event_sample_indices` (existing) reused by Task 3. The io functions (`read_*_json`/`write_*_json`/`*_template`) follow one consistent signature shape across all three modules. `operator_` ↔ JSON `"operator"` is the only name-mapping (C++ keyword).

**Risk notes for the executor:**
- `operator` is a C++ keyword — the field MUST be named `operator_` (or similar) and mapped to/from the JSON key `"operator"`.
- Parity is SEMANTIC: gate on reading the committed Python golden + C++ round-trip, NOT on byte-identical JSON. Use `nlohmann::ordered_json` + `dump(2)` + `"\n"` to stay close, but a formatting difference (e.g. `2420.0` vs `2420`) is NOT a failure as long as the round-trip + golden-read pass.
- `read_*_json` must IGNORE unknown keys and keep defaults for missing keys (matches the Python `allowed`-filter + dataclass defaults).
- Task 3 reuses the golden-tested `event_id`/`event_sample_indices` (P4) — do NOT reimplement them; the golden `events.json` event_id (`evt-0002500-0004000-motion-...`) should match what the C++ `event_id` produces for `EventMarker{5.0,"motion",...,3.0}` at 500 Hz.
- Read the full `event_template()` tuple from `events.py` for Task 3's template.
- Keep `core/model` Qt-free; the JSON lives in `io` (which already links nlohmann/json).
