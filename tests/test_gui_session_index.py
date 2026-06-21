from pathlib import Path

import numpy as np

from ads1292_studio.acquisition import build_acquisition_provenance, write_acquisition_json
from ads1292_studio.calibration import Calibration, write_calibration_json
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker, write_events_json
from ads1292_studio.gui_session_index import build_session_index_message
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol, write_protocol_json
from ads1292_studio.quality_gate import QualityGate, write_quality_gate_json
from ads1292_studio.session_index import export_session_index


def _samples() -> tuple[StreamSample, ...]:
    sample_rate_hz = 500.0
    t = np.arange(0, 7, 1 / sample_rate_hz)
    ch2 = 5 * np.sin(2 * np.pi * 1.0 * t)
    for peak in np.arange(0.5, 6.8, 0.58):
        ch2 += 420 * np.exp(-0.5 * ((t - peak) / 0.012) ** 2)
    return tuple(
        StreamSample(
            timestamp=index / sample_rate_hz,
            ch1=0,
            ch2=int(round(two)),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index, two in enumerate(ch2)
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


def _write_recording(root: Path, name: str, samples: tuple[StreamSample, ...]) -> Path:
    path = root / name
    write_recording_csv(path, samples)
    write_metadata_json(
        path.with_suffix(".json"),
        SessionMetadata(session_id=path.stem, electrode="MOTAC gel + Ag/AgCl"),
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
            name="gui-index-protocol",
            steps=(ProtocolStep(start_seconds=0.0, duration_seconds=1.0, label="baseline", instruction="sit still"),),
        ),
    )
    write_quality_gate_json(path.with_suffix(".quality-gate.json"), QualityGate(min_duration_seconds=1.0))


def test_build_session_index_message_includes_action_queue_counts(tmp_path: Path) -> None:
    ready = _write_recording(tmp_path, "ready.csv", _samples())
    _write_recording(tmp_path, "incomplete.csv", _samples())
    review = _write_recording(tmp_path, "review.csv", _review_samples())
    _write_complete_sidecars(
        ready,
        (
            EventMarker(timestamp_seconds=0.5, duration_seconds=2.0, label="baseline", notes="quiet"),
            EventMarker(timestamp_seconds=3.0, label="tap", notes="single tap"),
        ),
    )
    _write_complete_sidecars(
        review,
        (
            EventMarker(timestamp_seconds=1.0, duration_seconds=4.0, label="motion", notes="arm moved"),
        ),
    )
    export = export_session_index(tmp_path, out_dir=tmp_path / "index", title="GUI Session Index")

    message = build_session_index_message(export)

    assert "Indexed 3 recordings" in message
    assert str(export.html_path) in message
    assert "Package-ready: 1" in message
    assert "Incomplete records: 1" in message
    assert "Need signal review: 1" in message
    assert "Package record: 1" in message
    assert "Complete sidecars: 1" in message
    assert "Review signal: 1" in message
    assert "Annotated recordings: 2" in message
    assert "Event annotations: 3" in message
    assert "Interval annotations: 2" in message
    assert "Annotated seconds: 6.00" in message
    assert "Sidecar plan rows: 5" in message
    assert str(export.sidecar_plan_csv_path) in message
    assert str(export.sidecar_plan_html_path) in message
    assert "Sidecar template files: 5" in message
    assert str(export.sidecar_template_dir) in message
    assert "Apply sidecars script:" in message
    assert str(export.sidecar_apply_script_path) in message
