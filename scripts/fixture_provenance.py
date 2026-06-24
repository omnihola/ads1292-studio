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
