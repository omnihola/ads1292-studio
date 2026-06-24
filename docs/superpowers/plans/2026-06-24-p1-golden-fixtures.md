# P-1 Golden Fixtures Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the existing Python implementation's behavior into language-neutral golden fixtures + a Python validator, so the later C++/Qt rewrite has a fixed, versioned oracle to match — with **zero C++ written in this phase**.

**Architecture:** Pure-Python tooling. A generator calls the existing `ads1292_studio` oracle functions and serializes their inputs/outputs to JSON (+ real `.h5`/`.xlsx` artifacts with JSON sidecars). A validator checks every fixture's schema, provenance, hashes, and tolerance fields. A pytest re-runs the oracle to prove each stored golden is a faithful, reproducible capture of the pinned Python version. The C++/Catch2 reader is **specified as an interface note only**, not implemented.

**Tech Stack:** Python 3.11 (`sensor` conda env), numpy, scipy, h5py, the existing `ads1292_studio` package as the oracle, pytest. JSON for fixtures; hex strings for binary frames; real `.h5`/`.xlsx` files for binary formats.

## Global Constraints

- **No C++ in P-1.** No CMake, no Qt, no QSerialPort, no LiveScope, no Catch2 implementation. C++/Catch2 reader requirements are written as a doc note only.
- **Oracle = the current Python package**, run in the `sensor` conda env. Invocation prefix: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor`.
- **Every fixture batch carries an `oracle.json` provenance manifest** with: `oracle_repo_commit`, `python_version`, `numpy_version`, `scipy_version`, `h5py_version`, `sample_rate_hz`, `fixture_generation_command`, `platform`. A fixture without provenance must fail validation.
- **Frozen inputs, not seeds.** Any synthetic signal is generated once and stored verbatim in the fixture as a numeric array. The C++ side will consume the stored input; it must never regenerate from a seed (cross-language RNG differs).
- **Tolerances are explicit per fixture.** Coefficients: abs `1e-12`. filtfilt/filter outputs: abs `1e-6`. FFT power: rel `1e-9`. R-peak indices: exact integer equality. HR/float summaries: abs `1e-9`.
- **Determinism.** Running the generator twice on the same oracle commit must produce byte-identical JSON fixtures (sorted keys, fixed float formatting via Python `repr`). HDF5/XLSX binary artifacts may differ byte-wise; their JSON sidecars (schema/attrs/cells/hashes-of-arrays) must be byte-identical.
- **Fixture root:** `tests/fixtures/golden/`. **Generator:** `scripts/generate_golden_fixtures.py`. **Validator:** `scripts/validate_golden_fixtures.py`. **Pytest:** `tests/test_golden_fixtures.py`.
- **Compatibility contract levels** (from the master spec) govern which fields a fixture must capture: CSV text-level; HDF5 schema+datasets+attrs+per-array-hash; XLSX sheet-names+cell-values; DSP numeric tolerance; reports out of P-1 scope.

---

## Fixture Format Specification

Every fixture is a JSON file: `tests/fixtures/golden/<category>/<name>.json` with this envelope:

```json
{
  "schema_version": 1,
  "category": "device_parser",
  "name": "stream_payload_nominal",
  "oracle": {
    "function": "ads1292_studio.device.parse_stream_payload",
    "module_commit_ref": "see ../oracle.json"
  },
  "input": { "...": "category-specific" },
  "output": { "...": "category-specific" },
  "tolerance": { "kind": "abs", "value": 1e-6 },
  "notes": "human-readable description of what this freezes"
}
```

- **Floats**: emitted via a canonical encoder (Python `repr`, full precision, round-trippable). Arrays are JSON arrays of numbers.
- **Binary frames**: lowercase hex string with no separators, e.g. `"02 93..."` → `"0293..."`.
- **Error oracles** (bad frames): `output` is `{ "raises": "ValueError", "message_contains": "bad stream trailer" }`.
- **Exact-match outputs** (peak indices): `tolerance` is `{ "kind": "exact" }`.
- **Binary file fixtures** (HDF5/XLSX): the real artifact lives next to the JSON sidecar (`<name>.h5` / `<name>.xlsx`); the JSON captures structure + per-array sha256, not the file bytes.

The standalone schema design doc (`docs/superpowers/specs/2026-06-24-p1-golden-fixtures-design.md`) reproduces this section plus the per-category field tables produced in Tasks 4–9.

---

### Task 1: P-1 design doc + fixture scaffold

**Files:**
- Create: `docs/superpowers/specs/2026-06-24-p1-golden-fixtures-design.md`
- Create: `tests/fixtures/golden/.gitkeep`
- Create: `scripts/__init__.py` (empty, makes `scripts` importable in tests)

**Interfaces:**
- Consumes: nothing.
- Produces: the directory layout and the design doc that Tasks 2–11 reference.

- [ ] **Step 1: Create the fixture root and scripts package**

```bash
mkdir -p tests/fixtures/golden
touch tests/fixtures/golden/.gitkeep
touch scripts/__init__.py
```

- [ ] **Step 2: Write the design doc**

Create `docs/superpowers/specs/2026-06-24-p1-golden-fixtures-design.md` with these sections, copied/expanded from this plan:
1. Purpose: freeze Python oracle behavior; no C++ in P-1.
2. The "Fixture Format Specification" envelope (copy verbatim from this plan).
3. Per-category field tables (placeholders to be filled as Tasks 4–9 land; each table lists the exact oracle function, input fields, output fields, tolerance).
4. Provenance manifest (`oracle.json`) field list.
5. P-1 acceptance criteria (verbatim):
   - Python oracle generates fixtures.
   - Python validator verifies schema, hash, version, tolerance-field completeness.
   - Every fixture has `oracle.json` provenance.
   - Generation script is repeatable and stable (deterministic JSON).
   - C++/Catch2 reader is specified as an interface requirement only, not implemented in P-1.
6. C++/Catch2 reader interface note (forward requirement): "A future C++ reader MUST load the JSON envelope, the stored input arrays, and compare against `output` using `tolerance`; it MUST NOT regenerate inputs. HDF5/XLSX fixtures are compared at sidecar level."

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-06-24-p1-golden-fixtures-design.md tests/fixtures/golden/.gitkeep scripts/__init__.py
git commit -m "docs: P-1 golden fixture design doc and scaffold"
```

---

### Task 2: Provenance manifest (`oracle.json`)

**Files:**
- Create: `scripts/fixture_provenance.py`
- Test: `tests/test_fixture_provenance.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `build_provenance(sample_rate_hz: float, generation_command: str) -> dict` — returns the manifest dict.
  - `write_provenance(root: Path, sample_rate_hz: float, generation_command: str) -> Path` — writes `<root>/oracle.json`, returns the path.
  - `REQUIRED_PROVENANCE_KEYS: tuple[str, ...]` — `("oracle_repo_commit", "python_version", "numpy_version", "scipy_version", "h5py_version", "sample_rate_hz", "fixture_generation_command", "platform")`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fixture_provenance.py
from pathlib import Path
import json
from scripts.fixture_provenance import build_provenance, write_provenance, REQUIRED_PROVENANCE_KEYS


def test_provenance_has_all_required_keys():
    manifest = build_provenance(sample_rate_hz=500.0, generation_command="python -m scripts.generate_golden_fixtures")
    for key in REQUIRED_PROVENANCE_KEYS:
        assert key in manifest, f"missing provenance key: {key}"
    assert manifest["sample_rate_hz"] == 500.0
    assert manifest["python_version"].count(".") >= 2


def test_write_provenance_round_trips(tmp_path: Path):
    path = write_provenance(tmp_path, sample_rate_hz=500.0, generation_command="cmd")
    assert path.name == "oracle.json"
    loaded = json.loads(path.read_text())
    assert loaded["fixture_generation_command"] == "cmd"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_fixture_provenance.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.fixture_provenance'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/fixture_provenance.py
from __future__ import annotations

import json
import platform as _platform
import subprocess
import sys
from pathlib import Path

import h5py
import numpy
import scipy

REQUIRED_PROVENANCE_KEYS = (
    "oracle_repo_commit",
    "python_version",
    "numpy_version",
    "scipy_version",
    "h5py_version",
    "sample_rate_hz",
    "fixture_generation_command",
    "platform",
)


def _git_commit() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True)
        return out.strip()
    except Exception:
        return "unknown"


def build_provenance(sample_rate_hz: float, generation_command: str) -> dict:
    return {
        "oracle_repo_commit": _git_commit(),
        "python_version": sys.version.split()[0],
        "numpy_version": numpy.__version__,
        "scipy_version": scipy.__version__,
        "h5py_version": h5py.__version__,
        "sample_rate_hz": float(sample_rate_hz),
        "fixture_generation_command": generation_command,
        "platform": f"{_platform.system()}-{_platform.machine()}",
    }


def write_provenance(root: Path, sample_rate_hz: float, generation_command: str) -> Path:
    manifest = build_provenance(sample_rate_hz, generation_command)
    path = Path(root) / "oracle.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_fixture_provenance.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/fixture_provenance.py tests/test_fixture_provenance.py
git commit -m "feat: P-1 fixture provenance manifest"
```

