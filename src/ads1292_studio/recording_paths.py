from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def recording_csv_path(
    *,
    started_at: datetime,
    acquisition_mode: Any,
    root: Path | str = Path("recordings"),
) -> Path:
    stamp = started_at.strftime("%Y-%m-%d-%H%M%S-%f")
    suffix = "ads1292-raw" if _mode_text(acquisition_mode).startswith("raw") else "ads1292-studio"
    return Path(root) / f"{stamp}-{suffix}.csv"


def _mode_text(value: Any) -> str:
    return str(getattr(value, "value", value)).strip().lower()
