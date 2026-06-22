"""Free-disk-space check used to warn before a recording fills the disk."""
from __future__ import annotations

from pathlib import Path

from ads1292_studio.disk_space import MIN_FREE_BYTES, free_space_status


def test_reports_ok_when_plenty_free(tmp_path: Path) -> None:
    status = free_space_status(tmp_path, min_free_bytes=1)
    assert status.ok is True
    assert status.free_bytes > 0


def test_reports_low_when_below_threshold(tmp_path: Path) -> None:
    # require an absurd amount so it always reports low
    status = free_space_status(tmp_path, min_free_bytes=10**18)
    assert status.ok is False
    assert status.free_mb >= 0


def test_missing_path_walks_up_to_existing_parent(tmp_path: Path) -> None:
    # a not-yet-created recording dir must still resolve to a real filesystem
    status = free_space_status(tmp_path / "ECG" / "live", min_free_bytes=1)
    assert status.ok is True


def test_default_threshold_is_sensible() -> None:
    assert MIN_FREE_BYTES >= 50 * 1024 * 1024  # at least ~50 MB headroom
