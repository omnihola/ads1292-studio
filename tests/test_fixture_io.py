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
