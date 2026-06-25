from __future__ import annotations

from pathlib import Path

from ads1292_studio.spectrum import build_spectrum_analysis
from ads1292_studio.models import StreamSample
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, floats

SR = 500.0


def _samples(ch2: list[float]) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(timestamp=i / SR, ch1=0, ch2=int(round(v)),
                     board_heart_rate=0, board_respiration_rate=0, status_byte=0)
        for i, v in enumerate(ch2)
    )


def generate(root: Path) -> list[Path]:
    out = Path(root) / "spectrum"
    signal = synthetic_ecg(2048, SR, bpm=72.0)
    analysis = build_spectrum_analysis(_samples(signal), source="CH2",
                                       sample_rate_hz=SR, max_frequency_hz=60.0, histogram_bins=48)
    path = out / "spectrum_clean_72bpm_ch2.json"
    dump_fixture({
        "schema_version": 1, "category": "spectrum", "name": "spectrum_clean_72bpm_ch2",
        "oracle": {"function": "ads1292_studio.spectrum.build_spectrum_analysis"},
        "input": {"ch2": floats(signal), "source": "CH2", "sample_rate_hz": SR,
                  "max_frequency_hz": 60.0, "histogram_bins": 48},
        "output": {
            "ecg_frequency_hz": floats(analysis.ecg_frequency_hz),
            "ecg_power": floats(analysis.ecg_power),
            "histogram_counts": [int(c) for c in analysis.histogram_counts],
            "histogram_bin_edges": floats(analysis.histogram_bin_edges),
        },
        "output_tolerances": {
            "ecg_frequency_hz": {"kind": "abs", "value": 1e-9},
            "ecg_power": {"kind": "rel", "value": 1e-9},
            "histogram_counts": {"kind": "exact"},
            "histogram_bin_edges": {"kind": "abs", "value": 1e-9},
        },
        "notes": "Hann-windowed rfft power + amplitude histogram",
    }, path)
    return [path]
