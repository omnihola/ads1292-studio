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
