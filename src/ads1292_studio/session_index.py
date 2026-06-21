from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from shlex import quote

from ads1292_studio.acquisition import build_acquisition_provenance, read_acquisition_json, write_acquisition_json
from ads1292_studio.calibration import calibration_template, write_calibration_json
from ads1292_studio.csv_io import read_recording_csv
from ads1292_studio.events import EventMarker, event_template, read_events_csv, read_events_json, write_events_json
from ads1292_studio.metadata import SessionMetadata, read_metadata_json, write_metadata_json
from ads1292_studio.protocol import protocol_template, write_protocol_json
from ads1292_studio.quality import compute_quality_metrics
from ads1292_studio.quality_gate import quality_gate_template, write_quality_gate_json
from ads1292_studio.recording_manifest import verify_recording_manifest


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
    completion_status: str
    recorded_sample_count: int
    recorded_span_seconds: float
    completion_audit: str
    recorded_sample_count_delta: int
    recorded_span_delta_seconds: float
    ecg_source: str
    contact_ok_percent: float
    r_peaks: int
    hr_median_bpm: float
    qrs_clear: bool
    quality_label: str
    status: str
    sidecar_status: str
    missing_sidecars: str
    event_count: int
    interval_event_count: int
    total_annotated_seconds: float
    event_labels: str
    recording_manifest_status: str
    recording_manifest_failures: str
    package_ready_status: str
    next_action: str


@dataclass(frozen=True)
class SessionIndexSummary:
    recordings: int
    usable_recordings: int
    package_ready: int
    incomplete_records: int
    needs_signal_review: int
    finalized_recordings: int
    open_recordings: int
    unknown_completion_records: int
    completion_audit_pass: int
    completion_audit_fail: int
    completion_audit_pending: int
    completion_audit_unknown: int
    recording_manifest_pass: int
    recording_manifest_fail: int
    recording_manifest_missing: int
    recording_manifest_unknown: int
    annotated_recordings: int
    event_annotations: int
    interval_event_annotations: int
    total_annotated_seconds: float
    action_package_record: int
    action_complete_sidecars: int
    action_review_signal: int


@dataclass(frozen=True)
class EventAnnotationSummary:
    count: int = 0
    interval_count: int = 0
    total_annotated_seconds: float = 0.0
    labels: str = ""


@dataclass(frozen=True)
class AcquisitionCompletionSummary:
    status: str = "unknown"
    sample_count: int = 0
    span_seconds: float = 0.0


@dataclass(frozen=True)
class SidecarPlanRow:
    relative_path: str
    sidecar: str
    target_path: Path
    template_path: Path
    suggested_action: str


@dataclass(frozen=True)
class SessionIndexExport:
    csv_path: Path
    html_path: Path
    sidecar_plan_csv_path: Path
    sidecar_plan_html_path: Path
    sidecar_template_dir: Path
    sidecar_apply_script_path: Path
    rows: tuple[SessionIndexRow, ...]
    summary: SessionIndexSummary
    sidecar_plan_rows: tuple[SidecarPlanRow, ...]
    sidecar_template_paths: tuple[Path, ...]


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
    summary = summarize_rows(rows)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = _slugify(title)
    csv_path = output / f"{stamp}-{slug}.csv"
    html_path = output / f"{stamp}-{slug}.html"
    sidecar_plan_csv_path = output / f"{stamp}-{slug}-sidecar-plan.csv"
    sidecar_plan_html_path = output / f"{stamp}-{slug}-sidecar-plan.html"
    sidecar_template_dir = output / f"{stamp}-{slug}-sidecar-templates"
    sidecar_apply_script_path = output / f"{stamp}-{slug}-apply-sidecars.sh"
    sidecar_plan_rows = build_sidecar_completion_plan(rows, sidecar_template_dir)
    _write_csv(csv_path, rows)
    html_path.write_text(_html(title, rows, summary))
    _write_sidecar_plan_csv(sidecar_plan_csv_path, sidecar_plan_rows)
    sidecar_plan_html_path.write_text(_sidecar_plan_html(title, sidecar_plan_rows))
    sidecar_template_paths = write_sidecar_template_bundle(sidecar_template_dir, rows)
    write_sidecar_apply_script(sidecar_apply_script_path, sidecar_plan_rows)
    return SessionIndexExport(
        csv_path=csv_path,
        html_path=html_path,
        sidecar_plan_csv_path=sidecar_plan_csv_path,
        sidecar_plan_html_path=sidecar_plan_html_path,
        sidecar_template_dir=sidecar_template_dir,
        sidecar_apply_script_path=sidecar_apply_script_path,
        rows=rows,
        summary=summary,
        sidecar_plan_rows=sidecar_plan_rows,
        sidecar_template_paths=sidecar_template_paths,
    )


