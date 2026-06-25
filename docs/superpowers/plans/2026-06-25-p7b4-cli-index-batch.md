# P7b-4: CLI index + batch Subcommands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the verified P7b-3 session_index + batch core into the Qt-free `ads1292_cli` as `index` (scan a directory → summary counters + a deterministic JSON index) and `batch` (aggregate recordings → rows + per-electrode group summaries) subcommands.

**Architecture:** Add `run_index`/`run_batch` (each `std::ostream& + options → int`) to the existing P7a `cli/Cli.{h,cpp}`, reusing P7b-3 `scan_recording_directory`/`summarize_rows`/`write_session_index_json` and `aggregate_recordings`/`group_recordings_by_electrode`; extend `main.cpp`'s dispatch. The C++ subcommands emit the DETERMINISTIC subset the C++ produces (summary counters + a JSON index for `index`; rows + group summaries for `batch`); the Python CLI's timestamped CSV/HTML/PNG + sidecar/manifest repair-script artifact lines are NOT emitted (that tooling is deferred). Parity is on the deterministic counters + exit codes.

**Tech Stack:** C++17, CMake, Catch2. Reuses P7b-3 `ads1292::io::scan_recording_directory`/`aggregate_recordings`/`write_session_index_json` + `ads1292::index::summarize_rows`/`group_recordings_by_electrode`, P2 `write_recording_csv` (tests). Oracle: `cli.py` (`cmd_index`, `cmd_batch`).

## Global Constraints

- **C++17**; the CLI stays Qt-free (links `ads1292_core` + `ads1292_io` only).
- **Layering**: `cli/` depends on `core` + `io`. No Qt.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Parity gates:** the index/batch output lines (the deterministic counters the C++ produces) + exit codes, exercised on in-test constructed recording dirs. The underlying scan/aggregate/summarize/group logic is already P7b-3-verified.
- **`run_index` (subset of `cmd_index`, cli.py L181):** if root is not a directory → print `index expects a directory; '<root>' is not a directory` (then proceed with an empty scan). Else if `discover_recording_csvs(root)` is empty → print `no recording CSVs found under <root>` (then proceed). Always: `rows = scan_recording_directory(root)`; `summary = summarize_rows(rows)`; write the JSON index via `write_session_index_json(<out>/index.json, rows, summary)`; print (in this order): `index_json=<path>`, `rows=<rows.size()>`, `package_ready=<summary.package_ready>`, `incomplete_records=<summary.incomplete_records>`, `needs_signal_review=<summary.needs_signal_review>`, `action_package_record=<summary.action_package_record>`, `action_complete_sidecars=<summary.action_complete_sidecars>`, `action_review_signal=<summary.action_review_signal>`. Return `0`. (The Python `csv=/html=/sidecar_plan_*/manifest_*/template` lines are NOT emitted — that tooling is deferred; document this.)
- **`run_batch` (subset of `cmd_batch`, cli.py L167):** resolve inputs — each input path that is a directory expands to its recording CSVs (via `discover_recording_csvs`), each file passes through (mirror `_resolve_batch_inputs`); if no CSVs → print `no recording CSVs found in the given path(s)` (then proceed). `rows = aggregate_recordings(paths)`; `groups = group_recordings_by_electrode(rows)`; print `rows=<rows.size()>`, `groups=<groups.size()>`, then one line per group: `group=<electrode>\trecordings=<n>\tusable_percent=<:.2f>\tmean_hr_median_bpm=<:.2f>`. Return `0`. (The Python `csv=/group_csv=/html=/png=` lines are NOT emitted — rendering deferred.)

## File Structure

```
cli/include/ads1292/cli/Cli.h   # MODIFY: add IndexOptions/run_index, BatchOptions/run_batch
cli/src/Cli.cpp                 # MODIFY: implement run_index, run_batch
cli/src/main.cpp                # MODIFY: dispatch index, batch
tests/cpp/test_cli.cpp          # MODIFY: index + batch integration cases
```

