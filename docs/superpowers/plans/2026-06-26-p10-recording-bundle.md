# P10: recording_bundle (write canonical + read + index/batch interop) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Close the recording_bundle gap (audit section A): rewrite the early P2-era `Bundle.{h,cpp}` to use the CANONICAL model/sidecar types (eliminating its duplicate `ads1292::io` types + the `AcquisitionProvenance` ODR clash + the stub `ProtocolStep`), add the bundle READ side, and wire bundle detection into the session-index/batch consumers so C++ correctly scans Python-produced recording bundles. GUI write-on-save is a SEPARATE later decision (Task 4 deferred).

**Architecture:** A Python recording's `.json` (at `csv.with_suffix(".json")`) is EITHER a recording bundle (`{"schema":"ads1292-recording-bundle-v1", created_at, csv_name, metadata, events, calibration, acquisition, protocol, quality_gate, processing}`) OR a plain metadata sidecar — distinguished by the `schema` key. Each bundle sub-object equals the corresponding individual sidecar's JSON (Python: both use `asdict(x.normalized())` / the same events payload). So we extract `*_to_json(const T&) -> nlohmann::ordered_json` helpers from the 7 P7b writers (writer = `*_to_json` + dump-to-file), and `build_recording_bundle` reuses them — guaranteeing bundle≡sidecar. The READ side adds `is_recording_bundle_path`/`read_recording_bundle`/`*_from_bundle`. The index/batch `_metadata_for`/`_sidecar_status` detect a bundle and extract from it.

**Tech Stack:** C++17, CMake, Catch2, nlohmann/json. Oracle: `src/ads1292_studio/recording_bundle.py`, `metadata.py`/`calibration.py`/`events.py`/`acquisition.py`/`protocol.py`/`quality_gate.py`/`processing.py` (the `asdict(normalized)` writers), `session_index.py` (`_metadata_for`/`_sidecar_status` bundle short-circuit), `batch.py`.

## Global Constraints

