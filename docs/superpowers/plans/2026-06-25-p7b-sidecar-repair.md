# P7b: Sidecar Repair Tooling (completion plan + template bundle + apply script) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the recording-recovery tooling — a sidecar completion plan (which sidecars are missing + where templates go), a template bundle (write template sidecars for the missing ones), and an apply script (a `cp -n` shell script to install them) — wired into the `ads1292_cli index` command, reusing the verified P7b-1/2 sidecar templates + P7b-3 scan rows.

**Architecture:** `build_sidecar_completion_plan(rows, template_dir)` (pure logic over the scan rows' `missing_sidecars`) → `SidecarPlanRow[]`. `write_sidecar_template_bundle(template_dir, rows)` writes a template sidecar per missing slot via the existing `write_*_json`/`*_template` (adding a small `write_quality_gate_json` for the quality-gate slot, and a simplified default acquisition template). `write_sidecar_apply_script(path, plan)` emits the `#!/bin/sh` + `mkdir -p`/`cp -n` script. The `index` CLI command emits the plan + templates + apply script. The recording-MANIFEST repair tooling (`build_recording_manifest_repair_plan`/`write_recording_manifest_apply_script`) is DEFERRED (the manifest module isn't ported). Parity: plan rows + the apply-script content + the written template sidecars (which round-trip via the P7b readers).

**Tech Stack:** C++17, CMake, Catch2. Reuses P7b-3 `SessionIndexRow`/`scan_recording_directory`, P7b-1/2 `write_metadata_json`/`write_events_json`+`event_template`/`write_calibration_json`+`calibration_template`/`write_protocol_json`+`protocol_template`/`write_processing_json`+`build_processing_settings`/`write_acquisition_json`+`AcquisitionProvenance`, P7a `QualityGate`. Oracle: `session_index.py` (`SidecarPlanRow`/`build_sidecar_completion_plan`/`write_sidecar_template_bundle`/`write_sidecar_apply_script`/`_expected_sidecar_path`/`_sidecar_label`/`_template_path_for`/`_write_sidecar_template`), `quality_gate.py` (`write_quality_gate_json`/`quality_gate_template`).

## Global Constraints

