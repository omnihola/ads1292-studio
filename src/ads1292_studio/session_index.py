from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.metadata import SessionMetadata, read_metadata_json
from ads1292_studio.quality import compute_quality_metrics


@dataclass(frozen=True)
class SessionIndexRow:
    path: Path
    relative_path: str
    session_id: str
    subject_id: str
    electrode: str
    montage: str
    operator: str
    sample_count: int
    duration_seconds: float
    ecg_source: str
    contact_ok_percent: float
    r_peaks: int
    hr_median_bpm: float
    qrs_clear: bool
    quality_label: str
    status: str
    sidecar_status: str
    missing_sidecars: str
    package_ready_status: str


@dataclass(frozen=True)
class SessionIndexExport:
    csv_path: Path
    html_path: Path
    rows: tuple[SessionIndexRow, ...]


def scan_recording_directory(root: Path | str) -> tuple[SessionIndexRow, ...]:
    root_path = Path(root)
    rows = tuple(
        _row_for_csv(path, root_path)
        for path in sorted(root_path.rglob("*.csv"))
        if _looks_like_recording_csv(path)
    )
    return tuple(row for row in rows if row is not None)


def export_session_index(
    root: Path | str,
    out_dir: Path | str,
    title: str = "ADS1292 Session Index",
) -> SessionIndexExport:
    rows = scan_recording_directory(root)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = _slugify(title)
    csv_path = output / f"{stamp}-{slug}.csv"
    html_path = output / f"{stamp}-{slug}.html"
    _write_csv(csv_path, rows)
    html_path.write_text(_html(title, rows))
    return SessionIndexExport(csv_path=csv_path, html_path=html_path, rows=rows)


def _looks_like_recording_csv(path: Path) -> bool:
    if "session-index" in path.stem or path.stem.endswith("-groups"):
        return False
    try:
        with path.open(newline="") as handle:
            header = next(csv.reader(handle), [])
    except (OSError, StopIteration):
        return False
    fields = set(header)
    has_ch1 = bool({"ch1_counts", "ecg_counts"} & fields)
    has_ch2 = bool({"ch2_counts", "resp_counts"} & fields)
    return "timestamp" in fields and has_ch1 and has_ch2


def _row_for_csv(path: Path, root: Path) -> SessionIndexRow | None:
    try:
        recording = read_recording_csv(path)
    except (OSError, ValueError):
        return None
    if not recording.samples:
        return None
    metadata = _metadata_for(path)
    metrics = compute_quality_metrics(recording.samples, sample_rate_hz=recording.sample_rate_hz)
    sidecar_status, missing_sidecars = _sidecar_status(path)
    waveform_status = _status_for_quality(metrics.quality_label)
    return SessionIndexRow(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        session_id=metadata.session_id,
        subject_id=metadata.subject_id,
        electrode=metadata.electrode,
        montage=metadata.montage,
        operator=metadata.operator,
        sample_count=metrics.sample_count,
        duration_seconds=metrics.duration_seconds,
        ecg_source=metrics.ecg_source,
        contact_ok_percent=metrics.contact_ok_percent,
        r_peaks=metrics.r_peaks,
        hr_median_bpm=metrics.hr_median_bpm,
        qrs_clear=metrics.qrs_clear,
        quality_label=metrics.quality_label,
        status=waveform_status,
        sidecar_status=sidecar_status,
        missing_sidecars=missing_sidecars,
        package_ready_status=_package_ready_status(waveform_status, sidecar_status),
    )


def _metadata_for(csv_path: Path) -> SessionMetadata:
    sidecar = csv_path.with_suffix(".json")
    if sidecar.exists():
        return read_metadata_json(sidecar)
    return SessionMetadata(session_id=csv_path.stem).normalized()


def _status_for_quality(quality_label: str) -> str:
    if quality_label in {"Good ECG/QRS", "Usable ECG/QRS"}:
        return "usable"
    return "review"


def _sidecar_status(csv_path: Path) -> tuple[str, str]:
    expected = {
        "metadata": csv_path.with_suffix(".json"),
        "events": csv_path.with_suffix(".events.json"),
        "calibration": csv_path.with_suffix(".calibration.json"),
        "protocol": csv_path.with_suffix(".protocol.json"),
        "quality_gate": csv_path.with_suffix(".quality-gate.json"),
    }
    missing = tuple(name for name, path in expected.items() if not path.exists())
    return ("complete", "") if not missing else ("missing", ";".join(missing))


def _package_ready_status(waveform_status: str, sidecar_status: str) -> str:
    if sidecar_status != "complete":
        return "incomplete_record"
    if waveform_status != "usable":
        return "needs_signal_review"
    return "package_ready"


def _write_csv(path: Path, rows: tuple[SessionIndexRow, ...]) -> None:
    columns = [
        "relative_path",
        "session_id",
        "subject_id",
        "electrode",
        "montage",
        "operator",
        "sample_count",
        "duration_seconds",
        "ecg_source",
        "contact_ok_percent",
        "r_peaks",
        "hr_median_bpm",
        "qrs_clear",
        "quality_label",
        "status",
        "sidecar_status",
        "missing_sidecars",
        "package_ready_status",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in columns})


def _html(title: str, rows: tuple[SessionIndexRow, ...]) -> str:
    usable = sum(1 for row in rows if row.status == "usable")
    header = [
        "File",
        "Session",
        "Electrode",
        "Montage",
        "Source",
        "Contact OK",
        "R peaks",
        "HR median",
        "Quality",
        "Status",
        "Sidecars",
        "Missing Sidecars",
        "Package Ready",
    ]
    body = []
    for row in rows:
        values = [
            row.relative_path,
            row.session_id,
            row.electrode,
            row.montage,
            row.ecg_source,
            f"{row.contact_ok_percent:.2f}%",
            str(row.r_peaks),
            f"{row.hr_median_bpm:.1f}",
            row.quality_label,
            row.status,
            row.sidecar_status,
            row.missing_sidecars,
            row.package_ready_status,
        ]
        body.append("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in values) + "</tr>")
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>{escape(title)}</h1>
  <p>Recordings: {len(rows)} | Usable recordings: {usable}</p>
  <table>
    <tr>{"".join(f"<th>{escape(item)}</th>" for item in header)}</tr>
    {"".join(body)}
  </table>
</body>
</html>
"""


def _slugify(text: str) -> str:
    clean = "".join(char.lower() if char.isalnum() else "-" for char in text)
    return "-".join(part for part in clean.split("-") if part)[:48] or "ads1292-session-index"