---

### Task 1: `index` subcommand

**Files:** Modify `cli/include/ads1292/cli/Cli.h`, `cli/src/Cli.cpp`, `cli/src/main.cpp`; Modify `tests/cpp/test_cli.cpp`.

**Interfaces:**
- Consumes: P7b-3 `ads1292::io::discover_recording_csvs`/`scan_recording_directory`/`write_session_index_json`, `ads1292::index::summarize_rows`.
- Produces: `ads1292::cli::struct IndexOptions { std::string root; std::string out_dir; };` and `int run_index(std::ostream& out, const IndexOptions& opt);`.

- [ ] **Step 1: Write the failing index test** — construct a recording dir, run_index, check counters + exit.

```cpp
// add to tests/cpp/test_cli.cpp (reuse the existing write_clean helper / includes)
#include "ads1292/io/CsvIo.h"
#include "ads1292/io/MetadataIo.h"
#include <filesystem>
TEST_CASE("run_index scans a directory and prints summary counters", "[cli]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b4_index";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  // one clean recording, no sidecars -> incomplete_record / complete_sidecars
  ads1292::cli::write_clean_recording((dir / "rec1.csv").string());   // a clean ~10s 72bpm recording (reuse the test helper pattern)
  ads1292::cli::IndexOptions opt; opt.root = dir.string(); opt.out_dir = (dir / "out").string();
  std::ostringstream o;
  int code = ads1292::cli::run_index(o, opt);
  REQUIRE(code == 0);
  REQUIRE(o.str().find("rows=1") != std::string::npos);
  REQUIRE(o.str().find("index_json=") != std::string::npos);
  REQUIRE(o.str().find("incomplete_records=1") != std::string::npos);   // no sidecars
  REQUIRE(o.str().find("action_complete_sidecars=1") != std::string::npos);
  REQUIRE(std::filesystem::exists(std::filesystem::path(opt.out_dir) / "index.json"));
}
TEST_CASE("run_index on a non-directory prints the diagnostic", "[cli]") {
  ads1292::cli::IndexOptions opt; opt.root = (std::filesystem::temp_directory_path()/"p7b4_nope_xyz").string(); opt.out_dir = (std::filesystem::temp_directory_path()/"p7b4_o2").string();
  std::ostringstream o;
  REQUIRE(ads1292::cli::run_index(o, opt) == 0);
  REQUIRE(o.str().find("is not a directory") != std::string::npos);
  REQUIRE(o.str().find("rows=0") != std::string::npos);
}
```
(If there is no shared `write_clean_recording` helper, add a small file-local one in the test that writes a ~5000-sample Gaussian-R-peak 72bpm recording via `ads1292::io::write_recording_csv`, like the P7b-3 tests.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `IndexOptions` + `run_index` per the Global Constraints (directory/empty diagnostics, scan + summarize + write JSON to `<out_dir>/index.json`, print the 8 lines, return 0). Add `index <root> [--out <dir>]` dispatch to `main.cpp` (default `--out` to e.g. `<root>/index-out` or the cwd; choose a sensible default + document). `create_directories(out_dir)` before writing.

- [ ] **Step 4: Build, run.** Expected PASS.

- [ ] **Step 5: Commit** `git commit -m "feat: P7b CLI index subcommand (scan dir -> summary + json index)"`

---

### Task 2: `batch` subcommand

**Files:** Modify `cli/include/ads1292/cli/Cli.h`, `cli/src/Cli.cpp`, `cli/src/main.cpp`; Modify `tests/cpp/test_cli.cpp`.

**Interfaces:**
- Consumes: P7b-3 `ads1292::io::aggregate_recordings`/`discover_recording_csvs`, `ads1292::index::group_recordings_by_electrode`.
- Produces: `ads1292::cli::struct BatchOptions { std::vector<std::string> inputs; };` and `int run_batch(std::ostream& out, const BatchOptions& opt);`.

- [ ] **Step 1: Write the failing batch test**

```cpp
TEST_CASE("run_batch aggregates recordings and groups by electrode", "[cli]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b4_batch";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  std::vector<std::string> inputs;
  for (auto stem : {"a","b"}) {
    auto csv = (dir / (std::string(stem)+".csv")).string();
    ads1292::cli::write_clean_recording(csv);
    ads1292::SessionMetadata m; m.electrode="MOTAC"; ads1292::io::write_metadata_json((dir/(std::string(stem)+".json")).string(), m);
    inputs.push_back(csv);
  }
  ads1292::cli::BatchOptions opt; opt.inputs = inputs;
  std::ostringstream o;
  int code = ads1292::cli::run_batch(o, opt);
  REQUIRE(code == 0);
  REQUIRE(o.str().find("rows=2") != std::string::npos);
  REQUIRE(o.str().find("groups=1") != std::string::npos);
  REQUIRE(o.str().find("group=MOTAC") != std::string::npos);
}
TEST_CASE("run_batch on a directory input expands to its CSVs", "[cli]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b4_batch_dir";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  ads1292::cli::write_clean_recording((dir/"x.csv").string());
  ads1292::cli::BatchOptions opt; opt.inputs = { dir.string() };   // directory input
  std::ostringstream o;
  REQUIRE(ads1292::cli::run_batch(o, opt) == 0);
  REQUIRE(o.str().find("rows=1") != std::string::npos);
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `BatchOptions` + `run_batch` per the Global Constraints (resolve inputs: directory→`discover_recording_csvs`, file→passthrough; empty→diagnostic; aggregate + group; print rows/groups + per-group lines; return 0). Add `batch <csv-or-dir>...` dispatch to `main.cpp` (variadic positional inputs).

- [ ] **Step 4: Build, run.** Expected PASS.

- [ ] **Step 5: Commit** `git commit -m "feat: P7b CLI batch subcommand (aggregate + group-by-electrode)"`

---

## Self-Review

**1. Spec coverage:** `index` subcommand (scan + summary + json) → Task 1 ✓; `batch` subcommand (aggregate + group) → Task 2 ✓. The Python CSV/HTML/PNG/sidecar-plan/manifest artifact output lines are intentionally NOT emitted (deferred rendering/repair tooling) — documented.

**2. Placeholder scan:** the output line sets + exit codes + the directory/empty diagnostics are concrete; the test bodies are concrete. The heavy scan/aggregate/summarize/group logic is reused from P7b-3 (already verified). Parity is on the deterministic counter lines.

**3. Type consistency:** `IndexOptions`/`run_index` (Task 1) + `BatchOptions`/`run_batch` (Task 2) added to the existing `cli/Cli.h` alongside `QcOptions`/`ReportOptions`/`VerifyOptions`. Reuses P7b-3 `scan_recording_directory`/`summarize_rows`/`write_session_index_json`/`aggregate_recordings`/`group_recordings_by_electrode`. `main.cpp` dispatch extends the existing qc/report/verify switch.

**Risk notes for the executor:**
- The CLI stays Qt-FREE (only core+io). Do not pull in Qt.
- Emit ONLY the deterministic lines the C++ produces; do NOT fabricate the deferred `csv=/html=/png=/sidecar_plan_*/manifest_*` lines (they'd be lying about artifacts that aren't generated).
- `run_index`/`run_batch` take `std::ostream&` (testable), like the P7a subcommands.
- `index` writes its JSON to `<out_dir>/index.json` (create the dir); pick a sensible `--out` default in main.cpp.
- `batch` input resolution: a directory argument expands to its recording CSVs (mirror `_resolve_batch_inputs`); a file passes through.
- Reuse the existing `write_clean`-style helper in test_cli.cpp (or add one) for synthetic recordings; share it across the index/batch cases.
