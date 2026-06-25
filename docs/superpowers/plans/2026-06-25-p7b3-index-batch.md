# P7b-3: Session Index + Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the core recording-catalog logic — `session_index` (scan a directory of recordings → per-recording index rows + a directory summary) and `batch` (aggregate recordings → rows + per-electrode group summaries) — reusing the verified quality metrics + sidecar readers, verified by constructing recording directories in-test and asserting the row/summary fields against the Python oracle's logic.

**Architecture:** New portable `core/index` (pure C++17 logic) + `io/`-level scan functions (filesystem + sidecar reads). `scan_recording_directory` builds a `SessionIndexRow` per CSV (composing `read_recording_csv` + `compute_quality_metrics` + the sidecar readers + sidecar-presence/event/completion/status derivation); `summarize_rows` counts. `batch` aggregates a list of recordings into `BatchRow`s + `BatchGroupSummary`s. The DETERMINISTIC core (rows + summary, plus a JSON export of them) is in scope; the timestamped CSV/HTML report artifacts, the sidecar/manifest repair-script generators, and `verify_recording_manifest` (manifest module not ported) are DEFERRED. Parity is **semantic**: tests construct dirs via the committed C++ io writers + assert specific row fields + summary counters against the oracle's derivation rules (spelled out below); the underlying quality metrics + sidecars are already golden-verified.

**Tech Stack:** C++17, CMake, Catch2 + nlohmann/json + std::filesystem. Reuses P2 `read_recording_csv`/`write_recording_csv`, P5c `compute_quality_metrics`/`quality_label`, P7b-1/2 sidecar readers (`read_metadata_json`/`read_events_json`/`read_acquisition_json`). Oracle: `session_index.py`, `batch.py`.

## Global Constraints