def write_sidecar_apply_script(path: Path | str, rows: tuple[SidecarPlanRow, ...]) -> Path:
    script_path = Path(path)
    lines = [
        "#!/bin/sh",
        "set -eu",
        "",
        "# Generated by ADS1292 Studio.",
        "# Review generated sidecar templates before running this script.",
        "# Existing target sidecars are left untouched by cp -n.",
        "",
    ]
    if not rows:
        lines.append("echo 'No missing sidecars to apply.'")
    for row in rows:
        template_path = row.template_path.resolve()
        target_path = row.target_path.resolve()
        lines.extend(
            [
                f"# {row.relative_path}: {row.sidecar}",
                f"mkdir -p {quote(str(target_path.parent))}",
                f"cp -n {quote(str(template_path))} {quote(str(target_path))}",
                "",
            ]
        )
    script_path.write_text("\n".join(lines) + "\n")
    script_path.chmod(0o755)
    return script_path


def build_sidecar_completion_plan(
    rows: tuple[SessionIndexRow, ...],
    template_dir: Path | str,
) -> tuple[SidecarPlanRow, ...]:
    output = Path(template_dir)
    return tuple(
        SidecarPlanRow(
            relative_path=row.relative_path,
            sidecar=sidecar,
            target_path=_expected_sidecar_path(row.path, sidecar),
            template_path=_template_path_for(output, row, sidecar),
            suggested_action=f"Create {_sidecar_label(sidecar)} sidecar",
        )
        for row in rows
        for sidecar in row.missing_sidecars.split(";")
        if sidecar
    )


def write_sidecar_template_bundle(template_dir: Path | str, rows: tuple[SessionIndexRow, ...]) -> tuple[Path, ...]:
    output = Path(template_dir)
    written: list[Path] = []
    for row in rows:
        for sidecar in row.missing_sidecars.split(";"):
            if not sidecar:
                continue
            path = _template_path_for(output, row, sidecar)
            _write_sidecar_template(path, row, sidecar)
            written.append(path)
    return tuple(written)


