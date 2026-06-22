"""Streaming file hashing — bounded memory for large recordings."""
from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_BYTES = 1 << 20  # 1 MiB


def sha256_file(path: Path | str, chunk_bytes: int = _CHUNK_BYTES) -> str:
    """Return the hex SHA-256 of a file, read in chunks (no full load)."""
    digest = hashlib.sha256()
    with open(Path(path), "rb") as handle:
        for block in iter(lambda: handle.read(chunk_bytes), b""):
            digest.update(block)
    return digest.hexdigest()
