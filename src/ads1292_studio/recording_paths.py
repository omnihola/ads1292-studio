from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def recording_csv_path(
    *,
    started_at: datetime,
    acquisition_mode: Any,
    root: Path | str | None = None,
) -> Path:
    stamp = started_at.strftime("%Y-%m-%d-%H%M%S-%f")
    is_raw = _mode_text(acquisition_mode).startswith("raw")
    mode_folder = "raw" if is_raw else "live"
    suffix = "ads1292-raw" if is_raw else "ads1292-studio"
    base = Path.home() / "Documents" / "ECG" if root is None else Path(root)
    return base / mode_folder / f"{stamp}-{suffix}.csv"


def _mode_text(value: Any) -> str:
    return str(getattr(value, "value", value)).strip().lower()