---

### Task 3: Canonical fixture serialization helpers

**Files:**
- Create: `scripts/fixture_io.py`
- Test: `tests/test_fixture_io.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `dump_fixture(obj: dict, path: Path) -> None` — writes canonical JSON (sorted keys, `ensure_ascii=False`, trailing newline) so re-runs are byte-identical.
  - `load_fixture(path: Path) -> dict`.
  - `floats(seq) -> list[float]` — coerces a numpy array / iterable to a plain `list[float]` for JSON.
  - `to_hex(data: bytes) -> str` / `from_hex(text: str) -> bytes`.
  - `sha256_array(arr) -> str` — sha256 of a numpy array's canonical bytes (C-order, float64), for HDF5 sidecars.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fixture_io.py
from pathlib import Path
import numpy as np
from scripts.fixture_io import dump_fixture, load_fixture, floats, to_hex, from_hex, sha256_array


def test_dump_is_deterministic(tmp_path: Path):
    obj = {"b": 2, "a": [1.5, 2.25]}
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    dump_fixture(obj, p1)
    dump_fixture(obj, p2)
    assert p1.read_bytes() == p2.read_bytes()
    assert load_fixture(p1) == obj


def test_floats_coerces_numpy():
    assert floats(np.array([1, 2, 3], dtype=float)) == [1.0, 2.0, 3.0]


def test_hex_round_trip():
    assert from_hex(to_hex(b"\x02\x93")) == b"\x02\x93"


def test_sha256_array_is_stable():
    arr = np.arange(10, dtype=float)
    assert sha256_array(arr) == sha256_array(arr.copy())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_fixture_io.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.fixture_io'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/fixture_io.py
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


def dump_fixture(obj: dict, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    Path(path).write_text(text + "\n")


def load_fixture(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def floats(seq) -> list[float]:
    return [float(v) for v in np.asarray(seq, dtype=float).tolist()]


def to_hex(data: bytes) -> str:
    return bytes(data).hex()


def from_hex(text: str) -> bytes:
    return bytes.fromhex(text)


def sha256_array(arr) -> str:
    canonical = np.ascontiguousarray(np.asarray(arr, dtype=float))
    return hashlib.sha256(canonical.tobytes(order="C")).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_fixture_io.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/fixture_io.py tests/test_fixture_io.py
git commit -m "feat: P-1 canonical fixture serialization helpers"
```

---

### Task 4: Device parser fixtures

**Files:**
- Create: `scripts/gen_device_fixtures.py`
- Create (generated): `tests/fixtures/golden/device_parser/*.json`
- Test: `tests/test_gen_device_fixtures.py`

**Interfaces:**
- Consumes: `scripts.fixture_io` (`dump_fixture`, `to_hex`, `floats`).
- Produces: `generate(root: Path) -> list[Path]` — writes device-parser fixtures, returns written paths.

**Oracle:** `ads1292_studio.device.parse_stream_payload(payload, start_timestamp, sample_rate_hz, start_index)` and `parse_acquire_payload(...)`. Stream payload = 61 bytes (3 header + 14×4 + 2 trailer in `STREAM_TRAILERS`). Acquire payload = 51 bytes (2 status + 8×6 + 1 `END=0x03` trailer).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gen_device_fixtures.py
from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_device_fixtures import generate


