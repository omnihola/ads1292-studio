from __future__ import annotations

from ads1292_studio.session_index import SessionIndexExport


def build_session_index_message(export: SessionIndexExport) -> str:
    summary = export.summary
    return "\n".join(
        [
            f"Indexed {summary.recordings} recordings:",
            str(export.html_path),
            "",
            f"Package-ready: {summary.package_ready}",
            f"Incomplete records: {summary.incomplete_records}",
            f"Need signal review: {summary.needs_signal_review}",
            "",
            f"Finalized recordings: {summary.finalized_recordings}",
            f"Open/unfinalized recordings: {summary.open_recordings}",
            f"Unknown completion: {summary.unknown_completion_records}",
            "",
            f"Completion audit pass: {summary.completion_audit_pass}",
            f"Completion audit fail: {summary.completion_audit_fail}",
            f"Completion audit pending: {summary.completion_audit_pending}",
            f"Completion audit unknown: {summary.completion_audit_unknown}",
            "",
            f"Package record: {summary.action_package_record}",
            f"Complete sidecars: {summary.action_complete_sidecars}",
            f"Review signal: {summary.action_review_signal}",
            "",
            f"Annotated recordings: {summary.annotated_recordings}",
            f"Event annotations: {summary.event_annotations}",
            f"Interval annotations: {summary.interval_event_annotations}",
            f"Annotated seconds: {summary.total_annotated_seconds:.2f}",
            "",
            f"Sidecar plan rows: {len(export.sidecar_plan_rows)}",
            str(export.sidecar_plan_csv_path),
            str(export.sidecar_plan_html_path),
            "",
            f"Sidecar template files: {len(export.sidecar_template_paths)}",
            str(export.sidecar_template_dir),
            "",
            "Apply sidecars script:",
            str(export.sidecar_apply_script_path),
            "",
            f"Recording manifest plan rows: {len(export.manifest_plan_rows)}",
            str(export.manifest_plan_csv_path),
            str(export.manifest_plan_html_path),
            "",
            "Apply recording manifests script:",
            str(export.manifest_apply_script_path),
        ]
    )