- **C++17**; the row/summary structs + derivation are pure portable C++; the scan/read functions use `std::filesystem` + nlohmann/json (io layer). No Qt.
- **Layering**: depends on P2 (CSV read) + P5c (quality) + P7b sidecar readers. No Qt.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Parity gates:** SEMANTIC — construct recording directories in-test (write CSVs + sidecars via the committed C++ io writers), `scan_recording_directory` → assert specific `SessionIndexRow` fields + `summarize_rows` counters against the oracle's derivation; `aggregate_recordings`/`group_recordings_by_electrode` similarly. The quality metrics / sidecar reads they compose are ALREADY golden-verified (P5c/P7b).
- **DEFERRED (out of scope, later slice):** the timestamped CSV/HTML exports (`_write_csv`, `_html`, `_sidecar_plan_html`, etc.), the repair-script generators (`write_sidecar_apply_script`, `build_sidecar_completion_plan`, `write_recording_manifest_apply_script`, `build_recording_manifest_repair_plan`, `write_sidecar_template_bundle`), `export_batch_summary`'s PNG/HTML. The `_recording_manifest_audit` degrades to `("missing","")` when no `<csv>.manifest.json` exists (the common case); the actual `verify_recording_manifest` is NOT ported (manifest module → packaging slice) — when a `.manifest.json` IS present, return `("unknown","manifest verification not available")` rather than crashing.
- **`SessionIndexRow`** (34 fields — read the exact list from session_index.py L38-72): `path`, `relative_path`, `session_id`, `subject_id`, `electrode`, `montage`, `operator_` (C++ keyword → `operator_`), `sample_count`, `duration_seconds`, `completion_status`, `recorded_sample_count`, `recorded_span_seconds`, `completion_audit`, `recorded_sample_count_delta`, `recorded_span_delta_seconds`, `ecg_source`, `contact_ok_percent`, `r_peaks`, `hr_median_bpm`, `qrs_clear`, `quality_label`, `status`, `sidecar_status`, `missing_sidecars`, `event_count`, `interval_event_count`, `total_annotated_seconds`, `total_annotated_samples`, `event_labels`, `recording_manifest_status`, `recording_manifest_failures`, `package_ready_status`, `next_action`.
- **`_row_for_csv(path, root)`** (session_index.py L366): `read_recording_csv(path)` (skip on error/empty → null row, filtered out); `metadata = read_metadata_json(<csv>.json)` if present else `SessionMetadata{session_id=<stem>}.normalized()` (read `_metadata_for`); `metrics = compute_quality_metrics(samples, sr)`; `(sidecar_status, missing) = _sidecar_status(path)`; `event_summary = _event_summary_for(path, sr)`; `completion = _completion_summary_for(path)`; `(audit, count_delta, span_delta) = _completion_audit(completion, metrics.sample_count, metrics.duration_seconds)`; `(manifest_status, manifest_failures) = _recording_manifest_audit(path)` (degraded as above); `status = _status_for_quality(metrics.quality_label)`; `package_ready_status = _package_ready_status(status, sidecar_status)`; `next_action = _next_action(package_ready_status)`. Fill all 34 fields.
- **Derivation rules (session_index.py, EXACT):**
  - `_status_for_quality(q)`: `q in {"Good ECG/QRS","Usable ECG/QRS"} ? "usable" : "review"`.
  - `_package_ready_status(waveform, sidecar)`: `sidecar!="complete" → "incomplete_record"; waveform!="usable" → "needs_signal_review"; else "package_ready"`.
  - `_next_action(pkg)`: `"package_ready"→"package_record"; "needs_signal_review"→"review_signal"; else "complete_sidecars"`.
  - `_sidecar_status(csv)`: if a recording bundle exists at the bundle path → `("complete","")`; else check each expected sidecar exists (metadata `<csv>.json`; events `<csv>.events.json` OR `.events.csv`; calibration `.calibration.json`; acquisition `.acquisition.json`; protocol `.protocol.json`; quality_gate `.quality-gate.json`; processing `.processing.json`); `missing` = the names lacking any file; `("complete","") if none missing else ("missing", join(missing,";"))`. (Read `_sidecar_status` + `is_recording_bundle_path`/`recording_bundle_path` — if bundle detection isn't ported, treat "no bundle" and just do the sidecar-existence checks.)
  - `_event_summary_for(csv, sr)`: read events sidecar (`.events.json` if present, else empty) → `EventAnnotationSummary{count, interval_count, total_annotated_seconds, total_annotated_samples, labels}` (read `_summarize_events`: count=len; interval_count=#(duration>0); total_annotated_seconds=round(sum(durations),6); total_annotated_samples=sum(round(duration*sr)); labels=unique labels joined). Read the exact `_summarize_events`.
  - `_completion_summary_for(csv)`: read acquisition sidecar's `completion` block → `AcquisitionCompletionSummary{status, sample_count, span_seconds}` (status from completion["status"] default "unknown"; sample_count/span from completion fields). Read `_completion_summary_for` + `AcquisitionCompletionSummary`.
  - `_completion_audit(completion, actual_count, actual_span)`: read session_index.py L497 — returns `(audit, count_delta, span_delta)`; audit ∈ {"pass","fail","pending","unknown"} based on whether completion is finalized + deltas within tolerance. Replicate exactly.
- **`summarize_rows(rows)`** → `SessionIndexSummary` (24 counters, session_index.py L323 — all spelled out: recordings, usable_recordings (status=="usable"), package_ready/incomplete_records/needs_signal_review (package_ready_status), finalized/open/unknown_completion (completion_status), completion_audit_pass/fail/pending/unknown, recording_manifest_pass/fail/missing/unknown, annotated_recordings (event_count>0), event_annotations (sum event_count), interval_event_annotations (sum interval), total_annotated_seconds (round(sum,6)), total_annotated_samples (sum), action_package_record/complete_sidecars/review_signal (next_action)).
- **`BatchRow`** (batch.py L29 — 12 fields): relative path/name, session_id, subject_id, electrode, montage, sample_count, duration_seconds, ecg_source, contact_ok_percent, r_peaks, hr_median_bpm, quality_label (read the exact list). **`aggregate_recordings(paths)`**: per path read CSV + metadata + compute_quality_metrics → BatchRow (skip unreadable). **`BatchGroupSummary`** (8 fields): electrode, recordings, usable_recordings, usable_percent, mean_duration_seconds, mean_contact_ok_percent, mean_r_peaks, mean_hr_median_bpm. **`group_recordings_by_electrode(rows)`**: group by electrode, compute the means + usable% (read batch.py L102 for the exact grouping + mean math + ordering).

## File Structure

```
core/include/ads1292/index/SessionIndexRow.h    # SessionIndexRow + SessionIndexSummary + derivation (pure)
core/src/index/SessionIndexRow.cpp
io/include/ads1292/io/SessionIndexScan.h         # discover/scan/summarize/export-json
io/src/SessionIndexScan.cpp
core/include/ads1292/index/BatchRow.h            # BatchRow + BatchGroupSummary (pure)
core/src/index/BatchRow.cpp
io/include/ads1292/io/BatchScan.h                # aggregate/group
io/src/BatchScan.cpp
tests/cpp/test_session_index.cpp
tests/cpp/test_batch.cpp
```

---

### Task 1: session_index (scan + rows + summarize)

**Files:** Create `core/.../index/SessionIndexRow.{h,cpp}`, `io/.../SessionIndexScan.{h,cpp}`; Modify core/io CMake; Create `tests/cpp/test_session_index.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: `read_recording_csv` (P2), `compute_quality_metrics`/`quality_label` (P5c), `read_metadata_json`/`read_events_json`/`read_acquisition_json` (P7b).
- Produces: `ads1292::index::SessionIndexRow {...34 fields...}`, `ads1292::index::SessionIndexSummary {...24 fields...}`, `SessionIndexSummary summarize_rows(const std::vector<SessionIndexRow>&)` (pure, core); `ads1292::io::std::vector<std::string> discover_recording_csvs(const std::string& root)` (sorted), `std::vector<ads1292::index::SessionIndexRow> scan_recording_directory(const std::string& root)`, and `void write_session_index_json(const std::string& path, const std::vector<SessionIndexRow>& rows, const SessionIndexSummary& summary)` (deterministic JSON export of rows+summary — NOT the timestamped CSV/HTML).

- [ ] **Step 1: Write the failing test** — construct a recording dir via the committed C++ io, scan, assert row fields + summary counters.

```cpp
// tests/cpp/test_session_index.cpp
#include "catch.hpp"
#include "ads1292/io/SessionIndexScan.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/MetadataIo.h"
#include "ads1292/model/StreamSample.h"
#include <filesystem>
#include <cmath>
using namespace ads1292;
namespace {
std::string make_clean_recording(const std::filesystem::path& dir, const std::string& stem) {
  std::vector<StreamSample> rec;
  for (int i=0;i<5000;++i){ StreamSample s; double t=i/500.0, v=0.0;
    for(double bt=0.2; bt<10.0; bt+=60.0/72.0){ double d=t-bt; v+=300.0*std::exp(-(d*d)/(2*0.01*0.01)); }
    s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s); }
  auto p = (dir / (stem + ".csv")).string();
  io::write_recording_csv(p, rec); return p;
}
}
TEST_CASE("scan_recording_directory builds rows + summary", "[index]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b3_idx";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  auto csv = make_clean_recording(dir, "rec1");
  // give rec1 a metadata sidecar so some sidecar status is exercised
  SessionMetadata m; m.session_id="run-1"; m.subject_id="subj-A"; io::write_metadata_json((dir/"rec1.json").string(), m);
  auto rows = io::scan_recording_directory(dir.string());
  REQUIRE(rows.size() == 1);
  REQUIRE(rows[0].relative_path == "rec1.csv");
  REQUIRE(rows[0].session_id == "run-1");
  REQUIRE(rows[0].r_peaks >= 5);
  REQUIRE(rows[0].quality_label.size() > 0);
  // sidecar_status: only metadata present -> missing the others
  REQUIRE(rows[0].sidecar_status == "missing");
  REQUIRE(rows[0].missing_sidecars.find("calibration") != std::string::npos);
  // manifest absent -> "missing"
  REQUIRE(rows[0].recording_manifest_status == "missing");
  auto sum = index::summarize_rows(rows);
  REQUIRE(sum.recordings == 1);
  REQUIRE(sum.recording_manifest_missing == 1);
  // export json round-trips structurally (no crash, file written)
  auto out = (dir / "index.json").string();
  io::write_session_index_json(out, rows, sum);
  REQUIRE(std::filesystem::exists(out));
}
```

- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement** per Global Constraints — READ `session_index.py` for the exact `_row_for_csv`, `_sidecar_status`, `_event_summary_for`/`_summarize_events`, `_completion_summary_for`, `_completion_audit`, `_status_for_quality`/`_package_ready_status`/`_next_action`, `summarize_rows`, and the `EventAnnotationSummary`/`AcquisitionCompletionSummary` shapes. Degrade `_recording_manifest_audit` (missing manifest → "missing"; present → "unknown"+message, no crash). `discover_recording_csvs` = sorted `*.csv` under root that look like recordings (read `_looks_like_recording_csv`/`discover_recording_csvs`). The JSON export is a deterministic `{rows:[...], summary:{...}}` via ordered_json.
- [ ] **Step 4: Wire CMake, build, run.** Iterate until the row fields + summary counters match.
- [ ] **Step 5: Commit** `git commit -m "feat: P7b session_index core (scan + rows + summarize + json export)"`

---

### Task 2: batch (aggregate + group)

**Files:** Create `core/.../index/BatchRow.{h,cpp}`, `io/.../BatchScan.{h,cpp}`; Modify core/io CMake; Create `tests/cpp/test_batch.cpp`; Modify tests CMake.

**Interfaces:**
- Produces: `ads1292::index::BatchRow {...12 fields...}`, `ads1292::index::BatchGroupSummary {...8 fields...}`, `std::vector<BatchGroupSummary> group_recordings_by_electrode(const std::vector<BatchRow>&)` (pure, core); `ads1292::io::std::vector<ads1292::index::BatchRow> aggregate_recordings(const std::vector<std::string>& csv_paths)`.

- [ ] **Step 1: Write the failing test**

```cpp
// tests/cpp/test_batch.cpp
#include "catch.hpp"
#include "ads1292/io/BatchScan.h"
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/MetadataIo.h"
#include <filesystem>
#include <cmath>
using namespace ads1292;
// (reuse a clean-recording writer like Task 1)
TEST_CASE("aggregate_recordings + group_by_electrode", "[batch]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b3_batch";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  // two recordings, same electrode via metadata
  std::vector<std::string> paths;
  for (auto stem : {"a","b"}) {
    std::vector<StreamSample> rec;
    for (int i=0;i<5000;++i){ StreamSample s; double t=i/500.0,v=0.0; for(double bt=0.2;bt<10.0;bt+=60.0/72.0){double d=t-bt; v+=300.0*std::exp(-(d*d)/(2*0.01*0.01));} s.ch2=(int)v; s.ch1=0; s.status_byte=0; rec.push_back(s);}
    auto p=(dir/(std::string(stem)+".csv")).string(); io::write_recording_csv(p, rec);
    SessionMetadata m; m.electrode="MOTAC"; io::write_metadata_json((dir/(std::string(stem)+".json")).string(), m);
    paths.push_back(p);
  }
  auto rows = io::aggregate_recordings(paths);
  REQUIRE(rows.size() == 2);
  REQUIRE(rows[0].electrode == "MOTAC");
  auto groups = index::group_recordings_by_electrode(rows);
  REQUIRE(groups.size() == 1);
  REQUIRE(groups[0].electrode == "MOTAC");
  REQUIRE(groups[0].recordings == 2);
  REQUIRE(groups[0].mean_r_peaks > 0.0);
}
```

- [ ] **Step 2: Run to verify it fails.**
- [ ] **Step 3: Implement** per Global Constraints — READ `batch.py` for the exact `BatchRow`/`BatchGroupSummary` fields, `aggregate_recordings` (per-path read+metadata+metrics→row, skip unreadable), `group_recordings_by_electrode` (grouping + mean math + usable% + ordering). Reuse P5c metrics + P7b metadata.
- [ ] **Step 4: Wire CMake, build, run.**
- [ ] **Step 5: Commit** `git commit -m "feat: P7b batch aggregate + group-by-electrode"`

---

## Self-Review

**1. Spec coverage:** session_index core (scan+rows+summarize+json) → Task 1 ✓; batch (aggregate+group) → Task 2 ✓. Repair-script tooling / CSV-HTML rendering / `verify_recording_manifest` / `export_batch_summary` PNG-HTML → DEFERRED (documented).

**2. Placeholder scan:** the row/summary/batch struct shapes + the derivation rules (status/package-ready/next-action/summarize counters) are spelled out; the per-CSV helper bodies (`_completion_audit`, `_summarize_events`, `_completion_summary_for`, `_sidecar_status`, `discover_recording_csvs`) are referenced to the oracle for exact replication (the executor reads session_index.py/batch.py). Tests construct dirs via the committed C++ io + assert real fields/counters. Parity is semantic.

**3. Type consistency:** `SessionIndexRow`/`SessionIndexSummary` (Task 1) + `BatchRow`/`BatchGroupSummary` (Task 2) independent. Both reuse `compute_quality_metrics`/`quality_label` (P5c) + `read_metadata_json` (P7b-1) + (Task 1) `read_events_json`/`read_acquisition_json` (P7b). `operator`→`operator_`.

**Risk notes for the executor:**
- Parity is SEMANTIC (constructed-dir scan + asserted fields/counters), per the established sidecar approach. The composed quality/sidecar reads are already golden-verified; this slice tests the COMPOSITION + counter logic.
- `_recording_manifest_audit` degrades: no `.manifest.json` → `("missing","")`; present → `("unknown","manifest verification not available")` (the manifest module is a later/packaging slice — do NOT block on it).
- READ `session_index.py` + `batch.py` for the exact helper bodies — the derivation rules above are the spec, but `_completion_audit`/`_summarize_events`/`_completion_summary_for`/`group_recordings_by_electrode` mean-math must match the oracle exactly.
- `operator` is a C++ keyword → `operator_` field (mapped to/from the metadata `operator`).
- DEFER the repair-script generators + CSV/HTML/PNG exports; only the deterministic rows+summary (+ a JSON export) are in scope.
- Keep the row/summary/batch structs pure (no Qt); scan/aggregate use std::filesystem + the io readers.
