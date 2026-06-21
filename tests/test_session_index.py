from pathlib import Path

import numpy as np

from ads1292_studio.acquisition import (
    build_acquisition_provenance,
    finalize_acquisition_provenance,
    write_acquisition_json,
)
from ads1292_studio.calibration import Calibration, write_calibration_json
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker, write_events_csv, write_events_json
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol, write_protocol_json
from ads1292_studio.quality_gate import QualityGate, write_quality_gate_json
from ads1292_studio.session_index import export_session_index, scan_recording_directory


def _samples() -> tuple[StreamSample, ...]:
    sample_rate_hz = 500.0
    t = np.arange(0, 7, 1 / sample_rate_hz)
    ch1 = 10 * np.sin(2 * np.pi * 0.6 * t)
    ch2 = 5 * np.sin(2 * np.pi * 1.0 * t)
    for peak in np.arange(0.5, 6.8, 0.58):
        ch2 += 420 * np.exp(-0.5 * ((t - peak) / 0.012) ** 2)
    return tuple(
        StreamSample(
            timestamp=index / sample_rate_hz,
            ch1=int(round(one)),
            ch2=int(round(two)),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index, (one, two) in enumerate(zip(ch1, ch2))
    )


def _review_samples() -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(
            timestamp=index / 500.0,
            ch1=0,
            ch2=0,
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0x0F,
        )
        for index in range(1500)
    )


def _write_recording(
    root: Path,
    relative: str,
    electrode: str,
    samples: tuple[StreamSample, ...] | None = None,
) -> Path:
    path = root / relative
    write_recording_csv(path, samples or _samples())
    write_metadata_json(
        path.with_suffix(".json"),
        SessionMetadata(
            session_id=path.stem,
            subject_id="anonymous",
            electrode=electrode,
            montage="RA/LA/RL torso",
            operator="tester",
        ),
    )
    return path


def _write_complete_sidecars(path: Path, events: tuple[EventMarker, ...] | None = None) -> None:
    markers = events or (EventMarker(0.5, "baseline", "quiet"),)
    write_events_json(path.with_suffix(".events.json"), markers)
    write_calibration_json(path.with_suffix(".calibration.json"), Calibration(label="bench-cal"))
    write_acquisition_json(
        path.with_suffix(".acquisition.json"),
        build_acquisition_provenance(
            csv_path=path,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem-test",
            sample_rate_hz=500.0,
            calibration=Calibration(label="bench-cal"),
            live_calibration=None,
            started_at="2026-06-21T00:00:00",
        ),
    )
    write_protocol_json(
        path.with_suffix(".protocol.json"),
        TestProtocol(
            name="session-index-protocol",
            steps=(ProtocolStep(start_seconds=0.0, duration_seconds=1.0, label="baseline", instruction="sit still"),),
        ),
    )
    write_quality_gate_json(path.with_suffix(".quality-gate.json"), QualityGate(min_duration_seconds=1.0))


def test_scan_recording_directory_discovers_recordings_and_ignores_exports(tmp_path: Path) -> None:
    _write_recording(tmp_path, "baseline/control.csv", "commercial Ag/AgCl")
    _write_recording(tmp_path, "motac.csv", "MOTAC gel + Ag/AgCl")
    (tmp_path / "old-session-index.csv").write_text("not,a,recording\n")

    rows = scan_recording_directory(tmp_path)

    assert [row.relative_path for row in rows] == ["baseline/control.csv", "motac.csv"]
    assert [row.electrode for row in rows] == ["commercial Ag/AgCl", "MOTAC gel + Ag/AgCl"]
    assert all(row.ecg_source == "CH2" for row in rows)
    assert all(row.status == "usable" for row in rows)


