import json
from pathlib import Path

import pytest

from ads1292_studio.metadata import SessionMetadata, read_metadata_json, write_metadata_json


def test_read_metadata_rejects_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps([1, 2, 3]))  # valid JSON, wrong shape

    with pytest.raises(ValueError):
        read_metadata_json(path)


def test_metadata_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    metadata = SessionMetadata(
        session_id="MOTAC-001",
        subject_id="anon-01",
        electrode="MOTAC gel + Ag/AgCl",
        montage="RA/LA/RL torso",
        operator="JB",
        notes="quiet seated test",
    )

    write_metadata_json(path, metadata)
    loaded = read_metadata_json(path)

    assert loaded == metadata


def test_metadata_normalizes_blank_fields() -> None:
    metadata = SessionMetadata(session_id="  run 1  ", subject_id="")

    assert metadata.normalized().session_id == "run 1"
    assert metadata.normalized().subject_id == "anonymous"


def test_metadata_records_acquisition_mode() -> None:
    metadata = SessionMetadata(session_id="run-raw", acquisition_mode=" raw_adc_24bit ")

    assert metadata.normalized().acquisition_mode == "raw_adc_24bit"