def test_generates_stream_and_acquire_and_errors(tmp_path: Path):
    paths = generate(tmp_path)
    names = {p.stem for p in paths}
    assert "stream_payload_nominal" in names
    assert "acquire_payload_nominal" in names
    assert "stream_bad_trailer" in names
    assert "stream_too_short" in names
    assert "acquire_bad_trailer" in names

    nominal = load_fixture(tmp_path / "device_parser" / "stream_payload_nominal.json")
    assert len(nominal["output"]["samples"]) == 14
    assert nominal["output"]["samples"][0]["ch1"] is not None

    bad = load_fixture(tmp_path / "device_parser" / "stream_bad_trailer.json")
    assert bad["output"]["raises"] == "ValueError"
    assert "trailer" in bad["output"]["message_contains"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_device_fixtures.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gen_device_fixtures'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/gen_device_fixtures.py
from __future__ import annotations

from pathlib import Path

from ads1292_studio.device import (
    END,
    parse_acquire_payload,
    parse_stream_payload,
)
from scripts.fixture_io import dump_fixture, to_hex

SAMPLE_RATE = 500.0


def _stream_payload_bytes() -> bytes:
    # 3-byte header (hr, resp, status) + 14 samples * 4 bytes (ch1 LE, ch2 LE) + 2-byte trailer.
    header = bytes([72, 18, 0x05])  # heart_rate=72, resp=18, status=0x05 (lead_off bits 0101)
    body = bytearray()
    for i in range(14):
        ch1 = 100 + i
        ch2 = -200 + i
        body += bytes([ch1 & 0xFF, (ch1 >> 8) & 0xFF, ch2 & 0xFF, (ch2 >> 8) & 0xFF])
    return header + bytes(body) + bytes([END, END])


def _acquire_payload_bytes() -> bytes:
    # 2-byte status + 8 samples * 6 bytes (ch1 24b BE, ch2 24b BE) + 1-byte END trailer.
    status = bytes([0x00, 0x05])
    body = bytearray()
    for i in range(8):
        ch1 = 1000 + i
        ch2 = -2000 - i
        body += (ch1 & 0xFFFFFF).to_bytes(3, "big")
        body += (ch2 & 0xFFFFFF).to_bytes(3, "big")
    return status + bytes(body) + bytes([END])


def _sample_dict(sample) -> dict:
    keys = ("timestamp", "ch1", "ch2", "board_heart_rate", "board_respiration_rate",
            "status_byte", "sample_index", "ch1_raw24", "ch2_raw24")
    out = {}
    for key in keys:
        if hasattr(sample, key):
            out[key] = getattr(sample, key)
    out["lead_off_bits"] = sample.lead_off_bits
    return out


def generate(root: Path) -> list[Path]:
    out_dir = Path(root) / "device_parser"
    written: list[Path] = []

    stream_bytes = _stream_payload_bytes()
    stream_samples = parse_stream_payload(stream_bytes, start_timestamp=0.0,
                                          sample_rate_hz=SAMPLE_RATE, start_index=0)
    written.append(_write(out_dir / "stream_payload_nominal.json", {
        "schema_version": 1, "category": "device_parser", "name": "stream_payload_nominal",
        "oracle": {"function": "ads1292_studio.device.parse_stream_payload"},
        "input": {"payload_hex": to_hex(stream_bytes), "start_timestamp": 0.0,
                  "sample_rate_hz": SAMPLE_RATE, "start_index": 0},
        "output": {"samples": [_sample_dict(s) for s in stream_samples]},
        "tolerance": {"kind": "exact"},
        "notes": "14 stream samples, int16 LE ch1/ch2, lead_off_bits from status low nibble",
    }))

    acquire_bytes = _acquire_payload_bytes()
    acquire_samples = parse_acquire_payload(acquire_bytes, start_timestamp=0.0,
                                            sample_rate_hz=SAMPLE_RATE, start_index=0)
    written.append(_write(out_dir / "acquire_payload_nominal.json", {
        "schema_version": 1, "category": "device_parser", "name": "acquire_payload_nominal",
        "oracle": {"function": "ads1292_studio.device.parse_acquire_payload"},
        "input": {"payload_hex": to_hex(acquire_bytes), "start_timestamp": 0.0,
                  "sample_rate_hz": SAMPLE_RATE, "start_index": 0},
        "output": {"samples": [_sample_dict(s) for s in acquire_samples]},
        "tolerance": {"kind": "exact"},
        "notes": "8 raw samples, int24 BE ch1/ch2, 16-bit status word",
    }))

    # Error oracles: capture exception type + message substring.
    written.append(_write_error(out_dir / "stream_bad_trailer.json", "stream_bad_trailer",
        "ads1292_studio.device.parse_stream_payload",
        stream_bytes[:-2] + bytes([0x00, 0x00]), "trailer"))
    written.append(_write_error(out_dir / "stream_too_short.json", "stream_too_short",
        "ads1292_studio.device.parse_stream_payload",
        stream_bytes[:40], "too short"))
    written.append(_write_error(out_dir / "acquire_bad_trailer.json", "acquire_bad_trailer",
        "ads1292_studio.device.parse_acquire_payload",
        acquire_bytes[:-1] + bytes([0x00]), "trailer"))
    return written


def _write(path: Path, payload: dict) -> Path:
    dump_fixture(payload, path)
    return path


def _write_error(path: Path, name: str, function: str, payload: bytes, message_contains: str) -> Path:
    func = {"ads1292_studio.device.parse_stream_payload": parse_stream_payload,
            "ads1292_studio.device.parse_acquire_payload": parse_acquire_payload}[function]
    try:
        func(payload, start_timestamp=0.0, sample_rate_hz=SAMPLE_RATE, start_index=0)
        raise AssertionError(f"expected {function} to raise on crafted payload")
    except ValueError as exc:
        assert message_contains in str(exc), f"message {str(exc)!r} lacks {message_contains!r}"
    dump_fixture({
        "schema_version": 1, "category": "device_parser", "name": name,
        "oracle": {"function": function},
        "input": {"payload_hex": to_hex(payload), "start_timestamp": 0.0,
                  "sample_rate_hz": SAMPLE_RATE, "start_index": 0},
        "output": {"raises": "ValueError", "message_contains": message_contains},
        "tolerance": {"kind": "exact"},
        "notes": "error oracle: malformed payload must raise ValueError",
    }, path)
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_device_fixtures.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Generate the committed fixtures and commit**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -c "from pathlib import Path; from scripts.gen_device_fixtures import generate; generate(Path('tests/fixtures/golden'))"
git add scripts/gen_device_fixtures.py tests/test_gen_device_fixtures.py tests/fixtures/golden/device_parser
git commit -m "feat: P-1 device parser golden fixtures"
```

---

### Task 5: DSP coefficient + filter-output fixtures

**Files:**
- Create: `scripts/_fixture_signals.py` (shared deterministic synthetic ECG)
- Create: `scripts/gen_dsp_fixtures.py`
- Create (generated): `tests/fixtures/golden/dsp/*.json`
- Test: `tests/test_gen_dsp_fixtures.py`

**Interfaces:**
- Consumes: `scripts.fixture_io`.
- Produces:
  - `scripts._fixture_signals.synthetic_ecg(n: int, sample_rate_hz: float) -> list[float]` — deterministic; returns a plain `list[float]` generated from a fixed numpy seed, used once at generation time and stored verbatim.
  - `scripts.gen_dsp_fixtures.generate(root: Path) -> list[Path]`.

**Oracle:** `signal_processing._bandpass_coefficients / _highpass_coefficients / _lowpass_coefficients / _notch_coefficients` (return `(b, a)` tuples) and `bandpass / highpass / lowpass / notch` (return filtered arrays via `scipy.signal.filtfilt`). **Must include a short-window case (size 16–40)** to freeze filtfilt boundary behavior, plus the `< 16` median-detrend fallback path.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gen_dsp_fixtures.py
from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_dsp_fixtures import generate


def test_generates_coeffs_and_filter_outputs(tmp_path: Path):
    paths = generate(tmp_path)
    names = {p.stem for p in paths}
    assert "coeffs_bandpass_500hz" in names
    assert "coeffs_notch_60hz_500hz" in names
    assert "filtfilt_bandpass_long" in names
    assert "filtfilt_bandpass_short_window" in names

    coeffs = load_fixture(tmp_path / "dsp" / "coeffs_bandpass_500hz.json")
    assert len(coeffs["output"]["b"]) == 5  # butter order 2 band -> 5 taps
    assert len(coeffs["output"]["a"]) == 5

    flt = load_fixture(tmp_path / "dsp" / "filtfilt_bandpass_long.json")
    assert len(flt["input"]["signal"]) == len(flt["output"]["filtered"])
    assert flt["tolerance"]["kind"] == "abs"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_dsp_fixtures.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gen_dsp_fixtures'`

- [ ] **Step 3: Write the shared signal generator**

```python
# scripts/_fixture_signals.py
from __future__ import annotations

import numpy as np


def synthetic_ecg(n: int, sample_rate_hz: float, *, bpm: float = 72.0, seed: int = 1292) -> list[float]:
    """Deterministic synthetic ECG: periodic QRS-like Gaussians + small seeded noise.

    Generated ONCE at fixture-build time and stored verbatim in the fixture.
    The C++ side consumes the stored array; it never calls this function.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n) / sample_rate_hz
    rr = 60.0 / bpm
    signal = np.zeros(n, dtype=float)
    beat_times = np.arange(0.4, t[-1] if n else 0.0, rr)
    for bt in beat_times:
        signal += 600.0 * np.exp(-((t - bt) ** 2) / (2 * 0.012 ** 2))   # R
        signal += -80.0 * np.exp(-((t - (bt - 0.03)) ** 2) / (2 * 0.010 ** 2))  # Q
        signal += -120.0 * np.exp(-((t - (bt + 0.03)) ** 2) / (2 * 0.012 ** 2))  # S
        signal += 90.0 * np.exp(-((t - (bt + 0.20)) ** 2) / (2 * 0.040 ** 2))   # T
    signal += rng.normal(0.0, 6.0, size=n)
    return [float(v) for v in signal]
```

- [ ] **Step 4: Write the DSP fixture generator**

```python
# scripts/gen_dsp_fixtures.py
from __future__ import annotations

from pathlib import Path

from ads1292_studio import signal_processing as sp
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, floats

SR = 500.0
ABS_TOL = 1e-6
COEF_TOL = 1e-12


def generate(root: Path) -> list[Path]:
    out = Path(root) / "dsp"
    written: list[Path] = []

    coeff_specs = [
        ("coeffs_bandpass_500hz", sp._bandpass_coefficients(SR, 0.7, 35.0)),
        ("coeffs_highpass_500hz", sp._highpass_coefficients(SR, 0.5)),
        ("coeffs_lowpass_500hz", sp._lowpass_coefficients(SR, 40.0)),
        ("coeffs_notch_60hz_500hz", sp._notch_coefficients(SR, 60.0, 30.0)),
    ]
    for name, (b, a) in coeff_specs:
        written.append(_write(out / f"{name}.json", {
            "schema_version": 1, "category": "dsp_coefficients", "name": name,
            "oracle": {"function": f"ads1292_studio.signal_processing.{name.split('_')[1]}_coefficients"},
            "input": {"sample_rate_hz": SR},
            "output": {"b": floats(b), "a": floats(a)},
            "tolerance": {"kind": "abs", "value": COEF_TOL},
            "notes": "scipy butter(2)/iirnotch transfer-function coefficients",
        }))

    long_signal = synthetic_ecg(2000, SR)
    short_signal = synthetic_ecg(32, SR)        # short window -> filtfilt boundary stress
    tiny_signal = synthetic_ecg(8, SR)          # < 16 -> median-detrend fallback path

    filt_specs = [
        ("filtfilt_bandpass_long", "bandpass", long_signal, sp.bandpass(long_signal, SR)),
        ("filtfilt_bandpass_short_window", "bandpass", short_signal, sp.bandpass(short_signal, SR)),
        ("filtfilt_bandpass_tiny_fallback", "bandpass", tiny_signal, sp.bandpass(tiny_signal, SR)),
        ("filtfilt_notch_long", "notch", long_signal, sp.notch(long_signal, SR)),
        ("filtfilt_highpass_long", "highpass", long_signal, sp.highpass(long_signal, SR)),
        ("filtfilt_lowpass_long", "lowpass", long_signal, sp.lowpass(long_signal, SR)),
    ]
    for name, kind, sig, filtered in filt_specs:
        written.append(_write(out / f"{name}.json", {
            "schema_version": 1, "category": "dsp_filter_output", "name": name,
            "oracle": {"function": f"ads1292_studio.signal_processing.{kind}"},
            "input": {"signal": floats(sig), "sample_rate_hz": SR},
            "output": {"filtered": floats(filtered)},
            "tolerance": {"kind": "abs", "value": ABS_TOL},
            "notes": f"{kind} via scipy.signal.filtfilt; frozen input stored verbatim",
        }))
    return written


def _write(path: Path, payload: dict) -> Path:
    dump_fixture(payload, path)
    return path
```

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_dsp_fixtures.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Generate and commit**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -c "from pathlib import Path; from scripts.gen_dsp_fixtures import generate; generate(Path('tests/fixtures/golden'))"
git add scripts/_fixture_signals.py scripts/gen_dsp_fixtures.py tests/test_gen_dsp_fixtures.py tests/fixtures/golden/dsp
git commit -m "feat: P-1 DSP coefficient and filtfilt golden fixtures"
```

---

### Task 6: R-peak chain fixtures

**Files:**
- Create: `scripts/gen_rpeak_fixtures.py`
- Create (generated): `tests/fixtures/golden/rpeak/*.json`
- Test: `tests/test_gen_rpeak_fixtures.py`

**Interfaces:**
- Consumes: `scripts._fixture_signals`, `scripts.fixture_io`.
- Produces: `generate(root: Path) -> list[Path]`.

**Oracle:** `signal_processing.detect_r_peaks(values, sample_rate_hz)`. Freeze the **full chain intermediates** so a C++ mismatch can be localized: `bandpass` output, `centered = filtered - median(filtered)`, `scale = std(centered)`, `prominence = max(20, scale*0.45)`, peak-signal polarity (`positive_excursion >= negative_excursion`), `distance = int(0.35*sr)`, and final peak indices.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gen_rpeak_fixtures.py
from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_rpeak_fixtures import generate


def test_freezes_rpeak_chain_intermediates(tmp_path: Path):
    paths = generate(tmp_path)
    assert any(p.stem == "rpeak_chain_clean_72bpm" for p in paths)
    fx = load_fixture(tmp_path / "rpeak" / "rpeak_chain_clean_72bpm.json")
    out = fx["output"]
    assert "filtered" in out and "centered" in out
    assert "prominence" in out and "distance" in out
    assert "polarity" in out  # "positive" or "negative"
    assert isinstance(out["peaks"], list)
    assert all(isinstance(i, int) for i in out["peaks"])
    assert fx["output_tolerances"]["peaks"]["kind"] == "exact"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_rpeak_fixtures.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gen_rpeak_fixtures'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/gen_rpeak_fixtures.py
from __future__ import annotations

from pathlib import Path

import numpy as np

from ads1292_studio import signal_processing as sp
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, floats

SR = 500.0


def _chain(signal: list[float]) -> dict:
    arr = np.asarray(signal, dtype=float)
    filtered = sp.bandpass(arr, SR)
    centered = filtered - np.median(filtered)
    scale = float(np.std(centered))
    prominence = max(20.0, scale * 0.45)
    positive = float(np.max(centered))
    negative = abs(float(np.min(centered)))
    polarity = "positive" if positive >= negative else "negative"
    peaks = sp.detect_r_peaks(arr, SR)
    return {
        "filtered": floats(filtered),
        "centered": floats(centered),
        "scale_std": scale,
        "prominence": prominence,
        "distance": int(0.35 * SR),
        "polarity": polarity,
        "peaks": [int(p) for p in peaks],
    }


def generate(root: Path) -> list[Path]:
    out = Path(root) / "rpeak"
    cases = {
        "rpeak_chain_clean_72bpm": synthetic_ecg(2500, SR, bpm=72.0),
        "rpeak_chain_fast_110bpm": synthetic_ecg(2500, SR, bpm=110.0),
        "rpeak_chain_short_below_sr": synthetic_ecg(300, SR),  # < sample_rate -> empty peaks
    }
    written: list[Path] = []
    for name, signal in cases.items():
        chain = _chain(signal)
        written.append(_write(out / f"{name}.json", {
            "schema_version": 1, "category": "rpeak_chain", "name": name,
            "oracle": {"function": "ads1292_studio.signal_processing.detect_r_peaks"},
            "input": {"signal": floats(signal), "sample_rate_hz": SR},
            "output": chain,
            "output_tolerances": {
                "filtered": {"kind": "abs", "value": 1e-6},
                "centered": {"kind": "abs", "value": 1e-6},
                "scale_std": {"kind": "abs", "value": 1e-9},
                "prominence": {"kind": "abs", "value": 1e-9},
                "peaks": {"kind": "exact"},
            },
            "notes": "full R-peak chain: bandpass -> centered -> prominence/polarity -> find_peaks",
        }))
    return written


def _write(path: Path, payload: dict) -> Path:
    dump_fixture(payload, path)
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_rpeak_fixtures.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Generate and commit**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -c "from pathlib import Path; from scripts.gen_rpeak_fixtures import generate; generate(Path('tests/fixtures/golden'))"
git add scripts/gen_rpeak_fixtures.py tests/test_gen_rpeak_fixtures.py tests/fixtures/golden/rpeak
git commit -m "feat: P-1 R-peak chain golden fixtures"
```

---

### Task 7: HR / PQRST / quality / realtime-SNR fixtures

**Files:**
- Create: `scripts/gen_review_fixtures.py`
- Create (generated): `tests/fixtures/golden/review/*.json`
- Test: `tests/test_gen_review_fixtures.py`

**Interfaces:**
- Consumes: `scripts._fixture_signals`, `scripts.fixture_io`.
- Produces: `generate(root: Path) -> list[Path]`.

**Oracle:** `signal_processing.heart_rate_summary(peaks, sr)`, `pqrst_review(values, peaks, sr)`, `quality.compute_quality_metrics(samples, sr, source)`, `quality.estimate_realtime_snr(values, sample_rate_hz=sr)`. Each downstream fixture **references the frozen upstream peaks** (stored in `input`) so HR/PQRST can be checked independently of R-peak drift.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gen_review_fixtures.py
from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_review_fixtures import generate


def test_freezes_hr_pqrst_quality_snr(tmp_path: Path):
    paths = generate(tmp_path)
    names = {p.stem for p in paths}
    assert "hr_summary_clean_72bpm" in names
    assert "pqrst_clean_72bpm" in names
    assert "quality_metrics_clean_72bpm" in names
    assert "realtime_snr_clean_72bpm" in names

    hr = load_fixture(tmp_path / "review" / "hr_summary_clean_72bpm.json")
    assert "peaks" in hr["input"]          # upstream frozen peaks
    assert "median_bpm" in hr["output"]

    snr = load_fixture(tmp_path / "review" / "realtime_snr_clean_72bpm.json")
    assert "snr_db" in snr["output"] and "noise_rms_counts" in snr["output"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_review_fixtures.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gen_review_fixtures'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/gen_review_fixtures.py
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

from ads1292_studio import signal_processing as sp
from ads1292_studio import quality as q
from ads1292_studio.models import StreamSample
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, floats

SR = 500.0
FLOAT_TOL = {"kind": "abs", "value": 1e-9}


def _stream_samples(ch2: list[float]) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(timestamp=i / SR, ch1=0, ch2=int(round(v)),
                     board_heart_rate=0, board_respiration_rate=0, status_byte=0)
        for i, v in enumerate(ch2)
    )


def generate(root: Path) -> list[Path]:
    out = Path(root) / "review"
    signal = synthetic_ecg(2500, SR, bpm=72.0)
    peaks = list(sp.detect_r_peaks(np.asarray(signal, dtype=float), SR))
    written: list[Path] = []

    hr = sp.heart_rate_summary(peaks, SR)
    written.append(_write(out / "hr_summary_clean_72bpm.json", {
        "schema_version": 1, "category": "hr_summary", "name": "hr_summary_clean_72bpm",
        "oracle": {"function": "ads1292_studio.signal_processing.heart_rate_summary"},
        "input": {"peaks": peaks, "sample_rate_hz": SR},
        "output": asdict(hr),
        "tolerance": FLOAT_TOL,
        "notes": "HR summary from frozen upstream peaks",
    }))

    pqrst = sp.pqrst_review(signal, peaks, SR)
    written.append(_write(out / "pqrst_clean_72bpm.json", {
        "schema_version": 1, "category": "pqrst_review", "name": "pqrst_clean_72bpm",
        "oracle": {"function": "ads1292_studio.signal_processing.pqrst_review"},
        "input": {"signal": floats(signal), "peaks": peaks, "sample_rate_hz": SR},
        "output": {
            "qrs_clear": pqrst.qrs_clear, "p_tentative": pqrst.p_tentative,
            "t_tentative": pqrst.t_tentative, "beats_used": pqrst.beats_used,
            "average_beat": floats(pqrst.average_beat), "time_ms": floats(pqrst.time_ms),
        },
        "output_tolerances": {"average_beat": {"kind": "abs", "value": 1e-6},
                              "time_ms": {"kind": "abs", "value": 1e-9}},
        "notes": "average-beat morphology + tentative P/T flags",
    }))

    samples = _stream_samples(signal)
    metrics = q.compute_quality_metrics(samples, SR, "Auto")
    written.append(_write(out / "quality_metrics_clean_72bpm.json", {
        "schema_version": 1, "category": "quality_metrics", "name": "quality_metrics_clean_72bpm",
        "oracle": {"function": "ads1292_studio.quality.compute_quality_metrics"},
        "input": {"ch2": floats(signal), "sample_rate_hz": SR, "source": "Auto"},
        "output": asdict(metrics),
        "tolerance": FLOAT_TOL,
        "notes": "full quality metrics incl. contact %, drift, noise RMS, peak-to-peak",
    }))

    snr = q.estimate_realtime_snr(np.asarray(signal, dtype=float), sample_rate_hz=SR)
    written.append(_write(out / "realtime_snr_clean_72bpm.json", {
        "schema_version": 1, "category": "realtime_snr", "name": "realtime_snr_clean_72bpm",
        "oracle": {"function": "ads1292_studio.quality.estimate_realtime_snr"},
        "input": {"values": floats(signal), "sample_rate_hz": SR},
        "output": asdict(snr),
        "tolerance": FLOAT_TOL,
        "notes": "lightweight realtime SNR: MAD-based noise RMS, p95-p5 peak-to-peak",
    }))
    return written


def _write(path: Path, payload: dict) -> Path:
    dump_fixture(payload, path)
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_review_fixtures.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Generate and commit**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -c "from pathlib import Path; from scripts.gen_review_fixtures import generate; generate(Path('tests/fixtures/golden'))"
git add scripts/gen_review_fixtures.py tests/test_gen_review_fixtures.py tests/fixtures/golden/review
git commit -m "feat: P-1 HR/PQRST/quality/SNR golden fixtures"
```

---

### Task 8: Spectrum fixtures

**Files:**
- Create: `scripts/gen_spectrum_fixtures.py`
- Create (generated): `tests/fixtures/golden/spectrum/*.json`
- Test: `tests/test_gen_spectrum_fixtures.py`

**Interfaces:**
- Consumes: `scripts._fixture_signals`, `scripts.fixture_io`.
- Produces: `generate(root: Path) -> list[Path]`.

**Oracle:** `spectrum.build_spectrum_analysis(samples, source, sample_rate_hz, max_frequency_hz, histogram_bins)`. The C++ KissFFT path must match `np.fft.rfft` of a Hann-windowed, mean-centered signal; freeze `ecg_frequency_hz`, `ecg_power`, `histogram_counts`, `histogram_bin_edges`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gen_spectrum_fixtures.py
from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_spectrum_fixtures import generate


def test_freezes_spectrum_and_histogram(tmp_path: Path):
    paths = generate(tmp_path)
    assert any(p.stem == "spectrum_clean_72bpm_ch2" for p in paths)
    fx = load_fixture(tmp_path / "spectrum" / "spectrum_clean_72bpm_ch2.json")
    out = fx["output"]
    assert len(out["ecg_frequency_hz"]) == len(out["ecg_power"])
    assert len(out["histogram_bin_edges"]) == len(out["histogram_counts"]) + 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_spectrum_fixtures.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gen_spectrum_fixtures'`

- [ ] **Step 3: Write the implementation**

```python
# scripts/gen_spectrum_fixtures.py
from __future__ import annotations

from pathlib import Path

from ads1292_studio.spectrum import build_spectrum_analysis
from ads1292_studio.models import StreamSample
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, floats

SR = 500.0


def _samples(ch2: list[float]) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(timestamp=i / SR, ch1=0, ch2=int(round(v)),
                     board_heart_rate=0, board_respiration_rate=0, status_byte=0)
        for i, v in enumerate(ch2)
    )


def generate(root: Path) -> list[Path]:
    out = Path(root) / "spectrum"
    signal = synthetic_ecg(2048, SR, bpm=72.0)
    analysis = build_spectrum_analysis(_samples(signal), source="CH2",
                                       sample_rate_hz=SR, max_frequency_hz=60.0, histogram_bins=48)
    path = out / "spectrum_clean_72bpm_ch2.json"
    dump_fixture({
        "schema_version": 1, "category": "spectrum", "name": "spectrum_clean_72bpm_ch2",
        "oracle": {"function": "ads1292_studio.spectrum.build_spectrum_analysis"},
        "input": {"ch2": floats(signal), "source": "CH2", "sample_rate_hz": SR,
                  "max_frequency_hz": 60.0, "histogram_bins": 48},
        "output": {
            "ecg_frequency_hz": floats(analysis.ecg_frequency_hz),
            "ecg_power": floats(analysis.ecg_power),
            "histogram_counts": [int(c) for c in analysis.histogram_counts],
            "histogram_bin_edges": floats(analysis.histogram_bin_edges),
        },
        "output_tolerances": {
            "ecg_frequency_hz": {"kind": "abs", "value": 1e-9},
            "ecg_power": {"kind": "rel", "value": 1e-9},
            "histogram_counts": {"kind": "exact"},
            "histogram_bin_edges": {"kind": "abs", "value": 1e-9},
        },
        "notes": "Hann-windowed rfft power + amplitude histogram",
    }, path)
    return [path]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_spectrum_fixtures.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Generate and commit**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -c "from pathlib import Path; from scripts.gen_spectrum_fixtures import generate; generate(Path('tests/fixtures/golden'))"
git add scripts/gen_spectrum_fixtures.py tests/test_gen_spectrum_fixtures.py tests/fixtures/golden/spectrum
git commit -m "feat: P-1 spectrum golden fixtures"
```

---

### Task 9: File-format fixtures (live/raw CSV, HDF5, **minimal XLSX semantic**, hashes)

**Files:**
- Create: `scripts/_xlsx_read.py` (minimal unzip+regex XLSX semantic reader — openpyxl is NOT in the env)
- Create: `scripts/gen_file_fixtures.py`
- Create (generated): `tests/fixtures/golden/files/*` (`.csv`, `.h5`, `.xlsx`, `*_sidecar.json`)
- Test: `tests/test_gen_file_fixtures.py`

**Interfaces:**
- Consumes: `scripts._fixture_signals`, `scripts.fixture_io`.
- Produces:
  - `scripts._xlsx_read.read_xlsx_semantic(path: Path) -> dict` — `{"sheet_names": [...], "sheets": {name: [[cell,...], ...]}}`; used by BOTH the generator (to freeze) and the validator (to re-check). Sheets are mapped to `sheet1.xml`/`sheet2.xml` by their order in `xl/workbook.xml`.
  - `scripts.gen_file_fixtures.generate(root: Path) -> list[Path]`.

**Oracle:** `csv_io.write_recording_csv` (live), `h5_io.write_recording_h5` / `verify_recording_h5`, `xlsx_io.write_recording_xlsx(csv_path, *, events, sample_rate_hz)`, `hashing.sha256_file`. **Live CSV** freezes the exact header + first rows (text-level). **HDF5** freezes a JSON sidecar: dataset names+shapes+dtypes, attribute keys+values, and `sha256_array` per sample array — **not** file bytes. **XLSX** is a **minimal semantic** fixture only: sheet names, Events header, Data header, ≥1 point-event row, ≥1 interval-event row, first/last data row — **no** style, column width, formula, or zip-entry equality. `EventMarker(timestamp_seconds, label, notes, duration_seconds)`: `duration_seconds == 0` → point event, `> 0` → interval event. Events sheet rows end in a type column literally `"point"`/`"interval"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gen_file_fixtures.py
from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_file_fixtures import generate


def test_freezes_csv_text_h5_sidecar_and_xlsx_semantic(tmp_path: Path):
    paths = generate(tmp_path)
    files_dir = tmp_path / "files"
    assert (files_dir / "live_recording.csv").exists()
    assert (files_dir / "live_recording_sidecar.json").exists()
    assert (files_dir / "recording.h5").exists()
    assert (files_dir / "recording.xlsx").exists()
    assert (files_dir / "recording_xlsx_sidecar.json").exists()

    live = load_fixture(files_dir / "live_recording_sidecar.json")
    assert live["csv_header"][0] == "timestamp"
    assert "ch2_counts" in live["csv_header"]

    h5 = load_fixture(files_dir / "recording_h5_sidecar.json")
    assert "datasets" in h5 and "attrs" in h5
    assert all("sha256" in d for d in h5["datasets"].values())
    assert h5["verify_ok"] is True

    xlsx = load_fixture(files_dir / "recording_xlsx_sidecar.json")
    assert len(xlsx["sheet_names"]) == 2
    assert xlsx["events_header"]            # exact header row, frozen
    assert xlsx["data_header"][0] == "timestamp"
    assert xlsx["point_event_row"][-3] == "point"     # type column
    assert xlsx["interval_event_row"][-3] == "interval"
    assert xlsx["data_first_row"] and xlsx["data_last_row"]
    assert xlsx["tolerance"]["kind"] == "semantic"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_file_fixtures.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.gen_file_fixtures'`

- [ ] **Step 3: Write the minimal XLSX semantic reader**

```python
# scripts/_xlsx_read.py
from __future__ import annotations

import re
import zipfile
from html import unescape
from pathlib import Path

_SHEET_NAME_RE = re.compile(r'<sheet [^>]*name="([^"]*)"')
_ROW_RE = re.compile(r"<row\b[^>]*>(.*?)</row>", re.DOTALL)
# Each cell carries exactly one of <v>..</v> (number) or <t>..</t> (inline string).
_CELL_VALUE_RE = re.compile(r"<v>(.*?)</v>|<t>(.*?)</t>", re.DOTALL)


def read_xlsx_semantic(path: Path) -> dict:
    """Semantic-only XLSX read: sheet names (workbook.xml order) + cell text per row.

    Deliberately ignores styles, column widths, formulas, and zip internals.
    sheet1.xml / sheet2.xml are matched to sheet names by their workbook order.
    """
    path = Path(path)
    with zipfile.ZipFile(path) as zf:
        workbook = zf.read("xl/workbook.xml").decode("utf-8")
        sheet_names = _SHEET_NAME_RE.findall(workbook)
        sheets: dict[str, list[list[str]]] = {}
        for order, name in enumerate(sheet_names, start=1):
            xml = zf.read(f"xl/worksheets/sheet{order}.xml").decode("utf-8")
            sheets[name] = _rows(xml)
    return {"sheet_names": sheet_names, "sheets": sheets}


def _rows(xml: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_xml in _ROW_RE.findall(xml):
        cells = [unescape(v if v else t) for v, t in _CELL_VALUE_RE.findall(row_xml)]
        rows.append(cells)
    return rows
```

- [ ] **Step 4: Write the file-format generator**

```python
# scripts/gen_file_fixtures.py
from __future__ import annotations

import csv
from pathlib import Path

import h5py
import numpy as np

from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.h5_io import write_recording_h5, verify_recording_h5
from ads1292_studio.events import EventMarker
from ads1292_studio.xlsx_io import write_recording_xlsx
from ads1292_studio.models import StreamSample
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, sha256_array
from scripts._xlsx_read import read_xlsx_semantic

SR = 500.0


def _samples(ch2: list[float], n: int) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(timestamp=round(i / SR, 6), ch1=10 + i, ch2=int(round(ch2[i])),
                     board_heart_rate=72, board_respiration_rate=18, status_byte=(i % 16))
        for i in range(n)
    )


def generate(root: Path) -> list[Path]:
    out = Path(root) / "files"
    out.mkdir(parents=True, exist_ok=True)
    signal = synthetic_ecg(50, SR, bpm=72.0)
    samples = _samples(signal, 50)
    written: list[Path] = []

    # --- live CSV: freeze header + first rows (text level) ---
    csv_path = out / "live_recording.csv"
    write_recording_csv(csv_path, samples)
    with csv_path.open() as fh:
        rows = list(csv.reader(fh))
    sidecar = out / "live_recording_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_csv_live", "name": "live_recording",
        "oracle": {"function": "ads1292_studio.csv_io.write_recording_csv"},
        "csv_header": rows[0],
        "csv_first_rows": rows[1:6],
        "row_count": len(rows) - 1,
        "tolerance": {"kind": "text"},
        "notes": "live CSV column order + names + value formatting frozen at text level",
    }, sidecar)
    written += [csv_path, sidecar]

    # --- HDF5: freeze sidecar (datasets/attrs/per-array sha256), NOT bytes ---
    h5_path = out / "recording.h5"
    write_recording_h5(h5_path, samples, sample_rate_hz=SR)
    datasets: dict[str, dict] = {}
    attrs: dict[str, str] = {}
    with h5py.File(h5_path, "r") as fh:
        def _visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                datasets[name] = {
                    "shape": list(obj.shape),
                    "dtype": str(obj.dtype),
                    "sha256": sha256_array(np.asarray(obj[()], dtype=float))
                        if np.issubdtype(obj.dtype, np.number) else "non-numeric",
                }
        fh.visititems(_visit)
        for key, value in fh.attrs.items():
            attrs[key] = str(value)
    verification = verify_recording_h5(h5_path)
    h5_sidecar = out / "recording_h5_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_hdf5", "name": "recording_h5",
        "oracle": {"function": "ads1292_studio.h5_io.write_recording_h5"},
        "artifact": "recording.h5",
        "datasets": datasets,
        "attrs": attrs,
        "verify_ok": bool(getattr(verification, "ok", verification)),
        "tolerance": {"kind": "structure"},
        "notes": "HDF5 schema + datasets + attrs + per-array sha256; byte-identity NOT required",
    }, h5_sidecar)
    written += [h5_path, h5_sidecar]

    # --- minimal XLSX semantic fixture: sheets + headers + event rows + data rows ---
    point_event = EventMarker(timestamp_seconds=0.020, label="touch", notes="point note", duration_seconds=0.0)
    interval_event = EventMarker(timestamp_seconds=0.040, label="motion", notes="range note", duration_seconds=0.030)
    xlsx_path = write_recording_xlsx(csv_path, events=(point_event, interval_event), sample_rate_hz=SR)
    if xlsx_path != out / "recording.xlsx":
        xlsx_path = xlsx_path.rename(out / "recording.xlsx")
    semantic = read_xlsx_semantic(xlsx_path)
    events_name, data_name = semantic["sheet_names"][0], semantic["sheet_names"][1]
    events_rows = semantic["sheets"][events_name]
    data_rows = semantic["sheets"][data_name]
    point_rows = [r for r in events_rows[1:] if r and r[-3] == "point"]
    interval_rows = [r for r in events_rows[1:] if r and r[-3] == "interval"]
    assert point_rows and interval_rows, "expected one point and one interval event row"
    xlsx_sidecar = out / "recording_xlsx_sidecar.json"
    dump_fixture({
        "schema_version": 1, "category": "file_xlsx", "name": "recording_xlsx",
        "oracle": {"function": "ads1292_studio.xlsx_io.write_recording_xlsx"},
        "artifact": "recording.xlsx",
        "sheet_names": semantic["sheet_names"],
        "events_header": events_rows[0],
        "point_event_row": point_rows[0],
        "interval_event_row": interval_rows[0],
        "data_header": data_rows[0],
        "data_first_row": data_rows[1],
        "data_last_row": data_rows[-1],
        "tolerance": {"kind": "semantic"},
        "notes": "XLSX semantic ONLY: sheet names + headers + 1 point + 1 interval event + first/last data row. No style/zip/byte equality.",
    }, xlsx_sidecar)
    written += [xlsx_path, xlsx_sidecar]
    return written
```

> Note: confirm the `H5Verification` attribute name (`.ok`) when implementing — `verify_recording_h5` returns an `H5Verification` dataclass (see `src/ads1292_studio/h5_io.py:149`). Adjust `getattr(verification, "ok", ...)` to the real field if it differs. **XLSX semantic fixture is now mandatory P-1 scope** (see above). Raw-CSV and recording-bundle sidecars are the only optional add-ons here: they follow the same sidecar shape; if deferred, log the gap in `findings.md` (P2 scope) rather than dropping silently.

- [ ] **Step 5: Run test to verify it passes**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_gen_file_fixtures.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Generate and commit**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -c "from pathlib import Path; from scripts.gen_file_fixtures import generate; generate(Path('tests/fixtures/golden'))"
git add scripts/_xlsx_read.py scripts/gen_file_fixtures.py tests/test_gen_file_fixtures.py tests/fixtures/golden/files
git commit -m "feat: P-1 file-format golden fixtures (CSV text + HDF5 sidecar + minimal XLSX semantic)"
```

---

### Task 10: Validator + faithful-reproduction pytest + C++ reader note

**Files:**
- Create: `scripts/validate_golden_fixtures.py`
- Create: `scripts/generate_golden_fixtures.py` (top-level aggregator)
- Create: `tests/test_golden_fixtures.py`
- Test: (the validator's own tests live in `tests/test_validate_golden_fixtures.py`)
- Create: `tests/test_validate_golden_fixtures.py`

**Interfaces:**
- Consumes: every `scripts/gen_*` module, `scripts.fixture_provenance`, `scripts.fixture_io`.
- Produces:
  - `scripts.generate_golden_fixtures.main(root: Path) -> None` — runs all generators + writes `oracle.json`.
  - `scripts.validate_golden_fixtures.validate_root(root: Path) -> list[str]` — returns a list of error strings (empty = valid).

- [ ] **Step 1: Write the failing test for the validator**

```python
# tests/test_validate_golden_fixtures.py
from pathlib import Path
from scripts.generate_golden_fixtures import main as generate_all
from scripts.validate_golden_fixtures import validate_root


def test_full_generation_validates_clean(tmp_path: Path):
    generate_all(tmp_path)
    errors = validate_root(tmp_path)
    assert errors == [], f"validator found problems: {errors}"


def test_missing_provenance_is_flagged(tmp_path: Path):
    generate_all(tmp_path)
    (tmp_path / "oracle.json").unlink()
    errors = validate_root(tmp_path)
    assert any("oracle.json" in e for e in errors)


def test_missing_tolerance_is_flagged(tmp_path: Path):
    generate_all(tmp_path)
    import json
    target = next((tmp_path / "dsp").glob("filtfilt_*.json"))
    obj = json.loads(target.read_text())
    obj.pop("tolerance", None)
    obj.pop("output_tolerances", None)
    target.write_text(json.dumps(obj))
    errors = validate_root(tmp_path)
    assert any("tolerance" in e for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_validate_golden_fixtures.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.generate_golden_fixtures'`

- [ ] **Step 3: Write the aggregator generator**

```python
# scripts/generate_golden_fixtures.py
from __future__ import annotations

from pathlib import Path

from scripts import (
    gen_device_fixtures, gen_dsp_fixtures, gen_rpeak_fixtures,
    gen_review_fixtures, gen_spectrum_fixtures, gen_file_fixtures,
)
from scripts.fixture_provenance import write_provenance

GENERATORS = (
    gen_device_fixtures.generate, gen_dsp_fixtures.generate, gen_rpeak_fixtures.generate,
    gen_review_fixtures.generate, gen_spectrum_fixtures.generate, gen_file_fixtures.generate,
)
COMMAND = "python -m scripts.generate_golden_fixtures"


def main(root: Path) -> None:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for generate in GENERATORS:
        generate(root)
    write_provenance(root, sample_rate_hz=500.0, generation_command=COMMAND)


if __name__ == "__main__":
    main(Path("tests/fixtures/golden"))
```

- [ ] **Step 4: Write the validator**

```python
# scripts/validate_golden_fixtures.py
from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.fixture_provenance import REQUIRED_PROVENANCE_KEYS
from scripts._xlsx_read import read_xlsx_semantic

# Two fixture shapes exist:
#  - "envelope" fixtures (device/dsp/rpeak/review/spectrum): need input + output.
#  - "file_*" sidecars (file_csv_live/file_hdf5/file_xlsx): flat, category-specific.
COMMON_KEYS = ("schema_version", "category", "name", "oracle")
ENVELOPE_KEYS = ("input", "output")
FILE_SIDECAR_KEYS = {
    "file_csv_live": ("csv_header", "csv_first_rows"),
    "file_hdf5": ("artifact", "datasets", "attrs"),
    "file_xlsx": ("artifact", "sheet_names", "events_header", "point_event_row",
                  "interval_event_row", "data_header", "data_first_row", "data_last_row"),
}


def validate_root(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []

    manifest_path = root / "oracle.json"
    if not manifest_path.exists():
        errors.append("missing provenance: oracle.json")
    else:
        manifest = json.loads(manifest_path.read_text())
        for key in REQUIRED_PROVENANCE_KEYS:
            if key not in manifest:
                errors.append(f"oracle.json missing key: {key}")

    for path in sorted(root.rglob("*.json")):
        if path.name == "oracle.json":
            continue
        obj = json.loads(path.read_text())
        rel = path.relative_to(root)
        category = obj.get("category", "")

        for key in COMMON_KEYS:
            if key not in obj:
                errors.append(f"{rel}: missing envelope key '{key}'")
        if not ("tolerance" in obj or "output_tolerances" in obj):
            errors.append(f"{rel}: missing tolerance / output_tolerances")

        if category in FILE_SIDECAR_KEYS:
            for key in FILE_SIDECAR_KEYS[category]:
                if key not in obj:
                    errors.append(f"{rel}: file sidecar missing '{key}'")
            if category == "file_xlsx":
                errors.extend(_validate_xlsx(path, obj, rel))
        else:
            for key in ENVELOPE_KEYS:
                if key not in obj:
                    errors.append(f"{rel}: missing envelope key '{key}'")
    return errors


def _validate_xlsx(sidecar_path: Path, obj: dict, rel: Path) -> list[str]:
    """Re-open the committed workbook and confirm the frozen semantics still hold."""
    artifact = sidecar_path.parent / obj["artifact"]
    if not artifact.exists():
        return [f"{rel}: xlsx artifact not found: {obj['artifact']}"]
    actual = read_xlsx_semantic(artifact)
    problems: list[str] = []
    if actual["sheet_names"] != obj["sheet_names"]:
        problems.append(f"{rel}: xlsx sheet names drifted")
    events_name, data_name = actual["sheet_names"][0], actual["sheet_names"][1]
    events_rows = actual["sheets"][events_name]
    data_rows = actual["sheets"][data_name]
    if events_rows[0] != obj["events_header"]:
        problems.append(f"{rel}: xlsx events header drifted")
    if data_rows[0] != obj["data_header"]:
        problems.append(f"{rel}: xlsx data header drifted")
    if data_rows[1] != obj["data_first_row"] or data_rows[-1] != obj["data_last_row"]:
        problems.append(f"{rel}: xlsx data first/last row drifted")
    if obj["point_event_row"] not in events_rows or obj["interval_event_row"] not in events_rows:
        problems.append(f"{rel}: xlsx event rows drifted")
    return problems


if __name__ == "__main__":
    problems = validate_root(Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/golden"))
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("all golden fixtures valid")
```

- [ ] **Step 5: Write the faithful-reproduction pytest**

```python
# tests/test_golden_fixtures.py
"""Guards the frozen fixtures against drift from the pinned Python oracle.

This is the P-1 acceptance test. It does NOT implement a C++ reader; it proves
the stored goldens are a faithful, reproducible capture of the current oracle.
A future C++/Catch2 reader will consume the same JSON envelopes (see
docs/superpowers/specs/2026-06-24-p1-golden-fixtures-design.md, "C++ reader
interface note").
"""
from pathlib import Path
import json

import numpy as np
import pytest

from scripts.validate_golden_fixtures import validate_root

ROOT = Path(__file__).resolve().parent / "fixtures" / "golden"


def test_committed_fixtures_pass_validation():
    assert validate_root(ROOT) == []


def test_device_stream_fixture_reproduces():
    from ads1292_studio.device import parse_stream_payload
    fx = json.loads((ROOT / "device_parser" / "stream_payload_nominal.json").read_text())
    payload = bytes.fromhex(fx["input"]["payload_hex"])
    samples = parse_stream_payload(payload, fx["input"]["start_timestamp"],
                                   fx["input"]["sample_rate_hz"], fx["input"]["start_index"])
    assert [s.ch1 for s in samples] == [row["ch1"] for row in fx["output"]["samples"]]


def test_dsp_filtfilt_fixture_reproduces_within_tolerance():
    from ads1292_studio.signal_processing import bandpass
    fx = json.loads((ROOT / "dsp" / "filtfilt_bandpass_long.json").read_text())
    recomputed = bandpass(fx["input"]["signal"], fx["input"]["sample_rate_hz"])
    expected = np.asarray(fx["output"]["filtered"], dtype=float)
    assert np.allclose(recomputed, expected, atol=fx["tolerance"]["value"])
```

- [ ] **Step 6: Run all tests to verify they pass**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_validate_golden_fixtures.py tests/test_golden_fixtures.py -v`
Expected: PASS (all)

- [ ] **Step 7: Regenerate the committed tree, then commit**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m scripts.generate_golden_fixtures
git add scripts/generate_golden_fixtures.py scripts/validate_golden_fixtures.py tests/test_validate_golden_fixtures.py tests/test_golden_fixtures.py tests/fixtures/golden/oracle.json
git commit -m "feat: P-1 golden fixture aggregator, validator, and drift-guard tests"
```

---

### Task 11: Determinism proof + acceptance pass

**Files:**
- Modify: `findings.md` (record what was frozen, what was deferred)

**Interfaces:**
- Consumes: everything above.
- Produces: a documented, green P-1 acceptance.

- [ ] **Step 1: Prove generation determinism (byte-identical re-run)**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m scripts.generate_golden_fixtures
git status --porcelain tests/fixtures/golden
```
Expected: **no JSON changes** under `tests/fixtures/golden` (the `.h5` binary may differ — that is allowed; its sidecar must not). If any `*.json` shows as modified, the generator is non-deterministic — fix float formatting / key ordering before proceeding.

- [ ] **Step 2: Run the full validator over the committed tree**

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m scripts.validate_golden_fixtures tests/fixtures/golden
```
Expected: `all golden fixtures valid`

> **XLSX acceptance is semantic only:** the validator re-opens `recording.xlsx` and checks sheet names + Events/Data headers + one point-event row + one interval-event row + first/last data row. It asserts **no binary equality, no style equality, no zip-entry equality**. Full XLSX writer parity and styling are P2/P7 scope (recorded in `findings.md`).

- [ ] **Step 3: Run the complete P-1 test set**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest tests/test_fixture_provenance.py tests/test_fixture_io.py tests/test_gen_device_fixtures.py tests/test_gen_dsp_fixtures.py tests/test_gen_rpeak_fixtures.py tests/test_gen_review_fixtures.py tests/test_gen_spectrum_fixtures.py tests/test_gen_file_fixtures.py tests/test_validate_golden_fixtures.py tests/test_golden_fixtures.py -v`
Expected: PASS (all)

- [ ] **Step 4: Confirm the existing suite still passes (no regressions)**

Run: `PYTHONPATH=src QT_QPA_PLATFORM=offscreen conda run -n sensor python -m pytest -q`
Expected: the prior 697 tests + the new P-1 tests all pass.

- [ ] **Step 5: Record outcome in findings.md and commit**

Append to `findings.md`: which categories were frozen (device, dsp, rpeak, review, spectrum, files), which sidecars were deferred (e.g. raw-CSV / XLSX / bundle if not done in Task 9), and the pinned oracle commit from `oracle.json`. Then:

```bash
git add findings.md
git commit -m "docs: record P-1 golden fixture acceptance and frozen oracle commit"
```

---

## Self-Review

**1. Spec coverage** (against the master spec's §6.1 P-1 asset list):
- stream/raw frame parser fixtures → Task 4 ✓
- live CSV fixture → Task 9 ✓ (raw CSV = optional same-shape add, log to findings if deferred)
- HDF5 fixture → Task 9 ✓
- XLSX semantic fixture → Task 9 ✓ **mandatory, semantic-only** (sheet names + headers + 1 point + 1 interval event + first/last data row; re-opened and checked by the validator). No style/zip/byte equality; full XLSX writer parity is P2/P7.
- ECG review fixture → Task 7 ✓
- R peak / HR / SNR / spectrum golden → Tasks 6, 7, 8 ✓
- bad frames / timeout / bad trailer → Task 4 ✓
- filtfilt / butter / iirnotch coeff + output (incl. short window) → Task 5 ✓
- oracle provenance manifest → Task 2 + Task 10 aggregator ✓
- validator (schema/hash/version/tolerance completeness) → Task 10 ✓
- C++/Catch2 reader as interface note only → Task 1 design doc + Task 10 docstring ✓

**2. Placeholder scan:** No "TBD/TODO/handle edge cases" — each step ships runnable code. The one forward-looking note (H5Verification field name) instructs verification against a cited source line, not a vague placeholder.

**3. Type consistency:** `generate(root: Path) -> list[Path]` is uniform across all `gen_*` modules; `validate_root(root) -> list[str]`; `main(root)` aggregator; `dump_fixture/load_fixture/floats/to_hex/sha256_array` names match across Tasks 3–10.

**Known follow-ups for the executor:**
- Verify `H5Verification` field name against `h5_io.py:149` (Task 9 note).
- Raw-CSV and recording-bundle sidecars are optional in P-1 (same sidecar pattern as HDF5). XLSX is **not** optional — it is mandatory semantic-only and is re-validated by the validator. If raw-CSV/bundle are deferred, record them in `findings.md` as P2 scope (Task 11 Step 5).