def test_scan_recording_directory_reports_sidecar_completeness(tmp_path: Path) -> None:
    partial = _write_recording(tmp_path, "partial.csv", "commercial Ag/AgCl")
    complete = _write_recording(tmp_path, "complete.csv", "MOTAC gel + Ag/AgCl")
    _write_complete_sidecars(complete)

    rows = {row.session_id: row for row in scan_recording_directory(tmp_path)}

    assert rows["complete"].sidecar_status == "complete"
    assert rows["complete"].missing_sidecars == ""
    assert rows["partial"].sidecar_status == "missing"
    assert rows["partial"].missing_sidecars == "events;calibration;acquisition;protocol;quality_gate"


def test_scan_recording_directory_requires_acquisition_provenance_sidecar(tmp_path: Path) -> None:
    path = _write_recording(tmp_path, "missing-acquisition.csv", "MOTAC gel + Ag/AgCl")
    write_events_json(path.with_suffix(".events.json"), (EventMarker(0.5, "baseline", "quiet"),))
    write_calibration_json(path.with_suffix(".calibration.json"), Calibration(label="bench-cal"))
    write_protocol_json(
        path.with_suffix(".protocol.json"),
        TestProtocol(
            name="session-index-protocol",
            steps=(ProtocolStep(start_seconds=0.0, duration_seconds=1.0, label="baseline", instruction="sit still"),),
        ),
    )
    write_quality_gate_json(path.with_suffix(".quality-gate.json"), QualityGate(min_duration_seconds=1.0))

    rows = {row.session_id: row for row in scan_recording_directory(tmp_path)}

    assert rows["missing-acquisition"].sidecar_status == "missing"
    assert rows["missing-acquisition"].missing_sidecars == "acquisition"
    assert rows["missing-acquisition"].package_ready_status == "incomplete_record"


def test_scan_recording_directory_reports_package_ready_status(tmp_path: Path) -> None:
    ready = _write_recording(tmp_path, "ready.csv", "MOTAC gel + Ag/AgCl")
    incomplete = _write_recording(tmp_path, "incomplete.csv", "MOTAC gel + Ag/AgCl")
    review = _write_recording(tmp_path, "review.csv", "MOTAC gel + Ag/AgCl", samples=_review_samples())
    _write_complete_sidecars(ready)
    _write_complete_sidecars(review)

    rows = {row.session_id: row for row in scan_recording_directory(tmp_path)}

    assert rows["ready"].package_ready_status == "package_ready"
    assert rows["incomplete"].package_ready_status == "incomplete_record"
    assert rows["review"].package_ready_status == "needs_signal_review"


def test_scan_recording_directory_reports_next_action(tmp_path: Path) -> None:
    ready = _write_recording(tmp_path, "ready.csv", "MOTAC gel + Ag/AgCl")
    incomplete = _write_recording(tmp_path, "incomplete.csv", "MOTAC gel + Ag/AgCl")
    review = _write_recording(tmp_path, "review.csv", "MOTAC gel + Ag/AgCl", samples=_review_samples())
    _write_complete_sidecars(ready)
    _write_complete_sidecars(review)

    rows = {row.session_id: row for row in scan_recording_directory(tmp_path)}

    assert rows["ready"].next_action == "package_record"
    assert rows["incomplete"].next_action == "complete_sidecars"
    assert rows["review"].next_action == "review_signal"


def test_scan_recording_directory_summarizes_event_annotations(tmp_path: Path) -> None:
    marked = _write_recording(tmp_path, "marked.csv", "MOTAC gel + Ag/AgCl")
    _write_recording(tmp_path, "unmarked.csv", "MOTAC gel + Ag/AgCl")
    _write_complete_sidecars(
        marked,
        (
            EventMarker(timestamp_seconds=0.5, label="baseline", notes="quiet"),
            EventMarker(timestamp_seconds=2.0, duration_seconds=3.25, label="motion", notes="arm moved"),
            EventMarker(timestamp_seconds=6.0, label="motion", notes="tap"),
        ),
    )

    rows = {row.session_id: row for row in scan_recording_directory(tmp_path)}

    assert rows["marked"].event_count == 3
    assert rows["marked"].interval_event_count == 1
    assert rows["marked"].total_annotated_seconds == 3.25
    assert rows["marked"].event_labels == "baseline:1;motion:2"
    assert rows["unmarked"].event_count == 0
    assert rows["unmarked"].interval_event_count == 0
    assert rows["unmarked"].total_annotated_seconds == 0.0
    assert rows["unmarked"].event_labels == ""


