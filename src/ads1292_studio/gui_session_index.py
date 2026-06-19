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
            f"Package record: {summary.action_package_record}",
            f"Complete sidecars: {summary.action_complete_sidecars}",
            f"Review signal: {summary.action_review_signal}",
        ]
    )
