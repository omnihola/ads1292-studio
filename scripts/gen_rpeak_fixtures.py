from __future__ import annotations

from pathlib import Path

import numpy as np

from ads1292_studio import signal_processing as sp
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, floats

SR = 500.0


def _chain(signal: list[float]) -> dict:
    arr = np.asarray(signal, dtype=float)
    filtered = sp.bandpass(arr, SR)
    centered = filtered - np.median(filtered)
    scale = float(np.std(centered))
    prominence = max(20.0, scale * 0.45)
    positive = float(np.max(centered))
    negative = abs(float(np.min(centered)))
    polarity = "positive" if positive >= negative else "negative"
    peaks = sp.detect_r_peaks(arr, SR)
    return {
        "filtered": floats(filtered),
        "centered": floats(centered),
        "scale_std": scale,
        "prominence": prominence,
        "distance": int(0.35 * SR),
        "polarity": polarity,
        "peaks": [int(p) for p in peaks],
    }


def generate(root: Path) -> list[Path]:
    out = Path(root) / "rpeak"
    cases = {
        "rpeak_chain_clean_72bpm": synthetic_ecg(2500, SR, bpm=72.0),
        "rpeak_chain_fast_110bpm": synthetic_ecg(2500, SR, bpm=110.0),
        "rpeak_chain_short_below_sr": synthetic_ecg(300, SR),  # < sample_rate -> empty peaks
    }
    written: list[Path] = []
    for name, signal in cases.items():
        chain = _chain(signal)
        written.append(_write(out / f"{name}.json", {
            "schema_version": 1, "category": "rpeak_chain", "name": name,
            "oracle": {"function": "ads1292_studio.signal_processing.detect_r_peaks"},
            "input": {"signal": floats(signal), "sample_rate_hz": SR},
            "output": chain,
            "output_tolerances": {
                "filtered": {"kind": "abs", "value": 1e-6},
                "centered": {"kind": "abs", "value": 1e-6},
                "scale_std": {"kind": "abs", "value": 1e-9},
                "prominence": {"kind": "abs", "value": 1e-9},
                "peaks": {"kind": "exact"},
            },
            "notes": "full R-peak chain: bandpass -> centered -> prominence/polarity -> find_peaks",
        }))
    return written


def _write(path: Path, payload: dict) -> Path:
    dump_fixture(payload, path)
    return path