def test_scan_recording_directory_uses_events_csv_when_json_is_missing(tmp_path: Path) -> None:
    marked = _write_recording(tmp_path, "marked-csv.csv", "MOTAC gel + Ag/AgCl")
    events = (
        EventMarker(timestamp_seconds=1.0, duration_seconds=2.5, label="deep breath", notes="inhale"),
    )
    write_events_csv(marked.with_suffix(".events.csv"), events)
    write_calibration_json(marked.with_suffix(".calibration.json"), Calibration(label="bench-cal"))
    write_acquisition_json(
        marked.with_suffix(".acquisition.json"),
        build_acquisition_provenance(
            csv_path=marked,
            acquisition_mode="live_stream",
            port="/dev/cu.usbmodem-test",
            sample_rate_hz=500.0,
            calibration=Calibration(label="bench-cal"),
            live_calibration=None,
            started_at="2026-06-21T00:00:00",
        ),
    )
    write_protocol_json(
        marked.with_suffix(".protocol.json"),
        TestProtocol(
            name="session-index-protocol",
            steps=(ProtocolStep(start_seconds=0.0, duration_seconds=1.0, label="baseline", instruction="sit still"),),
        ),
    )
    write_quality_gate_json(marked.with_suffix(".quality-gate.json"), QualityGate(min_duration_seconds=1.0))

    rows = {row.session_id: row for row in scan_recording_directory(tmp_path)}

    assert rows["marked-csv"].sidecar_status == "complete"
    assert rows["marked-csv"].missing_sidecars == ""
    assert rows["marked-csv"].event_count == 1
    assert rows["marked-csv"].interval_event_count == 1
    assert rows["marked-csv"].total_annotated_seconds == 2.5
    assert rows["marked-csv"].event_labels == "deep breath:1"


def test_export_session_index_writes_csv_and_html(tmp_path: Path) -> None:
    _write_recording(tmp_path, "control.csv", "commercial Ag/AgCl")
    motac = _write_recording(tmp_path, "motac.csv", "MOTAC gel + Ag/AgCl")
    _write_complete_sidecars(motac)
    out_dir = tmp_path / "index"

    export = export_session_index(tmp_path, out_dir=out_dir, title="MOTAC Session Library")

    assert export.csv_path.exists()
    assert export.html_path.exists()
    assert len(export.rows) == 2
    csv_text = export.csv_path.read_text()
    html = export.html_path.read_text()
    assert "relative_path,session_id,subject_id,electrode" in csv_text
    assert "commercial Ag/AgCl" in csv_text
    assert "sidecar_status,missing_sidecars" in csv_text
    assert "event_count,interval_event_count,total_annotated_seconds,event_labels" in csv_text
    assert "baseline:1" in csv_text
    assert "package_ready_status" in csv_text
    assert "next_action" in csv_text
    assert "package_ready" in csv_text
    assert "package_record" in csv_text
    assert "complete," in csv_text
    assert "MOTAC Session Library" in html
    assert "Usable recordings" in html
    assert "Sidecars" in html
    assert "Events" in html
    assert "baseline:1" in html
    assert "Package Ready" in html
    assert "Next Action" in html