def summarize_rows(rows: tuple[SessionIndexRow, ...]) -> SessionIndexSummary:
    return SessionIndexSummary(
        recordings=len(rows),
        usable_recordings=sum(1 for row in rows if row.status == "usable"),
        package_ready=sum(1 for row in rows if row.package_ready_status == "package_ready"),
        incomplete_records=sum(1 for row in rows if row.package_ready_status == "incomplete_record"),
        needs_signal_review=sum(1 for row in rows if row.package_ready_status == "needs_signal_review"),
        finalized_recordings=sum(1 for row in rows if row.completion_status == "finalized"),
        open_recordings=sum(1 for row in rows if row.completion_status == "open"),
        unknown_completion_records=sum(1 for row in rows if row.completion_status == "unknown"),
        completion_audit_pass=sum(1 for row in rows if row.completion_audit == "pass"),
        completion_audit_fail=sum(1 for row in rows if row.completion_audit == "fail"),
        completion_audit_pending=sum(1 for row in rows if row.completion_audit == "pending"),
        completion_audit_unknown=sum(1 for row in rows if row.completion_audit == "unknown"),
        recording_manifest_pass=sum(1 for row in rows if row.recording_manifest_status == "pass"),
        recording_manifest_fail=sum(1 for row in rows if row.recording_manifest_status == "fail"),
        recording_manifest_missing=sum(1 for row in rows if row.recording_manifest_status == "missing"),
        recording_manifest_unknown=sum(1 for row in rows if row.recording_manifest_status == "unknown"),
        annotated_recordings=sum(1 for row in rows if row.event_count > 0),
        event_annotations=sum(row.event_count for row in rows),
        interval_event_annotations=sum(row.interval_event_count for row in rows),
        total_annotated_seconds=round(sum(row.total_annotated_seconds for row in rows), 6),
        action_package_record=sum(1 for row in rows if row.next_action == "package_record"),
        action_complete_sidecars=sum(1 for row in rows if row.next_action == "complete_sidecars"),
        action_review_signal=sum(1 for row in rows if row.next_action == "review_signal"),
    )


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
    event_summary = _event_summary_for(path)
    completion = _completion_summary_for(path)
    audit, count_delta, span_delta = _completion_audit(
        completion,
        actual_sample_count=metrics.sample_count,
        actual_span_seconds=metrics.duration_seconds,
    )
    manifest_status, manifest_failures = _recording_manifest_audit(path)
    waveform_status = _status_for_quality(metrics.quality_label)
    package_ready_status = _package_ready_status(waveform_status, sidecar_status)
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
        completion_status=completion.status,
        recorded_sample_count=completion.sample_count,
        recorded_span_seconds=completion.span_seconds,
        completion_audit=audit,
        recorded_sample_count_delta=count_delta,
        recorded_span_delta_seconds=span_delta,
        ecg_source=metrics.ecg_source,
        contact_ok_percent=metrics.contact_ok_percent,
        r_peaks=metrics.r_peaks,
        hr_median_bpm=metrics.hr_median_bpm,
        qrs_clear=metrics.qrs_clear,
        quality_label=metrics.quality_label,
        status=waveform_status,
        sidecar_status=sidecar_status,
        missing_sidecars=missing_sidecars,
        event_count=event_summary.count,
        interval_event_count=event_summary.interval_count,
        total_annotated_seconds=event_summary.total_annotated_seconds,
        event_labels=event_summary.labels,
        recording_manifest_status=manifest_status,
        recording_manifest_failures=manifest_failures,
        package_ready_status=package_ready_status,
        next_action=_next_action(package_ready_status),
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
    expected = (
        ("metadata", (csv_path.with_suffix(".json"),)),
        ("events", (csv_path.with_suffix(".events.json"), csv_path.with_suffix(".events.csv"))),
        ("calibration", (csv_path.with_suffix(".calibration.json"),)),
        ("acquisition", (csv_path.with_suffix(".acquisition.json"),)),
        ("protocol", (csv_path.with_suffix(".protocol.json"),)),
        ("quality_gate", (csv_path.with_suffix(".quality-gate.json"),)),
    )
    missing = tuple(name for name, paths in expected if not any(path.exists() for path in paths))
    return ("complete", "") if not missing else ("missing", ";".join(missing))


def _event_summary_for(csv_path: Path) -> EventAnnotationSummary:
    events_json = csv_path.with_suffix(".events.json")
    events_csv = csv_path.with_suffix(".events.csv")
    if events_json.exists():
        return _summarize_events(read_events_json(events_json))
    if events_csv.exists():
        return _summarize_events(read_events_csv(events_csv))
    return EventAnnotationSummary()


def _completion_summary_for(csv_path: Path) -> AcquisitionCompletionSummary:
    acquisition_path = csv_path.with_suffix(".acquisition.json")
    if not acquisition_path.exists():
        return AcquisitionCompletionSummary()
    try:
        completion = read_acquisition_json(acquisition_path).completion
    except (OSError, ValueError, TypeError):
        return AcquisitionCompletionSummary()
    status = str(completion.get("status", "unknown")).strip() or "unknown"
    if status not in {"finalized", "open"}:
        status = "unknown"
    return AcquisitionCompletionSummary(
        status=status,
        sample_count=max(0, int(float(completion.get("sample_count", 0) or 0))),
        span_seconds=round(float(completion.get("sample_span_seconds", 0.0) or 0.0), 6),
    )


def _completion_audit(
    completion: AcquisitionCompletionSummary,
    *,
    actual_sample_count: int,
    actual_span_seconds: float,
) -> tuple[str, int, float]:
    if completion.status == "open":
        return "pending", 0, 0.0
    if completion.status != "finalized":
        return "unknown", 0, 0.0
    count_delta = int(completion.sample_count) - int(actual_sample_count)
    span_delta = round(float(completion.span_seconds) - float(actual_span_seconds), 6)
    if count_delta == 0 and abs(span_delta) <= 0.001:
        return "pass", count_delta, span_delta
    return "fail", count_delta, span_delta


def _recording_manifest_audit(csv_path: Path) -> tuple[str, str]:
    manifest_path = csv_path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        return "missing", ""
    try:
        result = verify_recording_manifest(manifest_path)
    except Exception as exc:
        return "unknown", str(exc)
    if result.ok:
        return "pass", ""
    return "fail", ";".join(result.failures)


