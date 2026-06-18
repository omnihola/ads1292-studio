from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ads1292-studio-matplotlib"))

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib.figure import Figure

from ads1292_studio.models import StreamSample
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.quality import QualityMetrics, compute_quality_metrics
from ads1292_studio.signal_processing import bandpass, detect_r_peaks, pqrst_review


@dataclass(frozen=True)
class ReportExport:
    html_path: Path
    ecg_png_path: Path
    pqrst_png_path: Path
    metrics: QualityMetrics


def export_review_report(
    samples: tuple[StreamSample, ...] | list[StreamSample],
    out_dir: Path | str,
    title: str = "ADS1292 Studio Review",
    sample_rate_hz: float = 500.0,
    source: str = "Auto",
    metadata: SessionMetadata | None = None,
) -> ReportExport:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    metrics = compute_quality_metrics(tuple(samples), sample_rate_hz=sample_rate_hz, source=source)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = _slugify(title)
    ecg_png = output / f"{stamp}-{slug}-ecg.png"
    pqrst_png = output / f"{stamp}-{slug}-pqrst.png"
    html_path = output / f"{stamp}-{slug}.html"
    _write_ecg_png(tuple(samples), ecg_png, metrics, sample_rate_hz)
    _write_pqrst_png(tuple(samples), pqrst_png, metrics, sample_rate_hz)
    html_path.write_text(_html(title, metrics, ecg_png.name, pqrst_png.name, metadata))
    return ReportExport(html_path, ecg_png, pqrst_png, metrics)


def _slugify(text: str) -> str:
    clean = "".join(char.lower() if char.isalnum() else "-" for char in text)
    return "-".join(part for part in clean.split("-") if part)[:48] or "ads1292-review"


def _selected_channel(samples: tuple[StreamSample, ...], source: str) -> np.ndarray:
    if source == "CH2":
        return np.array([sample.ch2 for sample in samples], dtype=float)
    return np.array([sample.ch1 for sample in samples], dtype=float)


def _other_channel(samples: tuple[StreamSample, ...], source: str) -> np.ndarray:
    if source == "CH2":
        return np.array([sample.ch1 for sample in samples], dtype=float)
    return np.array([sample.ch2 for sample in samples], dtype=float)


def _write_ecg_png(
    samples: tuple[StreamSample, ...],
    path: Path,
    metrics: QualityMetrics,
    sample_rate_hz: float,
) -> None:
    ecg_raw = _selected_channel(samples, metrics.ecg_source)
    other_raw = _other_channel(samples, metrics.ecg_source)
    ecg = bandpass(ecg_raw, sample_rate_hz)
    other = bandpass(other_raw, sample_rate_hz)
    peaks = detect_r_peaks(ecg_raw, sample_rate_hz)
    x = np.arange(ecg.size) / sample_rate_hz
    fig = Figure(figsize=(12, 7), dpi=160)
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212, sharex=ax1)
    ax1.plot(x, ecg, lw=0.8)
    if peaks:
        ax1.plot(x[list(peaks)], ecg[list(peaks)], "r.", ms=4)
    ax1.set_title(f"ECG source {metrics.ecg_source} | HR {metrics.hr_median_bpm:.1f} bpm | {metrics.quality_label}")
    ax1.set_ylabel("Filtered counts")
    ax1.grid(True, alpha=0.25)
    ax2.plot(x, other, lw=0.8)
    ax2.set_title("Other channel")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Filtered counts")
    ax2.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)


def _write_pqrst_png(
    samples: tuple[StreamSample, ...],
    path: Path,
    metrics: QualityMetrics,
    sample_rate_hz: float,
) -> None:
    ecg_raw = _selected_channel(samples, metrics.ecg_source)
    peaks = detect_r_peaks(ecg_raw, sample_rate_hz)
    review = pqrst_review(ecg_raw, peaks, sample_rate_hz)
    fig = Figure(figsize=(10, 5), dpi=160)
    ax = fig.add_subplot(111)
    if review.average_beat:
        ax.plot(review.time_ms, review.average_beat, lw=2, label="average beat")
        ax.axvline(0, color="r", linestyle="--", lw=1, label="R")
        ax.axvspan(-220, -80, color="green", alpha=0.08, label="P search")
        ax.axvspan(120, 380, color="orange", alpha=0.08, label="T search")
        ax.legend(loc="upper right")
    ax.set_title(f"PQRST review | QRS={review.qrs_clear} | P={review.p_tentative} | T={review.t_tentative}")
    ax.set_xlabel("Time relative to R peak (ms)")
    ax.set_ylabel("Filtered counts")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)


def _html(
    title: str,
    metrics: QualityMetrics,
    ecg_png: str,
    pqrst_png: str,
    metadata: SessionMetadata | None,
) -> str:
    rows = [
        ("Quality", metrics.quality_label),
        ("ECG source", metrics.ecg_source),
        ("Samples", str(metrics.sample_count)),
        ("Duration", f"{metrics.duration_seconds:.2f} s"),
        ("Contact OK", f"{metrics.contact_ok_percent:.2f}%"),
        ("Lead-off bad samples", str(metrics.lead_off_bad_samples)),
        ("R peaks", str(metrics.r_peaks)),
        ("Median HR", f"{metrics.hr_median_bpm:.1f} bpm"),
        ("HR range", f"{metrics.hr_min_bpm:.1f}-{metrics.hr_max_bpm:.1f} bpm"),
        ("QRS clear", str(metrics.qrs_clear)),
        ("P wave", "tentative" if metrics.p_tentative else "not reliable"),
        ("T wave", "tentative" if metrics.t_tentative else "not reliable"),
        ("CH1 score", f"{metrics.score_ch1:.2f}"),
        ("CH2 score", f"{metrics.score_ch2:.2f}"),
    ]
    table = "\n".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in rows)
    metadata_html = ""
    if metadata is not None:
        meta = metadata.normalized()
        meta_rows = [
            ("Session ID", meta.session_id),
            ("Subject ID", meta.subject_id),
            ("Electrode", meta.electrode),
            ("Montage", meta.montage),
            ("Operator", meta.operator),
            ("Notes", meta.notes),
        ]
        metadata_table = "\n".join(
            f"<tr><th>{escape(key)}</th><td>{escape(value)}</td></tr>" for key, value in meta_rows
        )
        metadata_html = f"<h2>Session Metadata</h2><table>{metadata_table}</table>"
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; color: #1f2937; }}
    h1 {{ margin-bottom: 4px; }}
    .sub {{ color: #6b7280; margin-bottom: 24px; }}
    table {{ border-collapse: collapse; margin: 16px 0 28px; min-width: 420px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px 10px; text-align: left; }}
    th {{ background: #f3f4f6; }}
    img {{ max-width: 100%; border: 1px solid #e5e7eb; margin: 12px 0 24px; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <div class=\"sub\">Generated by ADS1292 Studio. Research use only; not diagnostic medical software.</div>
  {metadata_html}
  <h2>Signal Quality</h2>
  <table>{table}</table>
  <h2>ECG Review</h2>
  <img src=\"{escape(ecg_png)}\" alt=\"ECG review plot\">
  <h2>PQRST Review</h2>
  <img src=\"{escape(pqrst_png)}\" alt=\"PQRST review plot\">
</body>
</html>
"""
