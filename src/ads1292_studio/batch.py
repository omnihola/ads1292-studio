from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from ads1292_studio.matplotlib_runtime import configure_matplotlib_cache

configure_matplotlib_cache()

import matplotlib

matplotlib.use("Agg")

from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.metadata import SessionMetadata, read_metadata_json
from ads1292_studio.plot_theme import PLOT_TRACE_COLORS, new_export_figure, style_export_axes
from ads1292_studio.quality import compute_quality_metrics
from ads1292_studio.recording_bundle import (
    is_recording_bundle_path,
    metadata_from_bundle,
    read_recording_bundle,
    recording_bundle_path,
)


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
class BatchGroupSummary:
    electrode: str
    recordings: int
    usable_recordings: int
    usable_percent: float
    mean_duration_seconds: float
    mean_contact_ok_percent: float
    mean_r_peaks: float
    mean_hr_median_bpm: float


@dataclass(frozen=True)
class BatchExport:
    csv_path: Path
    group_csv_path: Path
    html_path: Path
    png_path: Path
    rows: tuple[BatchRow, ...]
    group_summaries: tuple[BatchGroupSummary, ...]


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


def group_recordings_by_electrode(rows: tuple[BatchRow, ...] | list[BatchRow]) -> tuple[BatchGroupSummary, ...]:
    grouped: dict[str, list[BatchRow]] = {}
    for row in rows:
        grouped.setdefault(row.electrode, []).append(row)
    summaries: list[BatchGroupSummary] = []
    for electrode in sorted(grouped):
        items = grouped[electrode]
        recordings = len(items)
        usable = sum(1 for item in items if item.quality_label in {"Good ECG/QRS", "Usable ECG/QRS"})
        summaries.append(
            BatchGroupSummary(
                electrode=electrode,
                recordings=recordings,
                usable_recordings=usable,
                usable_percent=round(100.0 * usable / recordings, 2),
                mean_duration_seconds=_mean(item.duration_seconds for item in items),
                mean_contact_ok_percent=_mean(item.contact_ok_percent for item in items),
                mean_r_peaks=_mean(item.r_peaks for item in items),
                mean_hr_median_bpm=_mean(item.hr_median_bpm for item in items),
            )
        )
    return tuple(summaries)


def export_batch_summary(
    paths: list[Path] | tuple[Path, ...],
    out_dir: Path | str,
    title: str = "ADS1292 Batch Summary",
) -> BatchExport:
    rows = aggregate_recordings(tuple(Path(path) for path in paths))
    group_summaries = group_recordings_by_electrode(rows)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = _slugify(title)
    csv_path = output / f"{stamp}-{slug}.csv"
    group_csv_path = output / f"{stamp}-{slug}-groups.csv"
    html_path = output / f"{stamp}-{slug}.html"
    png_path = output / f"{stamp}-{slug}.png"
    _write_csv(csv_path, rows)
    _write_group_csv(group_csv_path, group_summaries)
    _write_png(png_path, rows, title)
    html_path.write_text(_html(title, rows, group_summaries, png_path.name))
    return BatchExport(csv_path, group_csv_path, html_path, png_path, rows, group_summaries)


def _metadata_for(csv_path: Path) -> SessionMetadata:
    bundle_path = recording_bundle_path(csv_path)
    if is_recording_bundle_path(bundle_path):
        return metadata_from_bundle(read_recording_bundle(bundle_path))
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


def _write_group_csv(path: Path, groups: tuple[BatchGroupSummary, ...]) -> None:
    columns = [
        "electrode",
        "recordings",
        "usable_recordings",
        "usable_percent",
        "mean_duration_seconds",
        "mean_contact_ok_percent",
        "mean_r_peaks",
        "mean_hr_median_bpm",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for group in groups:
            writer.writerow({column: getattr(group, column) for column in columns})


def _write_png(path: Path, rows: tuple[BatchRow, ...], title: str) -> None:
    fig = new_export_figure(figsize=(11, 6), dpi=160)
    ax_hr = fig.add_subplot(211)
    ax_contact = fig.add_subplot(212)
    labels = [row.session_id for row in rows]
    x = list(range(len(rows)))
    hr = [row.hr_median_bpm for row in rows]
    contact = [row.contact_ok_percent for row in rows]
    ax_hr.bar(x, hr, color=PLOT_TRACE_COLORS["ecg"], alpha=0.9)
    ax_hr.set_ylabel("Median HR (bpm)")
    ax_hr.set_title(title)
    ax_hr.set_xticks(x, labels, rotation=20, ha="right")
    ax_contact.bar(x, contact, color=PLOT_TRACE_COLORS["contact"], alpha=0.9)
    ax_contact.set_ylabel("Contact OK (%)")
    ax_contact.set_ylim(0, 105)
    ax_contact.set_xticks(x, labels, rotation=20, ha="right")
    style_export_axes((ax_hr, ax_contact))
    fig.tight_layout()
    fig.savefig(path)


def _html(
    title: str,
    rows: tuple[BatchRow, ...],
    group_summaries: tuple[BatchGroupSummary, ...],
    png_name: str,
) -> str:
    group_header = [
        "Electrode",
        "Recordings",
        "Usable",
        "Usable %",
        "Mean Contact OK",
        "Mean R peaks",
        "Mean HR",
        "Mean Duration",
    ]
    group_body = []
    for group in group_summaries:
        values = [
            group.electrode,
            str(group.recordings),
            str(group.usable_recordings),
            f"{group.usable_percent:.1f}%",
            f"{group.mean_contact_ok_percent:.2f}%",
            f"{group.mean_r_peaks:.1f}",
            f"{group.mean_hr_median_bpm:.1f}",
            f"{group.mean_duration_seconds:.2f} s",
        ]
        group_body.append("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in values) + "</tr>")
    group_head = "".join(f"<th>{escape(item)}</th>" for item in group_header)
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
  <h2>Group Summary</h2>
  <table><thead><tr>{group_head}</tr></thead><tbody>{''.join(group_body)}</tbody></table>
  <h2>Recording Details</h2>
  <table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>
</body>
</html>
"""


def _mean(values) -> float:
    items = [float(value) for value in values]
    if not items:
        return 0.0
    return round(sum(items) / len(items), 2)
