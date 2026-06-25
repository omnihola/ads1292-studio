# P7b-2: Remaining Sidecar JSON (processing / protocol / acquisition) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the three remaining recording sidecar JSON modules — `processing` (display/filter settings), `protocol` (test protocol + steps), and `acquisition` (provenance) — completing the sidecar layer, verified by reading the committed Python-generated golden sidecars + C++ round-trips.

**Architecture:** New pure-C++ model structs (`RecordingProcessingSettings`, `TestProtocol`/`ProtocolStep`, `AcquisitionProvenance`) with `normalized()` in `core/model`; JSON read/write/template in `io/` (nlohmann/json). `processing` reuses the existing P5d `EcgDisplaySettings`/`SoftwareFilterSettings` for its nested `display`/`software_filters` sub-objects. Parity is **semantic** (read the Python golden + round-trip), NOT byte-identical — consistent with P7b-1 + the P2 sidecar decision. After this slice the full sidecar set is done; `session_index` + `batch` follow in P7b-3.

**Tech Stack:** C++17, CMake, Catch2 + nlohmann/json (linked in `io`). Oracle: `processing.py`, `protocol.py`, `acquisition.py`. Golden: `tests/fixtures/golden/sidecar/{processing,protocol,acquisition}.json` (committed, Python-generated).

## Global Constraints