- **C++17**; preserve layering (io, no Qt). Branch `c++`; never touch `main`. `build/` gitignored. Reconfigure after adding files.
- **Build/test:** `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && QT_QPA_PLATFORM=offscreen ctest --test-dir build --output-on-failure`.
- **The 7 canonical types** (use THESE — delete Bundle.h's duplicates): `ads1292::SessionMetadata` (model), `std::vector<ads1292::EventMarker>` (model), `ads1292::Calibration` (model), `ads1292::io::AcquisitionProvenance` (AcquisitionIo.h — the 12-field canonical one), `ads1292::TestProtocol`/`ads1292::ProtocolStep` (model — start_seconds/duration_seconds/label/instruction), `ads1292::dsp::QualityGate`, `ads1292::RecordingProcessingSettings` (model).
- **Bundle payload ≡ individual sidecar JSON** (verified: Python `write_metadata_json` == bundle `"metadata"` value). Each `*_to_json` MUST be the EXACT json the P7b `write_*_json` already emits (so the writer refactor produces byte-identical sidecar files — the existing P7b sidecar tests must still pass unchanged).
- **Bundle top-level keys + ORDER** (Python build_recording_bundle): `schema, created_at, csv_name, metadata, events, calibration, acquisition, protocol, quality_gate, processing`. `schema="ads1292-recording-bundle-v1"`. `csv_name` = basename of the csv. Use `nlohmann::ordered_json`, `dump(2)+"\n"`.
- **events payload**: the bundle's `"events"` = the events-sidecar payload `_events_payload(normalized_events, sample_rate_hz)` (schema + entries with sample indices) — extract `events_to_json(const std::vector<EventMarker>&, double sample_rate_hz)` from the P7b events writer (it takes the rate). normalize each event first.
- **No behavior change to existing write_*_json output** — the refactor only extracts the json-building; the file bytes stay identical.

## File Structure

```
io/include/ads1292/io/{Metadata,Calibration,Events,Acquisition,Protocol,QualityGate,Processing}Io.h  # MODIFY: add *_to_json decl
io/src/{...}Io.cpp                                  # MODIFY: writer = *_to_json + dump
io/include/ads1292/io/Bundle.h                      # REWRITE: canonical types; build_recording_bundle + write_recording_bundle
io/src/Bundle.cpp                                   # REWRITE: reuse *_to_json
io/include/ads1292/io/RecordingBundle.h             # NEW: read side (is_recording_bundle_path, read_recording_bundle, *_from_bundle, recording_bundle_path)
io/src/RecordingBundle.cpp                          # NEW
io/src/SessionIndexScan.cpp + io/src/BatchScan.cpp  # MODIFY (Task 3): bundle detection in _metadata_for/_sidecar_status
tests/cpp/test_bundle_*.cpp                         # MODIFY: canonical types
tests/cpp/test_recording_bundle.cpp                 # NEW: read round-trip
tests/cpp/test_session_index*.cpp / test_batch*.cpp # MODIFY/ADD: bundle-backed recording
```

---

### Task 1: canonical bundle WRITE — extract *_to_json + rewrite Bundle

**Files:** Modify the 7 `io/src/*Io.cpp` + their headers (add `*_to_json`); rewrite `io/include/ads1292/io/Bundle.h` + `io/src/Bundle.cpp`; update `tests/cpp/test_bundle_sections.cpp`, `test_bundle_assembly.cpp`, `test_bundle_events.cpp`.

**Interfaces:**
- Produces in each `ads1292::io` sidecar module: `nlohmann::ordered_json metadata_to_json(const ads1292::SessionMetadata&);`, `calibration_to_json(const ads1292::Calibration&)`, `events_to_json(const std::vector<ads1292::EventMarker>&, double sample_rate_hz)`, `acquisition_to_json(const ads1292::io::AcquisitionProvenance&)`, `protocol_to_json(const ads1292::TestProtocol&)`, `quality_gate_to_json(const ads1292::dsp::QualityGate&)`, `processing_to_json(const ads1292::RecordingProcessingSettings&)`. Each writer `write_*_json` becomes `{ auto j = *_to_json(x); ofstream << j.dump(2) << "\n"; }` (byte-identical output).
- Produces in Bundle.h (namespace `ads1292::io`, canonical types only): `nlohmann::ordered_json build_recording_bundle(const std::string& csv_name, const ads1292::SessionMetadata& metadata, const std::vector<ads1292::EventMarker>& events, const ads1292::Calibration& calibration, const ads1292::io::AcquisitionProvenance& acquisition, const ads1292::TestProtocol& protocol, const ads1292::dsp::QualityGate& quality_gate, const ads1292::RecordingProcessingSettings& processing, double sample_rate_hz, const std::string& created_at);` + `std::string write_recording_bundle(const std::string& csv_path, <same args...>);` (writes to `csv` with `.json`, returns the path).

- [ ] **Step 1: Write/adjust failing tests.** Rewrite the 3 `test_bundle_*.cpp` to construct the CANONICAL types and assert the bundle JSON: top-level keys in order (schema/created_at/csv_name/metadata/events/calibration/acquisition/protocol/quality_gate/processing); `schema=="ads1292-recording-bundle-v1"`; `bundle["protocol"]["steps"][0]` has `start_seconds`/`duration_seconds`/`label`/`instruction` (NOT the old name/description — this is the bug fix); `bundle["acquisition"]` has the full 12 canonical fields (sample_rate_hz etc.); `bundle["metadata"] == metadata_to_json(metadata)` (bundle≡sidecar). Add a sidecar-equivalence assertion: the bundle's per-category object equals the corresponding `*_to_json`. (These fail on the current stub-type Bundle.)
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement.** (a) Extract `*_to_json` from each of the 7 writers; writer = to_json + dump. (b) Delete Bundle.h's local `SessionMetadata/QualityGate/RecordingProcessingSettings/ProtocolStep/TestProtocol/AcquisitionProvenance` + the per-category `*_payload` decls; rewrite build_recording_bundle to take canonical types and assemble `{schema, created_at, csv_name, metadata: metadata_to_json(metadata), events: events_to_json(events, rate), calibration: calibration_to_json(calibration), acquisition: acquisition_to_json(acquisition), protocol: protocol_to_json(protocol), quality_gate: quality_gate_to_json(quality_gate), processing: processing_to_json(processing)}` (ordered). Add write_recording_bundle. (c) Update the 3 test files.
- [ ] **Step 4: Build + ctest.** The EXISTING P7b sidecar tests (test_metadata_io etc.) must still pass byte-identical; the rewritten bundle tests pass.
- [ ] **Step 5: Commit** `git commit -m "fix: P10 canonical recording bundle write (eliminate duplicate io types + ODR, reuse sidecar serializers)"`

---

### Task 2: bundle READ side

**Files:** Create `io/include/ads1292/io/RecordingBundle.h` + `io/src/RecordingBundle.cpp`; add to io CMake; Create `tests/cpp/test_recording_bundle.cpp`; tests CMake.

**Interfaces (namespace `ads1292::io`):**
- `std::string recording_bundle_path(const std::string& csv_path);` — replace the csv extension with `.json` (match `with_suffix`).
- `bool is_recording_bundle_path(const std::string& path);` — read the json (if the file exists + parses), return `data.value("schema","") == "ads1292-recording-bundle-v1"`; false on missing/unparseable/wrong schema (match Python: catches read errors → false).
- `nlohmann::json read_recording_bundle(const std::string& path_or_csv);` — resolve to the bundle path (if given a csv, map to `.json`), parse, verify schema (throw if not a bundle), return the json.
- The 7 extractors (canonical types): `ads1292::SessionMetadata metadata_from_bundle(const nlohmann::json& bundle);`, `std::vector<ads1292::EventMarker> events_from_bundle(...)`, `ads1292::Calibration calibration_from_bundle(...)`, `ads1292::io::AcquisitionProvenance acquisition_from_bundle(...)`, `ads1292::TestProtocol protocol_from_bundle(...)`, `ads1292::dsp::QualityGate quality_gate_from_bundle(...)`, `ads1292::RecordingProcessingSettings processing_from_bundle(...)`. Each reads `bundle["<category>"]` and parses it into the canonical type — REUSE the P7b read parsers where they accept a json object, or factor a `*_from_json(const json&)` mirroring the existing `read_*_json` file parsers. (Match the Python `*_from_bundle` which read `bundle[key]` via the same mapping logic as the individual sidecar readers.)

- [ ] **Step 1: Write failing test** (`tests/cpp/test_recording_bundle.cpp`): build a bundle via Task 1's `build_recording_bundle` with known canonical values → write to a temp `rec.json` → `is_recording_bundle_path(temp/"rec.json")` true; a plain metadata sidecar (write_metadata_json) at another path → `is_recording_bundle_path` FALSE (schema mismatch). `read_recording_bundle` → `metadata_from_bundle` returns the known session_id/subject_id; `protocol_from_bundle` returns the steps with start_seconds/label; `events_from_bundle` returns the events; `acquisition_from_bundle` returns the port/sample_rate_hz; `quality_gate_from_bundle`/`processing_from_bundle`/`calibration_from_bundle` round-trip. If a committed Python golden bundle exists under tests/fixtures, also parse it; else rely on the C++ round-trip.
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** recording_bundle_path / is_recording_bundle_path / read_recording_bundle / the 7 *_from_bundle (reuse/factor the P7b json→type parsers). Match Python semantics (is_recording_bundle_path swallows read errors → false).
- [ ] **Step 4: Build + ctest.**
- [ ] **Step 5: Commit** `git commit -m "feat: P10 recording bundle read (is_recording_bundle_path, read_recording_bundle, *_from_bundle)"`

---

### Task 3: wire bundle detection into session-index + batch

**Files:** Modify `io/src/SessionIndexScan.cpp` (`_metadata_for`, `_sidecar_status`) + `io/src/BatchScan.cpp` (`_metadata_for`); Modify/add the relevant tests.

**Oracle facts (session_index.py):** `_metadata_for(csv)`: if `is_recording_bundle_path(recording_bundle_path(csv))` → `metadata_from_bundle(read_recording_bundle(...))`; else the individual `.json` metadata sidecar (current C++ behavior). `_sidecar_status(csv)`: if a valid bundle exists at the `.json` path → short-circuit to `("complete", "")` (the bundle carries all 7 categories); else the current per-sidecar audit. batch.py `_metadata_for` mirrors session_index.

- [ ] **Step 1: Write failing test.** Build a recording dir with `rec.csv` (a couple rows) + `rec.json` that is a recording BUNDLE (via Task 1 build_recording_bundle, with a distinctive `session_id="bundle-sess"` + `electrode="MOTAC"`). `scan_recording_directory(dir)` → the row for rec.csv has `session_id=="bundle-sess"`, `electrode=="MOTAC"` (from the bundle, NOT defaults) AND `sidecar_status=="complete"` / `missing_sidecars==""` (bundle short-circuit). Also assert `aggregate_recordings`/batch sees the bundle metadata. (Current code reads rec.json as a plain metadata sidecar → session_id would be the default + all 7 sidecars flagged missing → test fails before the fix.)
- [ ] **Step 2: Run, verify fail.**
- [ ] **Step 3: Implement** the bundle detection in both `_metadata_for` (SessionIndexScan + BatchScan) and `_sidecar_status` (SessionIndexScan): check `is_recording_bundle_path(recording_bundle_path(csv))`; if bundle → `metadata_from_bundle(read_recording_bundle(...))` + sidecar_status "complete"; else the existing path. Keep the non-bundle behavior unchanged.
- [ ] **Step 4: Build + ctest.** The existing non-bundle session-index/batch tests must still pass.
- [ ] **Step 5: Commit** `git commit -m "fix: P10 wire recording-bundle detection into session-index + batch (interop with Python recordings)"`

---

## Self-Review

**Coverage:** audit A.1 (Bundle stub types/ODR) → Task 1; A.2 (read not wired into consumers) → Tasks 2+3; A.3 (GUI write) → DEFERRED (separate decision). C10 (Bundle normalized) → subsumed by Task 1 (the *_to_json reuse the writers which already normalize). The bundle≡sidecar invariant is enforced by reusing *_to_json.

**Placeholder scan:** the bundle top-level key order, schema string, the 7 canonical types, the *_to_json extraction, the *_from_bundle extractors, and the index/batch short-circuit are all spelled out with oracle citations. Tests are concrete + are genuine discriminators (protocol steps with start_seconds; bundle metadata in the index).

**Type consistency:** Task 1 produces `build_recording_bundle`(canonical types) + the 7 `*_to_json`; Task 2 produces the read side + the 7 `*_from_bundle` (canonical types) reusing the P7b json parsers; Task 3 consumes `is_recording_bundle_path`/`recording_bundle_path`/`metadata_from_bundle`/`read_recording_bundle` from Task 2. All use the canonical model/sidecar types (no `ads1292::io` duplicates).

**Risk notes for the executor:**
- The `*_to_json` extraction must keep `write_*_json`'s file output BYTE-IDENTICAL (the existing P7b sidecar tests are the guard) — extract only, don't change keys/order/formatting.
- Deleting Bundle.h's duplicate types will break `test_bundle_*.cpp` + any other consumer — update them to canonical types (Step 1 of Task 1). Grep `io::SessionMetadata`/`io::TestProtocol`/`io::QualityGate`/`io::RecordingProcessingSettings` + the Bundle.h `AcquisitionProvenance` and fix every consumer. (The ODR clash with AcquisitionIo.h's AcquisitionProvenance is resolved by deleting Bundle.h's version.)
- `is_recording_bundle_path` must SWALLOW read/parse errors → return false (match Python `try/except → False`), so a non-bundle `.json` (plain metadata sidecar) or a missing file is correctly "not a bundle".
- Task 3 must NOT regress the non-bundle path — a recording with individual sidecars (no bundle) keeps the current per-sidecar audit + metadata read. Only add the bundle short-circuit.
- The events payload in the bundle uses the rate-dependent events sidecar payload — `events_to_json` takes `sample_rate_hz` (default the events DEFAULT_EVENT_SAMPLE_RATE_HZ — confirm the value from events.py).
