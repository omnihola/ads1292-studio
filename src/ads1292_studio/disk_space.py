"""Free-disk-space check to guard recordings against a full disk.

A long ECG capture writes continuously; running out of space mid-recording
would truncate/lose data. We warn before Start when free space is low.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

# ~200 MB headroom: live CSV is ~70 MB/hour at 500 Hz; this leaves margin.
MIN_FREE_BYTES = 200 * 1024 * 1024


@dataclass(frozen=True)
class FreeSpaceStatus:
    ok: bool
    free_bytes: int
    min_free_bytes: int

    @property
    def free_mb(self) -> float:
        return self.free_bytes / (1024 * 1024)


def free_space_status(path: Path | str, min_free_bytes: int = MIN_FREE_BYTES) -> FreeSpaceStatus:
    """Report free space at ``path`` (walking up to an existing parent)."""
    target = Path(path)
    while not target.exists() and target != target.parent:
        target = target.parent
    try:
        free = shutil.disk_usage(target).free
    except OSError:
        # if we can't measure, don't block the user
        return FreeSpaceStatus(ok=True, free_bytes=-1, min_free_bytes=min_free_bytes)
    return FreeSpaceStatus(ok=free >= min_free_bytes, free_bytes=int(free), min_free_bytes=min_free_bytes)