- **C++17**; `core/model` structs pure portable C++ (stdlib + nlohmann::json ONLY where a field is genuinely an arbitrary JSON blob — see acquisition; otherwise no nlohmann in core). The JSON read/write lives in `io/`. No Qt.
- **Layering**: `core/model` (structs + normalized) ← `io/` (JSON read/write). `processing` reuses P5d `EcgDisplaySettings`/`SoftwareFilterSettings` (core/dsp). No Qt anywhere.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Parity gates:** SEMANTIC — (1) reading the committed Python golden sidecar yields the expected field values; (2) C++ `write→read` round-trips to an equal normalized object. Byte-identical JSON NOT required (use `nlohmann::ordered_json` + `dump(2)` + `"\n"`).
- **`RecordingProcessingSettings` (processing.py):** schema constants `PROCESSING_SCHEMA="ads1292-processing-settings-v1"`, `PROCESSING_NOTES="display settings only; raw CSV samples are unchanged"`. Fields: `std::string schema=PROCESSING_SCHEMA; <display sub-object>; <software_filters sub-object>; double sample_rate_hz=500.0; bool ecg_inverted=false; int smoothing_window=11; std::string processing_notes=PROCESSING_NOTES`. The `display` JSON object = `{time_window_seconds, gain, sweep_speed_mm_s}` (an `EcgDisplaySettings`); the `software_filters` JSON object = `{highpass_enabled, notch_enabled, lowpass_enabled, bandpass_enabled, highpass_hz, notch_hz, lowpass_hz}` (a `SoftwareFilterSettings`). `normalized()`: `display = EcgDisplaySettings(display).normalized()`; `software_filters = SoftwareFilterSettings(software_filters)` (filters have no normalize); `schema=trim||default`; `sample_rate_hz = >0?·:500`; `smoothing_window=max(1,·)`; `processing_notes=trim||default`. Read fills the struct from the JSON (including the nested display/filters sub-objects), keeps defaults for missing, normalizes. Write = `ordered_json` with keys in field order (schema, display, software_filters, sample_rate_hz, ecg_inverted, smoothing_window, processing_notes), nested objects in their field orders. `build_processing_settings(display, filters, sr, ecg_inverted, smoothing_window)` (the template/builder) → defaults per the golden.
- **`ProtocolStep` (protocol.py):** `double start_seconds, duration_seconds; std::string label, instruction`. `normalized()`: `start=max(0,·)`, `duration=max(0,·)`, `label=clean(label,"step")`, `instruction=clean(instruction,"Follow the protocol step.")`.
- **`TestProtocol` (protocol.py):** schema `PROTOCOL_SCHEMA` (read it from protocol.py), `std::string name="ADS1292 validation protocol", objective="", operator_instructions="Follow the listed protocol steps."; std::vector<ProtocolStep> steps; std::string acceptance_notes="Review quality gate and artifacts before accepting the run."`. `normalized()`: each step normalized; `name=clean(name,default)`, `objective=trim`, `operator_instructions=clean(·,default)`, `acceptance_notes=clean(·,default)`. `read_protocol_json`: object (else throw); `steps` from `data["steps"]` array (forgiving per-step via `_step_from_mapping`: filter allowed keys, defaults start/duration 0, label/instruction ""); `name/objective/operator_instructions/acceptance_notes` = `str(data.get(key,""))`; then NOT auto-normalized on read? — match the oracle: `read_protocol_json` returns `TestProtocol(...)` WITHOUT calling `.normalized()` (verify in protocol.py; if it does normalize, match it). `write_protocol_json`: write `asdict(protocol.normalized())` (keys: name, objective, operator_instructions, steps[], acceptance_notes; each step: start_seconds, duration_seconds, label, instruction). `protocol_template()` = the specific values in the golden `protocol.json` (name "MOTAC ECG validation", 3 steps baseline/motion/recovery — read the exact tuple from protocol.py).
- **`AcquisitionProvenance` (acquisition.py):** 14 fields — `std::string schema=ACQUISITION_SCHEMA, csv_name="", csv_schema=LIVE_CSV_SCHEMA, acquisition_mode="live_stream", port="", started_at="", timestamp_reference=TIMESTAMP_REFERENCE; double sample_rate_hz=500.0; std::map<std::string,std::string> channel_map; std::vector<...> csv_columns; nlohmann::json raw_adc, live_calibration, completion;` (schema constants: `ACQUISITION_SCHEMA="ads1292-acquisition-provenance-v1"`, `LIVE_CSV_SCHEMA="ads1292-studio-live-stream-v1"`, `RAW_CSV_SCHEMA="ads1292-studio-raw-adc-v1"`, `TIMESTAMP_REFERENCE="relative_seconds_from_recording_start"`). `channel_map` defaults to `default_channel_map()` (4 entries — read from acquisition.py); `csv_columns` is an array of `{name, unit, description}` defaulting to `default_csv_columns(mode, include_live_calibration)`. `normalized()`: `mode = _normalized_mode(acquisition_mode)`; `csv_schema = mode=="raw_adc_24bit" ? RAW_CSV_SCHEMA : LIVE_CSV_SCHEMA`; trim string fields (schema/csv_name/port/started_at → trim, schema falls back to default); `sample_rate_hz = >0?·:500`; `timestamp_reference = _clean_timestamp_reference`; `channel_map = clean_string_map(channel_map) or default_channel_map()`; `csv_columns = clean_csv_columns(·) or default_csv_columns(mode, include_live_calibration=!live_calibration.empty())`; `raw_adc/live_calibration` passed through; `completion = _clean_completion(completion)`. (Read the exact `_normalized_mode`/`_clean_*`/`default_*` helpers from acquisition.py.) `read_acquisition_json`/`write_acquisition_json` (asdict normalized, ordered_json, field order). NOTE: `raw_adc`/`live_calibration`/`completion` are arbitrary JSON blobs — store them as `nlohmann::json` and pass through (so use `nlohmann::json` in the AcquisitionProvenance struct; this is the one core struct that may include nlohmann, OR keep the struct in `io` rather than core — your choice, document it).
- **`clean(value, fallback)`** (all three modules): trimmed value or fallback if empty after trim (ASCII whitespace). Reuse the same helper pattern as P7b-1's metadata.

## File Structure

