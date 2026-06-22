"""Round-trip tests for the canonical HDF5 recording container.

The .h5 is the single source of truth: raw sample arrays as datasets plus the
full metadata bundle as a JSON blob, with per-array SHA-256 integrity hashes.
XLSX/JSON/CSV are derived on demand from it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("h5py")

from ads1292_studio.calibration import Calibration
from ads1292_studio.events import EventMarker
from ads1292_studio.h5_io import (
    is_recording_h5_path,
    read_recording_h5,
    recording_h5_path,
    write_recording_h5,
)
from ads1292_studio.metadata import SessionMetadata
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import TestProtocol
from ads1292_studio.quality_gate import QualityGate
from ads1292_studio.recording_bundle import (
    AcquisitionProvenance,
    RecordingProcessingSettings,
    calibration_from_bundle,
    events_from_bundle,
    metadata_from_bundle,
    protocol_from_bundle,
)


def _samples(n: int = 20) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(
            timestamp=i / 500.0,
            ch1=i,
            ch2=-i,
            board_heart_rate=60 + (i % 3),
            board_respiration_rate=15,
            status_byte=i % 16,
        )
        for i in range(n)
    )


def _write(tmp_path: Path, **overrides):
    csv_path = tmp_path / "2026-06-21-rec-ads1292-studio.csv"
    csv_path.write_text("placeholder\n")  # journal exists alongside
    kwargs = dict(
        samples=_samples(),
        sample_rate_hz=500.0,
        metadata=SessionMetadata(operator="alice", subject_id="s1"),
        events=(EventMarker(timestamp_seconds=0.01, label="motion", notes="arm"),),
        calibration=Calibration(),
        acquisition=AcquisitionProvenance(),
        protocol=TestProtocol(),
        quality_gate=QualityGate(),
        processing=RecordingProcessingSettings(),
        created_at="2026-06-21T20:00:00",
    )
    kwargs.update(overrides)
    return write_recording_h5(csv_path, **kwargs)


def test_h5_path_helpers(tmp_path: Path) -> None:
    csv_path = tmp_path / "rec.csv"
    assert recording_h5_path(csv_path) == tmp_path / "rec.h5"
    assert is_recording_h5_path(tmp_path / "rec.h5") is True
    assert is_recording_h5_path(tmp_path / "rec.csv") is False


def test_write_then_read_round_trips_samples(tmp_path: Path) -> None:
    out = _write(tmp_path)
    assert out.exists() and out.suffix == ".h5"
    recording, bundle = read_recording_h5(out)
    assert recording.sample_rate_hz == 500.0
    assert len(recording.samples) == 20
    s5 = recording.samples[5]
    assert s5.ch1 == 5 and s5.ch2 == -5
    assert s5.status_byte == 5
    assert s5.board_heart_rate == 60 + (5 % 3)
    assert s5.timestamp == pytest.approx(5 / 500.0)


def test_metadata_bundle_round_trips(tmp_path: Path) -> None:
    out = _write(tmp_path)
    _, bundle = read_recording_h5(out)
    assert metadata_from_bundle(bundle).operator == "alice"
    assert metadata_from_bundle(bundle).subject_id == "s1"
    events = events_from_bundle(bundle)
    assert len(events) == 1 and events[0].label == "motion"
    assert calibration_from_bundle(bundle) == Calibration().normalized()
    assert protocol_from_bundle(bundle).name == TestProtocol().normalized().name
    assert bundle["created_at"] == "2026-06-21T20:00:00"


def test_live_calibration_surfaced_as_h5_attribute(tmp_path: Path) -> None:
    import h5py

    from ads1292_studio.acquisition import build_acquisition_provenance
    from ads1292_studio.calibration import LiveStreamCalibration

    live = LiveStreamCalibration(
        mean_uv_per_count=2.345, std_uv_per_count=0.01, cv_percent=0.4,
        runs=5, test_signal_pp_uv=2016.7,
    )
    provenance = build_acquisition_provenance(
        csv_path=tmp_path / "rec.csv", acquisition_mode="live", port="/dev/x",
        sample_rate_hz=500.0, calibration=Calibration(), live_calibration=live,
        started_at="2026-06-21T00:00:00",
    )
    out = _write(tmp_path, acquisition=provenance)

    # bundle carries the full live calibration
    _, bundle = read_recording_h5(out)
    live_block = bundle["acquisition"]["live_calibration"]
    assert live_block["mean_uv_per_count"] == pytest.approx(2.345)
    assert live_block["runs"] == 5

    # convenience scalar surfaced as a top-level attribute
    with h5py.File(out, "r") as f:
        assert float(f.attrs["live_uv_per_count"]) == pytest.approx(2.345)


def test_no_live_calibration_omits_attribute(tmp_path: Path) -> None:
    import h5py

    out = _write(tmp_path)  # default acquisition has no live calibration
    with h5py.File(out, "r") as f:
        assert "live_uv_per_count" not in dict(f.attrs)


def test_read_recording_h5_rejects_unknown_schema(tmp_path: Path) -> None:
    import h5py

    bad = tmp_path / "bad.h5"
    with h5py.File(bad, "w") as f:
        f.attrs["schema"] = "something-else/9"
    with pytest.raises(ValueError, match="schema"):
        read_recording_h5(bad)


def test_integrity_hashes_present_and_match(tmp_path: Path) -> None:
    import hashlib

    import numpy as np

    out = _write(tmp_path)
    recording, _ = read_recording_h5(out)
    ch2 = np.array([s.ch2 for s in recording.samples], dtype=np.int32)
    expected = hashlib.sha256(ch2.tobytes()).hexdigest()

    import h5py

    with h5py.File(out, "r") as f:
        assert "integrity" in f
        assert f["integrity"].attrs["sha256_ch2"] == expected