- **C++17**; the plan + helpers are pure portable C++; the template-bundle + apply-script writing use the io layer (filesystem + the sidecar writers). No Qt.
- **Layering**: in `io/` (alongside SessionIndexScan), reusing the P7b sidecar writers + P7b-3 rows. No Qt.
- **Branch**: work on `c++`; do NOT touch `main`. `build/` is gitignored.
- **Build/test**: `CMAKE_PREFIX_PATH="/opt/homebrew/opt/qt;/opt/homebrew/opt/hdf5" cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug && cmake --build build -j && ctest --test-dir build --output-on-failure`.
- **Parity gates:** plan rows (relative_path/sidecar/target_path/template_path/suggested_action) + the apply-script content (#!/bin/sh + set -eu + per-row mkdir/cp -n) + the written template sidecars (parse-back via the P7b readers). The manifest repair → DEFERRED (documented).
- **`SidecarPlanRow` (session_index.py):** `std::string relative_path; std::string sidecar; std::string target_path; std::string template_path; std::string suggested_action;` (Path→string).
- **`_expected_sidecar_path(csv_path, sidecar)`:** metadata→`<csv>.json` (replace `.csv` suffix); events→`.events.json`; calibration→`.calibration.json`; acquisition→`.acquisition.json`; protocol→`.protocol.json`; quality_gate→`.quality-gate.json`; processing→`.processing.json`; else `.<sidecar>.json`. (Suffix replacement: strip a trailing `.csv` and append the new suffix.)
- **`_sidecar_label(sidecar)`:** `sidecar` with `'_'`→`' '` (e.g. `quality_gate`→`quality gate`).
- **`_template_path_for(template_dir, row, sidecar)`:** `target_name = basename(_expected_sidecar_path(row.path, sidecar))`; `parent = parent_dir(row.relative_path)`; if parent is `"."`/empty → `template_dir/target_name` else `template_dir/parent/target_name`.
- **`build_sidecar_completion_plan(rows, template_dir)`:** for each `row`, for each `sidecar` in `split(row.missing_sidecars, ';')` (skip empty): `SidecarPlanRow{ row.relative_path, sidecar, _expected_sidecar_path(row.path, sidecar), _template_path_for(template_dir, row, sidecar), "Create " + _sidecar_label(sidecar) + " sidecar" }`.
- **`_write_sidecar_template(path, row, sidecar)`:** metadata → `write_metadata_json(path, SessionMetadata{session_id=row.session_id, subject_id=row.subject_id, electrode=row.electrode, montage=row.montage, operator_=row.operator_, notes="Review and complete this generated metadata sidecar before packaging."})`; events → `write_events_json(path, event_template())`; calibration → `write_calibration_json(path, calibration_template())`; acquisition → `write_acquisition_json(path, <simplified template>)` (use `AcquisitionProvenance a; a.csv_name=basename(row.path); a.port="review-required"; a.started_at="review-required"; write a.normalized();` — a SIMPLIFIED default standing in for the Python `build_acquisition_provenance(...)`, since the elaborate builder with calibration/live_calibration args isn't ported; document the simplification); protocol → `write_protocol_json(path, protocol_template())`; quality_gate → `write_quality_gate_json(path, QualityGate{})` (the new writer — Task 2); processing → `write_processing_json(path, build_processing_settings())`.
- **`write_sidecar_template_bundle(template_dir, rows)`:** for each row, for each non-empty sidecar in `split(missing_sidecars, ';')`: `path = _template_path_for(template_dir, row, sidecar)`; `create_directories(path.parent)`; `_write_sidecar_template(path, row, sidecar)`; collect. Return the written paths.
- **`write_sidecar_apply_script(path, plan_rows)` (session_index.py):** lines: `#!/bin/sh`, `set -eu`, ``, `# Generated by ADS1292 Studio.`, `# Review generated sidecar templates before running this script.`, `# Existing target sidecars are left untouched by cp -n.`, ``; if `plan_rows.empty()` → append `echo 'No missing sidecars to apply.'`; for each row: `# <relative_path>: <sidecar>`, `mkdir -p <shell-quote(parent of target_path resolved)>`, `cp -n <shell-quote(template_path resolved)> <shell-quote(target_path resolved)>`, ``. Write `join(lines, "\n") + "\n"`; `chmod 0755`. (shell-quote = POSIX single-quote escaping, matching Python `shlex.quote`.)
- **`write_quality_gate_json(path, gate)` + `quality_gate_template()` (quality_gate.py):** `quality_gate_template()` = `QualityGate{}` (defaults). `write_quality_gate_json` = write `asdict(gate.normalized())` as JSON: keys `min_duration_seconds, min_contact_ok_percent, min_r_peaks, min_hr_bpm, max_hr_bpm, require_qrs_clear, max_baseline_drift_counts, max_noise_rms_counts, max_peak_to_peak_counts` (the 3 optionals → `null` when unset). ordered_json, dump(2)+"\n".

## File Structure

```
io/include/ads1292/io/QualityGateIo.h     # write_quality_gate_json + quality_gate_template (Task 1, needed by Task 2 bundle)
io/src/QualityGateIo.cpp
io/include/ads1292/io/SidecarRepair.h      # SidecarPlanRow, build_sidecar_completion_plan, write_sidecar_template_bundle, write_sidecar_apply_script
io/src/SidecarRepair.cpp
cli/src/Cli.cpp                            # MODIFY (Task 2): run_index emits the plan + templates + apply script
tests/cpp/test_sidecar_repair.cpp
```

---

### Task 1: sidecar completion plan + quality_gate JSON

**Files:** Create `io/include/ads1292/io/SidecarRepair.h` + `io/src/SidecarRepair.cpp` (SidecarPlanRow + build_sidecar_completion_plan + the path helpers); Create `io/include/ads1292/io/QualityGateIo.h` + `io/src/QualityGateIo.cpp` (write_quality_gate_json + quality_gate_template); Modify io CMake; Create `tests/cpp/test_sidecar_repair.cpp`; Modify tests CMake.

**Interfaces:**
- Consumes: P7b-3 `ads1292::index::SessionIndexRow`, P7a `ads1292::dsp::QualityGate`.
- Produces (namespace `ads1292::io`): `struct SidecarPlanRow { std::string relative_path, sidecar, target_path, template_path, suggested_action; };`, `std::vector<SidecarPlanRow> build_sidecar_completion_plan(const std::vector<ads1292::index::SessionIndexRow>& rows, const std::string& template_dir);`, and `void write_quality_gate_json(const std::string& path, const ads1292::dsp::QualityGate& gate); ads1292::dsp::QualityGate quality_gate_template();`. (Expose `expected_sidecar_path(csv_path, sidecar)` + `sidecar_label(sidecar)` if useful for the test.)

- [ ] **Step 1: Write the failing test** (plan over rows with missing sidecars + quality_gate JSON round-trip)

```cpp
// tests/cpp/test_sidecar_repair.cpp
#include "catch.hpp"
#include "ads1292/io/SidecarRepair.h"
#include "ads1292/io/QualityGateIo.h"
#include "ads1292/index/SessionIndexRow.h"
#include <algorithm>
using namespace ads1292;
TEST_CASE("build_sidecar_completion_plan rows from missing sidecars", "[repair]") {
  index::SessionIndexRow row;
  row.path = "/data/rec1.csv"; row.relative_path = "rec1.csv";
  row.session_id = "run-1"; row.missing_sidecars = "calibration;processing";
  auto plan = io::build_sidecar_completion_plan({row}, "/tmp/templates");
  REQUIRE(plan.size() == 2);
  REQUIRE(plan[0].sidecar == "calibration");
  REQUIRE(plan[0].target_path == "/data/rec1.calibration.json");
  REQUIRE(plan[0].template_path == "/tmp/templates/rec1.calibration.json");
  REQUIRE(plan[0].suggested_action == "Create calibration sidecar");
  REQUIRE(plan[1].sidecar == "processing");
}
TEST_CASE("quality_gate label + processing label use spaces", "[repair]") {
  index::SessionIndexRow row; row.path="/d/r.csv"; row.relative_path="r.csv"; row.missing_sidecars="quality_gate";
  auto plan = io::build_sidecar_completion_plan({row}, "/tmp/t");
  REQUIRE(plan[0].target_path == "/d/r.quality-gate.json");
  REQUIRE(plan[0].suggested_action == "Create quality gate sidecar");   // '_'->' '
}
TEST_CASE("write_quality_gate_json round-trips defaults", "[repair]") {
  auto p = (std::string(SCRATCH_OR_TMP) + "/p7b_qg.json");   // use std::filesystem::temp_directory_path()
  io::write_quality_gate_json(p, io::quality_gate_template());
  std::ifstream f(p); std::string s((std::istreambuf_iterator<char>(f)), {});
  REQUIRE(s.find("\"min_duration_seconds\": 8.0") != std::string::npos);
  REQUIRE(s.find("\"require_qrs_clear\": true") != std::string::npos);
  REQUIRE(s.find("\"max_noise_rms_counts\": null") != std::string::npos);   // unset optional -> null
}
```
(Use `std::filesystem::temp_directory_path()` for the temp path; include `<filesystem>`/`<fstream>`/`<iterator>`.)

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** the path helpers (`expected_sidecar_path`, `sidecar_label`, `template_path_for`) + `build_sidecar_completion_plan` (split missing_sidecars on ';', skip empty) + `write_quality_gate_json` (ordered_json with the 9 keys; the 3 optionals → `null` when unset, else the value) + `quality_gate_template` (=`QualityGate{}`). Per the Global Constraints.

- [ ] **Step 4: Wire CMake, build, run.** Expected PASS.

- [ ] **Step 5: Commit** `git commit -m "feat: P7b sidecar completion plan + quality_gate JSON"`

---

### Task 2: template bundle + apply script + index wiring

**Files:** Modify `io/include/ads1292/io/SidecarRepair.h` + `io/src/SidecarRepair.cpp` (add write_sidecar_template_bundle + write_sidecar_apply_script + _write_sidecar_template); Modify `cli/src/Cli.cpp` (run_index emits them); Modify `tests/cpp/test_sidecar_repair.cpp` (bundle + script cases).

**Interfaces:**
- Consumes: the P7b sidecar writers (`write_metadata_json`/`write_events_json`/`write_calibration_json`/`write_acquisition_json`/`write_protocol_json`/`write_processing_json` + templates), Task 1 `write_quality_gate_json`.
- Produces (namespace `ads1292::io`): `std::vector<std::string> write_sidecar_template_bundle(const std::string& template_dir, const std::vector<ads1292::index::SessionIndexRow>& rows);`, `void write_sidecar_apply_script(const std::string& path, const std::vector<SidecarPlanRow>& plan);`.

- [ ] **Step 1: Write the failing test** (templates written + parse back; script content)

```cpp
TEST_CASE("write_sidecar_template_bundle writes parseable template sidecars", "[repair]") {
  auto dir = std::filesystem::temp_directory_path() / "p7b_bundle";
  std::filesystem::remove_all(dir); std::filesystem::create_directories(dir);
  index::SessionIndexRow row; row.path=(dir/"rec1.csv").string(); row.relative_path="rec1.csv";
  row.session_id="run-1"; row.subject_id="subjA"; row.missing_sidecars="metadata;calibration;quality_gate;processing;protocol;events;acquisition";
  auto written = io::write_sidecar_template_bundle((dir/"templates").string(), {row});
  REQUIRE(written.size() == 7);
  // the metadata template carries the row's session_id + the review note
  auto meta = ads1292::io::read_metadata_json((dir/"templates"/"rec1.json").string());
  REQUIRE(meta.session_id == "run-1");
  // the calibration template parses to defaults
  auto cal = ads1292::io::read_calibration_json((dir/"templates"/"rec1.calibration.json").string());
  REQUIRE(cal.label == "ADS1292 default");
}
TEST_CASE("write_sidecar_apply_script emits a cp -n script", "[repair]") {
  index::SessionIndexRow row; row.path="/data/rec1.csv"; row.relative_path="rec1.csv"; row.missing_sidecars="calibration";
  auto plan = io::build_sidecar_completion_plan({row}, "/tmp/templates");
  auto sp = (std::filesystem::temp_directory_path()/"p7b_apply.sh").string();
  io::write_sidecar_apply_script(sp, plan);
  std::ifstream f(sp); std::string s((std::istreambuf_iterator<char>(f)), {});
  REQUIRE(s.rfind("#!/bin/sh", 0) == 0);
  REQUIRE(s.find("set -eu") != std::string::npos);
  REQUIRE(s.find("cp -n") != std::string::npos);
  REQUIRE(s.find("rec1.csv: calibration") != std::string::npos);
}
TEST_CASE("write_sidecar_apply_script with no missing prints the echo", "[repair]") {
  auto sp = (std::filesystem::temp_directory_path()/"p7b_apply_empty.sh").string();
  io::write_sidecar_apply_script(sp, {});
  std::ifstream f(sp); std::string s((std::istreambuf_iterator<char>(f)), {});
  REQUIRE(s.find("No missing sidecars to apply.") != std::string::npos);
}
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Implement** `_write_sidecar_template` (per the Global Constraints — reuse the P7b writers/templates + Task 1 write_quality_gate_json + the simplified acquisition template) + `write_sidecar_template_bundle` (per-missing-sidecar, create dirs, write, collect) + `write_sidecar_apply_script` (the #!/bin/sh + set -eu + per-row mkdir/cp -n, POSIX shell-quoting, empty→echo, chmod 0755). Then extend `run_index` (cli/Cli.cpp) to, after writing the index json, also: `auto plan = build_sidecar_completion_plan(rows, <out>/sidecar-templates); write_sidecar_template_bundle(<out>/sidecar-templates, rows); write_sidecar_apply_script(<out>/apply-sidecars.sh, plan);` and print `sidecar_plan_rows=<plan.size()>`, `sidecar_apply_script=<path>`. (Keep the existing run_index output lines.)

- [ ] **Step 4: Wire CMake, build, run.** Iterate until the bundle/script/index cases pass.

- [ ] **Step 5: Commit** `git commit -m "feat: P7b sidecar template bundle + apply script + index wiring"`

---

## Self-Review

**1. Spec coverage:** sidecar completion plan → Task 1 ✓; quality_gate JSON (needed for the bundle) → Task 1 ✓; template bundle + apply script + index wiring → Task 2 ✓. Recording-MANIFEST repair (`build_recording_manifest_repair_plan`/`write_recording_manifest_apply_script`) → DEFERRED (manifest module not ported, documented). The acquisition template uses a SIMPLIFIED default (vs `build_acquisition_provenance`) — documented.

**2. Placeholder scan:** the plan/path-helper logic + the apply-script line format + the quality_gate JSON keys are spelled out; the test bodies are concrete. The template bundle reuses the verified P7b writers/templates (parse-back tested). Parity is plan rows + script content + parseable templates.

**3. Type consistency:** `SidecarPlanRow`/`build_sidecar_completion_plan` (Task 1) used by `write_sidecar_apply_script` (Task 2) + run_index; `write_quality_gate_json`/`quality_gate_template` (Task 1) used by `_write_sidecar_template` (Task 2). Reuses P7b-3 `SessionIndexRow`, P7b-1/2 sidecar writers/templates, P7a `QualityGate`.

**Risk notes for the executor:**
- The MANIFEST repair tooling is DEFERRED (manifest module not ported) — do NOT stub a fake manifest verifier; only the SIDECAR repair is in scope.
- The acquisition template is a SIMPLIFIED default `AcquisitionProvenance{csv_name, port="review-required", started_at="review-required"}.normalized()` (the Python `build_acquisition_provenance` with calibration/live_calibration args isn't ported) — document it; it still produces a valid, parseable acquisition sidecar.
- `_expected_sidecar_path` strips the trailing `.csv` and appends the new suffix (e.g. `rec1.csv` → `rec1.calibration.json`) — match Python `with_suffix` semantics (replaces the LAST suffix).
- The apply-script shell-quoting must be POSIX single-quote-safe (match `shlex.quote`); `chmod 0755` the script.
- `write_quality_gate_json`'s 3 optional caps serialize as JSON `null` when unset (match Python `asdict` of `None`).
- Keep it Qt-free + in io; reuse the P7b writers (do NOT reimplement sidecar serialization).
