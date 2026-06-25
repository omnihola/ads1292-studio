from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

from ads1292_studio import signal_processing as sp
from ads1292_studio import quality as q
from ads1292_studio.models import StreamSample
from scripts._fixture_signals import synthetic_ecg
from scripts.fixture_io import dump_fixture, floats

SR = 500.0
FLOAT_TOL = {"kind": "abs", "value": 1e-9}


def _stream_samples(ch2: list[float]) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(timestamp=i / SR, ch1=0, ch2=int(round(v)),
                     board_heart_rate=0, board_respiration_rate=0, status_byte=0)
        for i, v in enumerate(ch2)
    )


def generate(root: Path) -> list[Path]:
    out = Path(root) / "review"
    signal = synthetic_ecg(2500, SR, bpm=72.0)
    peaks = list(sp.detect_r_peaks(np.asarray(signal, dtype=float), SR))
    written: list[Path] = []

    hr = sp.heart_rate_summary(peaks, SR)
    written.append(_write(out / "hr_summary_clean_72bpm.json", {
        "schema_version": 1, "category": "hr_summary", "name": "hr_summary_clean_72bpm",
        "oracle": {"function": "ads1292_studio.signal_processing.heart_rate_summary"},
        "input": {"peaks": peaks, "sample_rate_hz": SR},
        "output": asdict(hr),
        "tolerance": FLOAT_TOL,
        "notes": "HR summary from frozen upstream peaks",
    }))

    pqrst = sp.pqrst_review(signal, peaks, SR)
    written.append(_write(out / "pqrst_clean_72bpm.json", {
        "schema_version": 1, "category": "pqrst_review", "name": "pqrst_clean_72bpm",
        "oracle": {"function": "ads1292_studio.signal_processing.pqrst_review"},
        "input": {"signal": floats(signal), "peaks": peaks, "sample_rate_hz": SR},
        "output": {
            "qrs_clear": pqrst.qrs_clear, "p_tentative": pqrst.p_tentative,
            "t_tentative": pqrst.t_tentative, "beats_used": pqrst.beats_used,
            "average_beat": floats(pqrst.average_beat), "time_ms": floats(pqrst.time_ms),
        },
        "output_tolerances": {"average_beat": {"kind": "abs", "value": 1e-6},
                              "time_ms": {"kind": "abs", "value": 1e-9}},
        "notes": "average-beat morphology + tentative P/T flags",
    }))

    samples = _stream_samples(signal)
    metrics = q.compute_quality_metrics(samples, SR, "Auto")
    written.append(_write(out / "quality_metrics_clean_72bpm.json", {
        "schema_version": 1, "category": "quality_metrics", "name": "quality_metrics_clean_72bpm",
        "oracle": {"function": "ads1292_studio.quality.compute_quality_metrics"},
        "input": {
            "ch2": [int(round(v)) for v in signal],
            "ch1": 0,
            "status_byte": 0,
            "sample_rate_hz": SR,
            "source": "Auto"
        },
        "output": asdict(metrics),
        "tolerance": FLOAT_TOL,
        "notes": "input rebuilds StreamSample(ch1=0, ch2=ch2[i], status_byte=0) per sample; ch2 is the integer-rounded ECG actually consumed by the oracle",
    }))

    snr = q.estimate_realtime_snr(np.asarray(signal, dtype=float), sample_rate_hz=SR)
    written.append(_write(out / "realtime_snr_clean_72bpm.json", {
        "schema_version": 1, "category": "realtime_snr", "name": "realtime_snr_clean_72bpm",
        "oracle": {"function": "ads1292_studio.quality.estimate_realtime_snr"},
        "input": {"values": floats(signal), "sample_rate_hz": SR},
        "output": asdict(snr),
        "tolerance": FLOAT_TOL,
        "notes": "lightweight realtime SNR: MAD-based noise RMS, p95-p5 peak-to-peak",
    }))
    return written


def _write(path: Path, payload: dict) -> Path:
    dump_fixture(payload, path)
    return path
