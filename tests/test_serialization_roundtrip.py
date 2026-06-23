"""Property-based (seeded, deterministic) round-trip tests for the data-integrity
layer of the recorder: CSV and HDF5 sample serialization, and event annotation
serialization (CSV / JSON / embedded in the .h5 bundle).

These guard the research instrument's core promise — that what is written is read
back exactly — against future serialization changes. The RNG is seeded so runs
are reproducible; a failure prints the offending sample/marker.
"""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from ads1292_studio.events import EventMarker, event_from_interval
from ads1292_studio.models import StreamSample

# Special-character labels/notes that have historically broken naive serializers.
_LABELS = ["baseline", "motion", "recovery", "p", "événement", "测试", "a,b,c", 'q"x', "tab\tx", "line\nbreak", ""]
_NOTES = ["", "arm moved", "с примечанием", "x,y,z", "semi;colon", 'has "quotes"', ""]


def _rand_samples(rng: random.Random, n: int, *, ch_lo: int, ch_hi: int) -> tuple[StreamSample, ...]:
    return tuple(
        StreamSample(
            timestamp=round(i / 500.0, 6),
            ch1=rng.randint(ch_lo, ch_hi),
            ch2=rng.randint(ch_lo, ch_hi),
            board_heart_rate=rng.randint(0, 255),
            board_respiration_rate=rng.randint(0, 255),
            status_byte=rng.randint(0, 0xFFFF),
            sample_index=i,
        )
        for i in range(n)
    )


def _rand_marker(rng: random.Random) -> EventMarker:
    start = round(rng.uniform(0.0, 600.0), 6)
    duration = rng.choice([0.0, round(rng.uniform(0.0, 30.0), 6)])
    return event_from_interval(
        start_seconds=start, end_seconds=start + duration,
        label=rng.choice(_LABELS), notes=rng.choice(_NOTES),
    )


def _samples_equal(a: StreamSample, b: StreamSample) -> bool:
    return (
        a.ch1 == b.ch1 and a.ch2 == b.ch2
        and a.board_heart_rate == b.board_heart_rate
        and a.board_respiration_rate == b.board_respiration_rate
        and a.status_byte == b.status_byte
        and abs(a.timestamp - b.timestamp) <= 1e-6
    )


def _markers_equal(a: EventMarker, b: EventMarker) -> bool:
    return (
        round(a.timestamp_seconds, 6) == round(b.timestamp_seconds, 6)
        and round(a.duration_seconds, 6) == round(b.duration_seconds, 6)
        and a.label == b.label and a.notes == b.notes
    )


def test_csv_sample_round_trip_is_lossless(tmp_path: Path) -> None:
    from ads1292_studio.csv_io import read_recording_csv, write_recording_csv

    rng = random.Random(101)
    for trial in range(60):
        samples = _rand_samples(rng, rng.randint(0, 40), ch_lo=-32768, ch_hi=32767)
        path = tmp_path / f"rec-{trial}.csv"
        write_recording_csv(path, samples)
        back = read_recording_csv(path).samples
        assert len(back) == len(samples)
        for a, b in zip(samples, back):
            assert _samples_equal(a, b), f"trial {trial}: {a} -> {b}"


def test_h5_sample_round_trip_is_lossless(tmp_path: Path) -> None:
    pytest.importorskip("h5py")
    from ads1292_studio.calibration import Calibration
    from ads1292_studio.h5_io import read_recording_h5, recording_h5_path, write_recording_h5
    from ads1292_studio.metadata import SessionMetadata
    from ads1292_studio.protocol import TestProtocol
    from ads1292_studio.quality_gate import QualityGate
    from ads1292_studio.recording_bundle import AcquisitionProvenance, RecordingProcessingSettings

    rng = random.Random(202)
    for trial in range(20):
        # full signed 24-bit raw range — the real worst case for ch1/ch2
        samples = _rand_samples(rng, rng.randint(1, 30), ch_lo=-(2 ** 23), ch_hi=2 ** 23 - 1)
        csv_path = tmp_path / f"rec-{trial}.csv"
        csv_path.write_text("journal\n")
        write_recording_h5(
            csv_path, samples=samples, sample_rate_hz=500.0, metadata=SessionMetadata(),
            events=(), calibration=Calibration(), acquisition=AcquisitionProvenance(),
            protocol=TestProtocol(), quality_gate=QualityGate(),
            processing=RecordingProcessingSettings(), created_at="2026-06-23T00:00:00",
        )
        back = read_recording_h5(recording_h5_path(csv_path))[0].samples
        assert len(back) == len(samples)
        for a, b in zip(samples, back):
            assert _samples_equal(a, b), f"trial {trial}: {a} -> {b}"


def test_event_csv_and_json_round_trip_preserve_special_characters(tmp_path: Path) -> None:
    from ads1292_studio.events import (
        read_events_csv, read_events_json, write_events_csv, write_events_json,
    )

    rng = random.Random(303)
    for trial in range(80):
        markers = tuple(_rand_marker(rng) for _ in range(rng.randint(0, 8)))
        normalized = tuple(m.normalized() for m in markers)

        csv_path = tmp_path / f"e-{trial}.csv"
        write_events_csv(csv_path, markers)
        back_csv = read_events_csv(csv_path)
        assert len(back_csv) == len(normalized)
        for a, b in zip(normalized, back_csv):
            assert _markers_equal(a, b), f"CSV trial {trial}: {(a.label, a.notes)} -> {(b.label, b.notes)}"

        json_path = tmp_path / f"e-{trial}.json"
        write_events_json(json_path, markers)
        back_json = read_events_json(json_path)
        assert len(back_json) == len(normalized)
        for a, b in zip(normalized, back_json):
            assert _markers_equal(a, b), f"JSON trial {trial}: {(a.label, a.notes)} -> {(b.label, b.notes)}"


def test_h5_bundle_event_round_trip_is_lossless(tmp_path: Path) -> None:
    pytest.importorskip("h5py")
    from ads1292_studio.calibration import Calibration
    from ads1292_studio.h5_io import read_recording_h5, recording_h5_path, write_recording_h5
    from ads1292_studio.metadata import SessionMetadata
    from ads1292_studio.protocol import TestProtocol
    from ads1292_studio.quality_gate import QualityGate
    from ads1292_studio.recording_bundle import (
        AcquisitionProvenance, RecordingProcessingSettings, events_from_bundle,
    )

    rng = random.Random(404)
    samples = _rand_samples(rng, 5, ch_lo=-100, ch_hi=100)
    for trial in range(40):
        markers = tuple(_rand_marker(rng) for _ in range(rng.randint(0, 6)))
        normalized = tuple(m.normalized() for m in markers)
        csv_path = tmp_path / f"rec-{trial}.csv"
        csv_path.write_text("journal\n")
        write_recording_h5(
            csv_path, samples=samples, sample_rate_hz=500.0, metadata=SessionMetadata(),
            events=markers, calibration=Calibration(), acquisition=AcquisitionProvenance(),
            protocol=TestProtocol(), quality_gate=QualityGate(),
            processing=RecordingProcessingSettings(), created_at="2026-06-23T00:00:00",
        )
        _, bundle = read_recording_h5(recording_h5_path(csv_path))
        back = events_from_bundle(bundle)
        assert len(back) == len(normalized)
        for a, b in zip(normalized, back):
            assert _markers_equal(a, b), f"trial {trial}: {(a.label, a.notes)} -> {(b.label, b.notes)}"