def _summarize_events(events: tuple[EventMarker, ...]) -> EventAnnotationSummary:
    labels: dict[str, int] = {}
    interval_count = 0
    total_annotated_seconds = 0.0
    for event in events:
        marker = event.normalized()
        labels[marker.label] = labels.get(marker.label, 0) + 1
        if marker.duration_seconds > 0:
            interval_count += 1
            total_annotated_seconds += marker.duration_seconds
    label_text = ";".join(f"{label}:{labels[label]}" for label in sorted(labels))
    return EventAnnotationSummary(
        count=len(events),
        interval_count=interval_count,
        total_annotated_seconds=round(total_annotated_seconds, 6),
        labels=label_text,
    )


def _expected_sidecar_path(csv_path: Path, sidecar: str) -> Path:
    if sidecar == "metadata":
        return csv_path.with_suffix(".json")
    if sidecar == "events":
        return csv_path.with_suffix(".events.json")
    if sidecar == "calibration":
        return csv_path.with_suffix(".calibration.json")
    if sidecar == "acquisition":
        return csv_path.with_suffix(".acquisition.json")
    if sidecar == "protocol":
        return csv_path.with_suffix(".protocol.json")
    if sidecar == "quality_gate":
        return csv_path.with_suffix(".quality-gate.json")
    return csv_path.with_suffix(f".{sidecar}.json")


def _sidecar_label(sidecar: str) -> str:
    return sidecar.replace("_", " ")


def _template_path_for(template_dir: Path, row: SessionIndexRow, sidecar: str) -> Path:
    target_name = _expected_sidecar_path(row.path, sidecar).name
    parent = Path(row.relative_path).parent
    if str(parent) == ".":
        return template_dir / target_name
    return template_dir / parent / target_name


def _write_sidecar_template(path: Path, row: SessionIndexRow, sidecar: str) -> None:
    if sidecar == "metadata":
        write_metadata_json(
            path,
            SessionMetadata(
                session_id=row.session_id,
                subject_id=row.subject_id,
                electrode=row.electrode,
                montage=row.montage,
                operator=row.operator,
                notes="Review and complete this generated metadata sidecar before packaging.",
            ),
        )
        return
    if sidecar == "events":
        write_events_json(path, event_template())
        return
    if sidecar == "calibration":
        write_calibration_json(path, calibration_template())
        return
    if sidecar == "acquisition":
        write_acquisition_json(path, _acquisition_template(row))
        return
    if sidecar == "protocol":
        write_protocol_json(path, protocol_template())
        return
    if sidecar == "quality_gate":
        write_quality_gate_json(path, quality_gate_template())


def _acquisition_template(row: SessionIndexRow):
    return build_acquisition_provenance(
        csv_path=row.path,
        acquisition_mode=_acquisition_mode_for_csv(row.path),
        port="review-required",
        sample_rate_hz=500.0,
        calibration=calibration_template(),
        live_calibration=None,
        started_at="review-required",
    )


def _acquisition_mode_for_csv(path: Path) -> str:
    try:
        with path.open(newline="") as handle:
            header = next(csv.reader(handle), [])
    except (OSError, StopIteration):
        return "live_stream"
    fields = set(header)
    if {"ch1_raw24", "ch2_raw24"} & fields or "raw_lsb_uv_per_count" in fields:
        return "raw_adc_24bit"
    return "live_stream"


def _package_ready_status(waveform_status: str, sidecar_status: str) -> str:
    if sidecar_status != "complete":
        return "incomplete_record"
    if waveform_status != "usable":
        return "needs_signal_review"
    return "package_ready"


def _next_action(package_ready_status: str) -> str:
    if package_ready_status == "package_ready":
        return "package_record"
    if package_ready_status == "needs_signal_review":
        return "review_signal"
    return "complete_sidecars"


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
        "completion_status",
        "recorded_sample_count",
        "recorded_span_seconds",
        "completion_audit",
        "recorded_sample_count_delta",
        "recorded_span_delta_seconds",
        "ecg_source",
        "contact_ok_percent",
        "r_peaks",
        "hr_median_bpm",
        "qrs_clear",
        "quality_label",
        "status",
        "sidecar_status",
        "missing_sidecars",
        "event_count",
        "interval_event_count",
        "total_annotated_seconds",
        "event_labels",
        "recording_manifest_status",
        "recording_manifest_failures",
        "package_ready_status",
        "next_action",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: getattr(row, column) for column in columns})


