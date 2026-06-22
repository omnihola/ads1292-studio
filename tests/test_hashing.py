"""Streaming file hashing must equal the one-shot hash, with bounded memory."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ads1292_studio.hashing import sha256_file


def test_sha256_file_matches_oneshot(tmp_path: Path) -> None:
    data = b"ads1292" * 100_000  # ~700 KB, multiple chunks
    f = tmp_path / "blob.bin"
    f.write_bytes(data)
    assert sha256_file(f) == hashlib.sha256(data).hexdigest()


def test_sha256_file_empty(tmp_path: Path) -> None:
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    assert sha256_file(f) == hashlib.sha256(b"").hexdigest()