def test_export_session_index_summarizes_package_readiness(tmp_path: Path) -> None:
    ready = _write_recording(tmp_path, "ready.csv", "MOTAC gel + Ag/AgCl")
    _write_recording(tmp_path, "incomplete.csv", "MOTAC gel + Ag/AgCl")
    review = _write_recording(tmp_path, "review.csv", "MOTAC gel + Ag/AgCl", samples=_review_samples())
    _write_complete_sidecars(ready)
    _write_complete_sidecars(review)

    export = export_session_index(tmp_path, out_dir=tmp_path / "index", title="Package Summary")

    assert export.summary.recordings == 3
    assert export.summary.package_ready == 1
    assert export.summary.incomplete_records == 1
    assert export.summary.needs_signal_review == 1
    assert export.summary.action_package_record == 1
    assert export.summary.action_complete_sidecars == 1
    assert export.summary.action_review_signal == 1
    html = export.html_path.read_text()
    assert "Package-ready recordings: 1" in html
    assert "Incomplete records: 1" in html
    assert "Need signal review: 1" in html
    assert "Next actions: package record 1 | complete sidecars 1 | review signal 1" in html


def test_export_session_index_summarizes_event_annotation_coverage(tmp_path: Path) -> None:
    baseline = _write_recording(tmp_path, "baseline.csv", "MOTAC gel + Ag/AgCl")
    movement = _write_recording(tmp_path, "movement.csv", "MOTAC gel + Ag/AgCl")
    _write_recording(tmp_path, "unmarked.csv", "MOTAC gel + Ag/AgCl")
    _write_complete_sidecars(
        baseline,
        (
            EventMarker(timestamp_seconds=0.5, duration_seconds=2.0, label="baseline", notes="quiet"),
        ),
    )
    _write_complete_sidecars(
        movement,
        (
            EventMarker(timestamp_seconds=1.0, duration_seconds=3.5, label="motion", notes="arm moved"),
            EventMarker(timestamp_seconds=6.0, label="tap", notes="single tap"),
        ),
    )

    export = export_session_index(tmp_path, out_dir=tmp_path / "index", title="Annotation Coverage")

    assert export.summary.annotated_recordings == 2
    assert export.summary.event_annotations == 3
    assert export.summary.interval_event_annotations == 2
    assert export.summary.total_annotated_seconds == 5.5
    html = export.html_path.read_text()
    assert "Annotated recordings: 2" in html
    assert "Event annotations: 3" in html
    assert "Interval annotations: 2" in html
    assert "Annotated seconds: 5.50" in html


def test_export_session_index_surfaces_acquisition_completion(tmp_path: Path) -> None:
    finalized = _write_recording(tmp_path, "finalized.csv", "MOTAC gel + Ag/AgCl")
    open_recording = _write_recording(tmp_path, "open.csv", "MOTAC gel + Ag/AgCl")
    _write_complete_sidecars(finalized)
    _write_complete_sidecars(open_recording)
    acquisition = build_acquisition_provenance(
        csv_path=finalized,
        acquisition_mode="live_stream",
        port="/dev/cu.usbmodem-test",
        sample_rate_hz=500.0,
        calibration=Calibration(label="bench-cal"),
        live_calibration=None,
        started_at="2026-06-21T00:00:00",
    )
    write_acquisition_json(
        finalized.with_suffix(".acquisition.json"),
        finalize_acquisition_provenance(
            acquisition,
            ended_at="2026-06-21T00:00:07",
            finalized_at="2026-06-21T00:00:08",
            sample_count=len(_samples()),
            first_timestamp_seconds=0.0,
            last_timestamp_seconds=6.998,
        ),
    )

    export = export_session_index(tmp_path, out_dir=tmp_path / "index", title="Completion Audit")
    rows = {row.session_id: row for row in export.rows}

    assert rows["finalized"].completion_status == "finalized"
    assert rows["finalized"].recorded_sample_count == len(_samples())
    assert rows["finalized"].recorded_span_seconds == 6.998
    assert rows["open"].completion_status == "open"
    assert rows["open"].recorded_sample_count == 0
    assert export.summary.finalized_recordings == 1
    assert export.summary.open_recordings == 1
    assert export.summary.unknown_completion_records == 0
    csv_text = export.csv_path.read_text()
    html = export.html_path.read_text()
    assert "completion_status,recorded_sample_count,recorded_span_seconds" in csv_text
    assert "finalized,3500,6.998" in csv_text
    assert "Completion" in html
    assert "Finalized recordings: 1" in html
    assert "Open/unfinalized recordings: 1" in html