def _write_sidecar_plan_csv(path: Path, rows: tuple[SidecarPlanRow, ...]) -> None:
    columns = ["relative_path", "sidecar", "target_path", "template_path", "suggested_action"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "relative_path": row.relative_path,
                    "sidecar": row.sidecar,
                    "target_path": str(row.target_path),
                    "template_path": str(row.template_path),
                    "suggested_action": row.suggested_action,
                }
            )


def _html(title: str, rows: tuple[SessionIndexRow, ...], summary: SessionIndexSummary) -> str:
    header = [
        "File",
        "Session",
        "Electrode",
        "Montage",
        "Completion",
        "Recorded Samples",
        "Recorded Span",
        "Completion Audit",
        "Recorded Sample Delta",
        "Recorded Span Delta",
        "Source",
        "Contact OK",
        "R peaks",
        "HR median",
        "Quality",
        "Status",
        "Sidecars",
        "Missing Sidecars",
        "Events",
        "Interval Events",
        "Annotated Seconds",
        "Event Labels",
        "Manifest",
        "Manifest Failures",
        "Package Ready",
        "Next Action",
    ]
    body = []
    for row in rows:
        values = [
            row.relative_path,
            row.session_id,
            row.electrode,
            row.montage,
            row.completion_status,
            str(row.recorded_sample_count),
            f"{row.recorded_span_seconds:.6g}",
            row.completion_audit,
            str(row.recorded_sample_count_delta),
            f"{row.recorded_span_delta_seconds:.6g}",
            row.ecg_source,
            f"{row.contact_ok_percent:.2f}%",
            str(row.r_peaks),
            f"{row.hr_median_bpm:.1f}",
            row.quality_label,
            row.status,
            row.sidecar_status,
            row.missing_sidecars,
            str(row.event_count),
            str(row.interval_event_count),
            f"{row.total_annotated_seconds:.2f}",
            row.event_labels,
            row.recording_manifest_status,
            row.recording_manifest_failures,
            row.package_ready_status,
            row.next_action,
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
  <p>Recordings: {summary.recordings} | Usable recordings: {summary.usable_recordings}</p>
  <p>Package-ready recordings: {summary.package_ready} | Incomplete records: {summary.incomplete_records} | Need signal review: {summary.needs_signal_review}</p>
  <p>Finalized recordings: {summary.finalized_recordings} | Open/unfinalized recordings: {summary.open_recordings} | Unknown completion: {summary.unknown_completion_records}</p>
  <p>Completion audit: pass {summary.completion_audit_pass} | fail {summary.completion_audit_fail} | pending {summary.completion_audit_pending} | unknown {summary.completion_audit_unknown}</p>
  <p>Manifest audit: pass {summary.recording_manifest_pass} | fail {summary.recording_manifest_fail} | missing {summary.recording_manifest_missing} | unknown {summary.recording_manifest_unknown}</p>
  <p>Annotated recordings: {summary.annotated_recordings} | Event annotations: {summary.event_annotations} | Interval annotations: {summary.interval_event_annotations} | Annotated seconds: {summary.total_annotated_seconds:.2f}</p>
  <p>Next actions: package record {summary.action_package_record} | complete sidecars {summary.action_complete_sidecars} | review signal {summary.action_review_signal}</p>
  <table>
    <tr>{"".join(f"<th>{escape(item)}</th>" for item in header)}</tr>
    {"".join(body)}
  </table>
</body>
</html>
"""


def _sidecar_plan_html(title: str, rows: tuple[SidecarPlanRow, ...]) -> str:
    body = []
    for row in rows:
        values = [row.relative_path, row.sidecar, str(row.target_path), str(row.template_path), row.suggested_action]
        body.append("<tr>" + "".join(f"<td>{escape(value)}</td>" for value in values) + "</tr>")
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{escape(title)} Sidecar Completion Plan</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>{escape(title)} Sidecar Completion Plan</h1>
  <p>Missing sidecar tasks: {len(rows)}</p>
  <table>
    <tr><th>File</th><th>Sidecar</th><th>Target Path</th><th>Template Path</th><th>Suggested Action</th></tr>
    {"".join(body)}
  </table>
</body>
</html>
"""


def _slugify(text: str) -> str:
    clean = "".join(char.lower() if char.isalnum() else "-" for char in text)
    return "-".join(part for part in clean.split("-") if part)[:48] or "ads1292-session-index"