```
core/include/ads1292/model/RecordingProcessingSettings.h   # (+ .cpp) struct + normalized (reuses EcgDisplaySettings/SoftwareFilterSettings)
core/include/ads1292/model/TestProtocol.h                  # (+ .cpp) ProtocolStep + TestProtocol + normalized
io/include/ads1292/io/ProcessingIo.h                       # (+ .cpp) read/write/build
io/include/ads1292/io/ProtocolIo.h                         # (+ .cpp) read/write/template
io/include/ads1292/io/AcquisitionIo.h                      # (+ .cpp) AcquisitionProvenance (struct may live here) + read/write/template
tests/cpp/test_processing_io.cpp
tests/cpp/test_protocol_io.cpp
tests/cpp/test_acquisition_io.cpp
```

---

### Task 1: processing sidecar (RecordingProcessingSettings + JSON)

**Files:** Create `core/.../model/RecordingProcessingSettings.{h,cpp}`, `io/.../ProcessingIo.{h,cpp}`; Modify core/io CMake; Create `tests/cpp/test_processing_io.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: P5d `EcgDisplaySettings`/`SoftwareFilterSettings` (core/dsp).
- Produces: `ads1292::RecordingProcessingSettings { std::string schema; ads1292::dsp::EcgDisplaySettings display; ads1292::dsp::SoftwareFilterSettings software_filters; double sample_rate_hz; bool ecg_inverted; int smoothing_window; std::string processing_notes; RecordingProcessingSettings normalized() const; };`. `ads1292::io::RecordingProcessingSettings read_processing_json(const std::string&); void write_processing_json(const std::string&, const RecordingProcessingSettings&); RecordingProcessingSettings build_processing_settings();` (defaults).

- [ ] **Step 1: Write the failing test**

```cpp
// tests/cpp/test_processing_io.cpp
#include "catch.hpp"
#include "ads1292/io/ProcessingIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }
TEST_CASE("read golden processing.json", "[sidecar]") {
  auto p = io::read_processing_json(fx("processing.json"));
  REQUIRE(p.schema == "ads1292-processing-settings-v1");
  REQUIRE(p.sample_rate_hz == Approx(500.0));
  REQUIRE(p.smoothing_window == 11);
  REQUIRE(p.display.time_window_seconds == Approx(8.0));
  REQUIRE(p.software_filters.notch_hz == Approx(60.0));
  REQUIRE(p.processing_notes == "display settings only; raw CSV samples are unchanged");
}
TEST_CASE("processing round-trips + normalizes smoothing", "[sidecar]") {
  RecordingProcessingSettings p; p.sample_rate_hz=-1; p.smoothing_window=0; p.schema="  ";
  auto n = p.normalized();
  REQUIRE(n.sample_rate_hz == Approx(500.0)); REQUIRE(n.smoothing_window == 1);
  REQUIRE(n.schema == "ads1292-processing-settings-v1");
  auto path = (std::filesystem::temp_directory_path()/"p7b2_proc.json").string();
  io::write_processing_json(path, io::build_processing_settings());
  REQUIRE(io::read_processing_json(path).smoothing_window == 11);
}
```

- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement** per Global Constraints (reuse EcgDisplaySettings/SoftwareFilterSettings for the nested objects; their JSON keys are the struct field names). Read the exact `build_processing_settings` defaults from processing.py.
- [ ] **Step 4: Wire CMake, build, run.**
- [ ] **Step 5: Commit** `git commit -m "feat: P7b processing sidecar (RecordingProcessingSettings + JSON)"`

---

### Task 2: protocol sidecar (TestProtocol/ProtocolStep + JSON)

**Files:** Create `core/.../model/TestProtocol.{h,cpp}`, `io/.../ProtocolIo.{h,cpp}`; Modify core/io CMake; Create `tests/cpp/test_protocol_io.cpp`; Modify tests CMake.

**Interfaces:**
- Produces: `ads1292::ProtocolStep { double start_seconds, duration_seconds; std::string label, instruction; ProtocolStep normalized() const; };`, `ads1292::TestProtocol { std::string name, objective, operator_instructions; std::vector<ProtocolStep> steps; std::string acceptance_notes; TestProtocol normalized() const; };`. `ads1292::io::TestProtocol read_protocol_json(const std::string&); void write_protocol_json(const std::string&, const TestProtocol&); TestProtocol protocol_template();`.

- [ ] **Step 1: Write the failing test**

```cpp
// tests/cpp/test_protocol_io.cpp
#include "catch.hpp"
#include "ads1292/io/ProtocolIo.h"
#include <filesystem>
using namespace ads1292;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }
TEST_CASE("read golden protocol.json", "[sidecar]") {
  auto p = io::read_protocol_json(fx("protocol.json"));
  REQUIRE(p.name == "MOTAC ECG validation");
  REQUIRE(p.steps.size() == 3);
  REQUIRE(p.steps[0].label == "baseline");
  REQUIRE(p.steps[1].start_seconds == Approx(30.0));
  REQUIRE(p.steps[2].label == "recovery");
}
TEST_CASE("protocol round-trips + step normalize", "[sidecar]") {
  TestProtocol p; p.name="  "; p.steps = { ProtocolStep{-1.0, -2.0, "", ""} };
  auto n = p.normalized();
  REQUIRE(n.name == "ADS1292 validation protocol");
  REQUIRE(n.steps[0].start_seconds == Approx(0.0)); REQUIRE(n.steps[0].label == "step");
  auto path = (std::filesystem::temp_directory_path()/"p7b2_proto.json").string();
  io::write_protocol_json(path, io::protocol_template());
  auto back = io::read_protocol_json(path);
  REQUIRE(back.steps.size() >= 1);
}
```

- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement** per Global Constraints (read the exact `protocol_template()` tuple + `read_protocol_json` forgiving step logic + whether read normalizes from protocol.py).
- [ ] **Step 4: Wire CMake, build, run.**
- [ ] **Step 5: Commit** `git commit -m "feat: P7b protocol sidecar (TestProtocol/ProtocolStep + JSON)"`

---

### Task 3: acquisition sidecar (AcquisitionProvenance + JSON)

**Files:** Create `io/.../AcquisitionIo.{h,cpp}` (the `AcquisitionProvenance` struct may live in this io header since it carries `nlohmann::json` blob fields); Modify io CMake; Create `tests/cpp/test_acquisition_io.cpp`; Modify tests CMake.

**Interfaces:**
- Produces (namespace `ads1292::io`): `struct CsvColumn { std::string name, unit, description; };`, `struct AcquisitionProvenance { std::string schema, csv_name, csv_schema, acquisition_mode, port, started_at, timestamp_reference; double sample_rate_hz; std::map<std::string,std::string> channel_map; std::vector<CsvColumn> csv_columns; nlohmann::json raw_adc, live_calibration, completion; AcquisitionProvenance normalized() const; };`. `AcquisitionProvenance read_acquisition_json(const std::string&); void write_acquisition_json(const std::string&, const AcquisitionProvenance&);` + a `default_channel_map()` + `default_csv_columns(mode, include_live_calibration)` + a template/default.

- [ ] **Step 1: Write the failing test** (golden-read + round-trip; the heaviest sidecar)

```cpp
// tests/cpp/test_acquisition_io.cpp
#include "catch.hpp"
#include "ads1292/io/AcquisitionIo.h"
#include <filesystem>
using namespace ads1292::io;
namespace { std::string fx(const std::string& n){ return std::string(FIXTURE_DIR) + "/sidecar/" + n; } }
TEST_CASE("read golden acquisition.json", "[sidecar]") {
  auto a = read_acquisition_json(fx("acquisition.json"));
  REQUIRE(a.schema == "ads1292-acquisition-provenance-v1");
  REQUIRE(a.csv_name == "rec.csv");
  REQUIRE(a.csv_schema == "ads1292-studio-live-stream-v1");
  REQUIRE(a.acquisition_mode == "live_stream");
  REQUIRE(a.port == "/dev/ttyUSB0");
  REQUIRE(a.channel_map.at("ch2_counts") == "CH2 ECG Lead I (LA-RA)");
  REQUIRE(a.csv_columns.size() >= 3);
  REQUIRE(a.csv_columns[0].name == "timestamp");
}
TEST_CASE("acquisition normalized fills channel_map default + round-trips", "[sidecar]") {
  AcquisitionProvenance a; a.csv_name="x.csv"; a.acquisition_mode="live_stream"; // empty channel_map
  auto n = a.normalized();
  REQUIRE_FALSE(n.channel_map.empty());            // defaults filled
  REQUIRE(n.csv_schema == "ads1292-studio-live-stream-v1");
  auto path = (std::filesystem::temp_directory_path()/"p7b2_acq.json").string();
  write_acquisition_json(path, n);
  auto back = read_acquisition_json(path);
  REQUIRE(back.csv_name == "x.csv");
  REQUIRE(back.channel_map.size() == n.channel_map.size());
}
```

- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement** `AcquisitionProvenance` + `normalized()` (mode→csv_schema, empty channel_map→default_channel_map, empty csv_columns→default_csv_columns(mode, include_live_calibration), trim strings, sample_rate normalize, _clean_completion) + read/write JSON. READ the exact `_normalized_mode`, `_clean_string_map`, `_clean_csv_columns`, `_clean_completion`, `_clean_timestamp_reference`, `default_channel_map`, `default_csv_columns`, `_csv_column_entry`, the CANONICAL_HEADER/RAW_HEADER/LIVE_CALIBRATION_COLUMNS from acquisition.py and replicate them. `raw_adc`/`live_calibration`/`completion` are arbitrary JSON → store/round-trip as `nlohmann::json`. Use ordered_json on write with the 14 keys in field order.
- [ ] **Step 4: Wire CMake, build, run.** Iterate until golden-read + round-trip pass.
- [ ] **Step 5: Commit** `git commit -m "feat: P7b acquisition sidecar (AcquisitionProvenance + JSON)"`

---

## Self-Review

**1. Spec coverage:** processing → Task 1 ✓; protocol → Task 2 ✓; acquisition → Task 3 ✓. session_index + batch → P7b-3 (out of scope).

**2. Placeholder scan:** struct fields + normalized rules + golden shapes are spelled out; tests are concrete; goldens committed (`processing/protocol/acquisition.json`). The elaborate acquisition helpers (`default_csv_columns`, `_clean_*`) + protocol template tuple + processing build defaults are referenced to the oracle for the exact remaining detail — the executor reads them from the .py. Parity is semantic.

**3. Type consistency:** `RecordingProcessingSettings` reuses `EcgDisplaySettings`/`SoftwareFilterSettings` (existing). `ProtocolStep`/`TestProtocol` independent. `AcquisitionProvenance`/`CsvColumn` independent (io, with nlohmann::json blob fields). All io functions follow the `read_*_json`/`write_*_json`/`*_template`-or-`build_*` shape.

**Risk notes for the executor:**
- Parity is SEMANTIC (golden-read + round-trip), not byte-identical.
- `processing`'s nested `display`/`software_filters` JSON objects use the EXISTING `EcgDisplaySettings`/`SoftwareFilterSettings` field names as keys — serialize/deserialize those sub-objects field-by-field.
- `acquisition` is the heaviest: replicate `normalized()`'s mode→csv_schema + default_channel_map/default_csv_columns logic EXACTLY from acquisition.py; `raw_adc`/`live_calibration`/`completion` are arbitrary JSON blobs (store as `nlohmann::json`). If a sub-helper proves very large, port it faithfully — the golden-read + round-trip gate it.
- Read whether `read_protocol_json`/`read_processing_json`/`read_acquisition_json` call `.normalized()` on the result (match the oracle exactly — some read paths normalize, some don't).
- Keep `core/model` structs Qt-free; `AcquisitionProvenance` carrying `nlohmann::json` means it lives in `io` (or core links nlohmann — prefer io to keep core clean).
