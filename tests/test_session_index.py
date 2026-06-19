from pathlib import Path

import numpy as np

from ads1292_studio.calibration import Calibration, write_calibration_json
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker, write_events_json
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


def _write_complete_sidecars(path: Path) -> None:
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
    assert rows["partial"].missing_sidecars == "events;calibration;protocol;quality_gate"


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
    assert "package_ready_status" in csv_text
    assert "next_action" in csv_text
    assert "package_ready" in csv_text
    assert "package_record" in csv_text
    assert "complete," in csv_text
    assert "MOTAC Session Library" in html
    assert "Usable recordings" in html
    assert "Sidecars" in html
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
