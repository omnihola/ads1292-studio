# P-1 Golden Fixtures Design

## 1. Purpose

Phase 1 (P-1) freezes the Python oracle behavior of the ADS1292 Studio application into golden test fixtures. These fixtures serve as:

- **Immutable reference implementations** of correct behavior for downstream test suites and C++ verification.
- **Regression prevention** against unintended changes to core processing functions.
- **Integration points** between Python prototyping and C++ production code.

**Scope:** P-1 captures Python-only behavior. No C++ implementation occurs in this phase. The C++ reader interface is specified as a forward requirement only.

---

## 2. Fixture Format Specification

Every fixture is a JSON file: `tests/fixtures/golden/<category>/<name>.json` with this envelope:

```json
{
  "schema_version": 1,
  "category": "device_parser",
  "name": "stream_payload_nominal",
  "oracle": { "function": "ads1292_studio.device.parse_stream_payload", "module_commit_ref": "see ../oracle.json" },
  "input": { "...": "category-specific" },
  "output": { "...": "category-specific" },
  "tolerance": { "kind": "abs", "value": 1e-6 },
  "notes": "human-readable description of what this freezes"
}
```

- **Floats:** emitted via a canonical encoder (Python `repr`, full precision, round-trippable). Arrays are JSON arrays of numbers.
- **Binary frames:** lowercase hex string with no separators.
- **Error oracles (bad frames):** `output` is `{ "raises": "ValueError", "message_contains": "bad stream trailer" }`.
- **Exact-match outputs (peak indices):** `tolerance` is `{ "kind": "exact" }`.
- **Binary file fixtures (HDF5/XLSX):** the real artifact lives next to the JSON sidecar; the JSON captures structure + per-array sha256, not the file bytes.
- **File sidecars (file_csv_live/file_hdf5/file_xlsx):** use a FLAT shape (category-specific top-level keys, e.g. csv_header / datasets / sheet_names), NOT the input/output envelope.

---

## 3. Per-Category Field Tables

Each category below will be filled as Tasks 4–9 land. For now, each lists the oracle function and placeholder fields to be populated later.

### device_parser
Oracle function: `ads1292_studio.device.parse_stream_payload`  
Input fields: *(to be filled by Task 4)*  
Output fields: *(to be filled by Task 4)*  
Tolerance: *(to be filled by Task 4)*  

### dsp_coefficients
Oracle function: *(to be filled by Task 5)*  
Input fields: *(to be filled by Task 5)*  
Output fields: *(to be filled by Task 5)*  
Tolerance: *(to be filled by Task 5)*  

### dsp_filter_output
Oracle function: *(to be filled by Task 5)*  
Input fields: *(to be filled by Task 5)*  
Output fields: *(to be filled by Task 5)*  
Tolerance: *(to be filled by Task 5)*  

### rpeak_chain
Oracle function: *(to be filled by Task 6)*  
Input fields: *(to be filled by Task 6)*  
Output fields: *(to be filled by Task 6)*  
Tolerance: *(to be filled by Task 6)*  

### hr_summary
Oracle function: *(to be filled by Task 7)*  
Input fields: *(to be filled by Task 7)*  
Output fields: *(to be filled by Task 7)*  
Tolerance: *(to be filled by Task 7)*  

### pqrst_review
Oracle function: *(to be filled by Task 8)*  
Input fields: *(to be filled by Task 8)*  
Output fields: *(to be filled by Task 8)*  
Tolerance: *(to be filled by Task 8)*  

### quality_metrics
Oracle function: *(to be filled by Task 8)*  
Input fields: *(to be filled by Task 8)*  
Output fields: *(to be filled by Task 8)*  
Tolerance: *(to be filled by Task 8)*  

### realtime_snr
Oracle function: *(to be filled by Task 9)*  
Input fields: *(to be filled by Task 9)*  
Output fields: *(to be filled by Task 9)*  
Tolerance: *(to be filled by Task 9)*  

### spectrum
Oracle function: *(to be filled by Task 9)*  
Input fields: *(to be filled by Task 9)*  
Output fields: *(to be filled by Task 9)*  
Tolerance: *(to be filled by Task 9)*  

### file_csv_live
Oracle function: *(to be filled by Task 10)*  
Input fields: *(to be filled by Task 10)*  
Output fields: *(to be filled by Task 10)*  
Tolerance: *(to be filled by Task 10)*  

### file_hdf5
Oracle function: *(to be filled by Task 10)*  
Input fields: *(to be filled by Task 10)*  
Output fields: *(to be filled by Task 10)*  
Tolerance: *(to be filled by Task 10)*  

### file_xlsx
Oracle function: *(to be filled by Task 11)*  
Input fields: *(to be filled by Task 11)*  
Output fields: *(to be filled by Task 11)*  
Tolerance: *(to be filled by Task 11)*  

---

## 4. Provenance Manifest (`oracle.json`)

Every fixture category root will contain an `oracle.json` file documenting the environment and command used to generate the fixtures. The manifest includes the following fields (one per line):

- `oracle_repo_commit` — git commit SHA of the Python oracle at generation time
- `python_version` — semantic version of Python executable used
- `numpy_version` — semantic version of NumPy
- `scipy_version` — semantic version of SciPy
- `h5py_version` — semantic version of h5py
- `sample_rate_hz` — sample rate used in fixture generation (e.g., 500 Hz)
- `fixture_generation_command` — the exact bash command used to invoke the fixture generator
- `platform` — platform identifier (e.g., `macos-amd64` or `linux-arm64`)

All fixtures under a category share the same `oracle.json` provenance.

---

## 5. P-1 Acceptance Criteria

- [ ] Python oracle generates fixtures in the format specified in Section 2.
- [ ] Python validator verifies schema, hash, version, and tolerance-field completeness for all fixtures.
- [ ] Every fixture has corresponding `oracle.json` provenance metadata.
- [ ] Generation script is repeatable and deterministic (identical fixture sets produced on subsequent runs).
- [ ] C++/Catch2 reader is specified as an interface requirement only; not implemented in P-1.

---

## 6. C++/Catch2 Reader Interface (Forward Requirement)

A future C++ reader MUST:

- Load the JSON envelope from `tests/fixtures/golden/<category>/<name>.json`.
- Deserialize the stored input arrays.
- Compare the C++ output against the stored `output` field using the `tolerance` specification.
- **MUST NOT** regenerate inputs; it MUST use the fixture's input arrays as-is.
- For HDF5/XLSX fixtures, compare at the sidecar (JSON metadata) level, not byte-for-byte file comparison.

This reader is a deferred requirement (target: P-2) and will be integrated into the Catch2 test suite after core C++ modules are implemented.

---

## References

- Task 1 (this): Scaffolds directories and design doc
- Tasks 2–3: Fixture generator and validator
- Tasks 4–9: Category-specific fixture generation
- Task 10: File-based fixture generation
- Task 11: XLSX fixture generation
- P-2+: C++/Catch2 reader implementation
