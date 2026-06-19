from __future__ import annotations

import os
from pathlib import Path
import tempfile


MATPLOTLIB_CACHE_DIR_NAME = "ads1292-studio-matplotlib"


def _ensure_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_path = path / ".write-test"
        test_path.write_text("ok")
        test_path.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def configure_matplotlib_cache() -> Path:
    configured = os.environ.get("MPLCONFIGDIR")
    if configured:
        configured_path = Path(configured).expanduser()
        if _ensure_writable_dir(configured_path):
            return configured_path

    cache_path = Path(tempfile.gettempdir()) / MATPLOTLIB_CACHE_DIR_NAME
    if not _ensure_writable_dir(cache_path):
        cache_path = Path(tempfile.gettempdir())
    os.environ["MPLCONFIGDIR"] = str(cache_path)
    return cache_path