def test_export_session_index_writes_sidecar_completion_plan(tmp_path: Path) -> None:
    partial = _write_recording(tmp_path, "partial.csv", "commercial Ag/AgCl")
    ready = _write_recording(tmp_path, "ready.csv", "MOTAC gel + Ag/AgCl")
    _write_complete_sidecars(ready)

    export = export_session_index(tmp_path, out_dir=tmp_path / "index", title="Completion Plan")

    assert export.sidecar_plan_csv_path.exists()
    assert export.sidecar_plan_html_path.exists()
    assert len(export.sidecar_plan_rows) == 5
    plan_text = export.sidecar_plan_csv_path.read_text()
    assert "relative_path,sidecar,target_path,template_path,suggested_action" in plan_text
    assert "partial.csv,events," in plan_text
    assert str(partial.with_suffix(".events.json")) in plan_text
    assert str(export.sidecar_template_dir / "partial.events.json") in plan_text
    assert "partial.csv,acquisition," in plan_text
    assert str(partial.with_suffix(".acquisition.json")) in plan_text
    assert str(export.sidecar_template_dir / "partial.acquisition.json") in plan_text
    assert "Create events sidecar" in plan_text
    assert "Create acquisition sidecar" in plan_text
    assert "quality_gate" in plan_text
    assert "ready.csv" not in plan_text
    html = export.sidecar_plan_html_path.read_text()
    assert "Sidecar Completion Plan" in html
    assert "partial.csv" in html
    assert "Template Path" in html
    assert "quality-gate.json" in html


def test_export_session_index_writes_sidecar_apply_script(tmp_path: Path) -> None:
    partial = _write_recording(tmp_path, "nested/partial.csv", "commercial Ag/AgCl")
    ready = _write_recording(tmp_path, "ready.csv", "MOTAC gel + Ag/AgCl")
    _write_complete_sidecars(ready)

    export = export_session_index(tmp_path, out_dir=tmp_path / "index", title="Apply Script")

    assert export.sidecar_apply_script_path.exists()
    script = export.sidecar_apply_script_path.read_text()
    assert script.startswith("#!/bin/sh\n")
    assert "Review generated sidecar templates before running this script." in script
    assert str(export.sidecar_template_dir / "nested" / "partial.events.json") in script
    assert str(partial.with_suffix(".events.json")) in script
    assert "cp -n" in script
    assert "ready.csv" not in script


def test_export_session_index_writes_sidecar_template_bundle(tmp_path: Path) -> None:
    partial = _write_recording(tmp_path, "partial.csv", "commercial Ag/AgCl")
    ready = _write_recording(tmp_path, "ready.csv", "MOTAC gel + Ag/AgCl")
    _write_complete_sidecars(ready)

    export = export_session_index(tmp_path, out_dir=tmp_path / "index", title="Template Bundle")

    assert export.sidecar_template_dir.exists()
    assert len(export.sidecar_template_paths) == 5
    template_names = {path.name for path in export.sidecar_template_paths}
    assert template_names == {
        "partial.events.json",
        "partial.calibration.json",
        "partial.acquisition.json",
        "partial.protocol.json",
        "partial.quality-gate.json",
    }
    assert not partial.with_suffix(".events.json").exists()
    acquisition_text = (export.sidecar_template_dir / "partial.acquisition.json").read_text()
    protocol_text = (export.sidecar_template_dir / "partial.protocol.json").read_text()
    gate_text = (export.sidecar_template_dir / "partial.quality-gate.json").read_text()
    assert "ads1292-acquisition-provenance-v1" in acquisition_text
    assert '"csv_name": "partial.csv"' in acquisition_text
    assert "csv_columns" in acquisition_text
    assert "MOTAC ECG validation" in protocol_text
    assert "min_contact_ok_percent" in gate_text
