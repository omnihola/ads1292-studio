from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from html import escape
import os
from pathlib import Path
import tempfile

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ads1292-studio-matplotlib"))

import matplotlib

matplotlib.use("Agg")
from matplotlib.figure import Figure

from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.metadata import SessionMetadata, read_metadata_json
from ads1292_studio.quality import compute_quality_metrics


@dataclass(frozen=True)
class BatchRow:
    path: Path
    session_id: str
    subject_id: str
    electrode: str
    montage: str
    sample_count: int
    duration_seconds: float
    ecg_source: str
    contact_ok_percent: float
    r_peaks: int
    hr_median_bpm: float
    qrs_clear: bool
    p_tentative: bool
    t_tentative: bool
    quality_label: str


@dataclass(frozen=True)
class BatchExport:
    csv_path: Path
    html_path: Path
    png_path: Path
    rows: tuple[BatchRow, ...]


def aggregate_recordings(paths: list[Path] | tuple[Path, ...]) -> tuple[BatchRow, ...]:
    rows: list[BatchRow] = []
    for path in paths:
        csv_path = Path(path)
        recording = read_recording_csv(csv_path)
        metadata = _metadata_for(csv_path)
        metrics = compute_quality_metrics(recording.samples, sample_rate_hz=recording.sample_rate_hz)
        rows.append(
            BatchRow(
                path=csv_path,
                session_id=metadata.session_id,
                subject_id=metadata.subject_id,
                electrode=metadata.electrode,
                montage=metadata.montage,
                sample_count=metrics.sample_count,
                duration_seconds=metrics.duration_seconds,
                ecg_source=metrics.ecg_source,
                contact_ok_percent=metrics.contact_ok_percent,
                r_peaks=metrics.r_peaks,
                hr_median_bpm=metrics.hr_median_bpm,
                qrs_clear=metrics.qrs_clear,
                p_tentative=metrics.p_tentative,
                t_tentative=metrics.t_tentative,
                quality_label=metrics.quality_label,
            )
        )
    return tuple(rows)


def export_batch_summary(
    paths: list[Path] | tuple[Path, ...],
    out_dir: Path | str,
    title: str = "ADS1292 Batch Summary",
) -> BatchExport:
    rows = aggregate_recordings(tuple(Path(path) for path in paths))
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = _slugify(title)
    csv_path = output / f"{stamp}-{slug}.csv"
    html_path = output / f"{stamp}-{slug}.html"
    png_path = output / f"{stamp}-{slug}.png"
    _write_csv(csv_path, rows)
    _write_png(png_path, rows, title)
    html_path.write_text(_html(title, rows, png_path.name))
    return BatchExport(csv_path, html_path, png_path, rows)


def _metadata_for(csv_path: Path) -> SessionMetadata:
    sidecar = csv_path.with_suffix(".json")
    if sidecar.exists():
        return read_metadata_json(sidecar)
    return SessionMetadata(session_id=csv_path.stem).normalized()


def _slugify(text: str) -> str:
    clean = "".join(char.lower() if char.isalnum() else "-" for char in text)
    return "-".join(part for part in clean.split("-") if part)[:48] or "ads1292-batch"


def _write_csv(path: Path, rows: tuple[BatchRow, ...]) -> None:
    columns = [
        "path",
        "session_id",
        "subject_id",
        "electrode",
        "montage",
        "sample_count",
        "duration_seconds",
        "ecg_source",
        "contact_ok_percent",
        "r_peaks",
        "hr_median_bpm",
        "qrs_clear",
        "p_tentative",
        "t_tentative",
        "quality_label",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in columns})


def _write_png(path: Path, rows: tuple[BatchRow, ...], title: str) -> None:
    fig = Figure(figsize=(11, 6), dpi=160)
    ax_hr = fig.add_subplot(211)
    ax_contact = fig.add_subplot(212)
    labels = [row.session_id for row in rows]
    x = list(range(len(rows)))
    hr = [row.hr_median_bpm for row in rows]
    contact = [row.contact_ok_percent for row in rows]
    ax_hr.bar(x, hr, color="#2563eb")
    ax_hr.set_ylabel("Median HR (bpm)")
    ax_hr.set_title(title)
    ax_hr.set_xticks(x, labels, rotation=20, ha="right")
    ax_hr.grid(True, axis="y", alpha=0.25)
    ax_contact.bar(x, contact, color="#059669")
    ax_contact.set_ylabel("Contact OK (%)")
    ax_contact.set_ylim(0, 105)
    ax_contact.set_xticks(x, labels, rotation=20, ha="right")
    ax_contact.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)


def _html(title: str, rows: tuple[BatchRow, ...], png_name: str) -> str:
    header = [
        "Session",
        "Subject",
        "Electrode",
        "Montage",
        "Source",
        "Contact OK",
        "R peaks",
        "HR median",
        "QRS",
        "P",
        "T",
        "Quality",
        "File",
    ]
    body = []
    for row in rows:
        values = [
            row.session_id,
            row.subject_id,
            row.electrode,
            row.montage,
            row.ecg_source,
            f"{row.contact_ok_percent:.2f}%",
            str(row.r_peaks),
            f"{row.hr_median_bpm:.1f}",
            str(row.qrs_clear),
            "tentative" if row.p_tentative else "not reliable",
            "tentative" if row.t_tentative else "not reliable",
            row.quality_label,
            str(row.path),
        ]
        body.append("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in values) + "</tr>")
    head = "".join(f"<th>{escape(item)}</th>" for item in header)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 7px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f4f6; }}
    img {{ max-width: 100%; border: 1px solid #e5e7eb; margin: 16px 0 24px; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p>Generated by ADS1292 Studio. Research use only; not diagnostic medical software.</p>
  <img src=\"{escape(png_name)}\" alt=\"Batch summary chart\">
  <table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>
</body>
</html>
"""
