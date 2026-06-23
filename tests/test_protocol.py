import json
from pathlib import Path

import pytest

from ads1292_studio.protocol import ProtocolStep, TestProtocol, protocol_template, read_protocol_json, write_protocol_json


def test_protocol_json_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "protocol.json"
    protocol = TestProtocol(
        name="MOTAC gel validation",
        objective="Compare MOTAC gel against commercial Ag/AgCl during motion.",
        operator_instructions="Seat subject, clean skin, attach RA/LA/RL.",
        steps=(
            ProtocolStep(start_seconds=0.0, duration_seconds=30.0, label="baseline", instruction="Sit still."),
            ProtocolStep(start_seconds=30.0, duration_seconds=15.0, label="motion", instruction="Move left arm."),
        ),
        acceptance_notes="Gate must pass and QRS must remain visible.",
    )

    write_protocol_json(path, protocol)
    loaded = read_protocol_json(path)

    assert loaded == protocol


def test_protocol_normalizes_blank_and_negative_fields() -> None:
    protocol = TestProtocol(
        name="  ",
        objective="  compare electrodes  ",
        operator_instructions="  ",
        steps=(ProtocolStep(start_seconds=-2.0, duration_seconds=-5.0, label="  ", instruction="  breathe normally  "),),
        acceptance_notes="  ",
    ).normalized()

    assert protocol.name == "ADS1292 validation protocol"
    assert protocol.objective == "compare electrodes"
    assert protocol.operator_instructions == "Follow the listed protocol steps."
    assert protocol.steps[0].start_seconds == 0.0
    assert protocol.steps[0].duration_seconds == 0.0
    assert protocol.steps[0].label == "step"
    assert protocol.steps[0].instruction == "breathe normally"
    assert protocol.acceptance_notes == "Review quality gate and artifacts before accepting the run."


def test_protocol_template_is_immediately_writable(tmp_path: Path) -> None:
    path = tmp_path / "protocol-template.json"

    write_protocol_json(path, protocol_template())

    loaded = read_protocol_json(path)
    assert loaded.name == "MOTAC ECG validation"
    assert loaded.steps[0].label == "baseline"
    assert loaded.steps[1].label == "motion"


def test_read_protocol_tolerates_unknown_step_keys(tmp_path: Path) -> None:
    """A hand-edited or schema-evolved step with an extra key must not crash the
    load (which would also abort CLI --protocol and session packaging)."""
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps({
        "name": "x",
        "steps": [{"start_seconds": 0, "duration_seconds": 10, "label": "a",
                   "instruction": "b", "color": "red"}],  # 'color' is not a field
    }))

    loaded = read_protocol_json(path)

    assert len(loaded.steps) == 1
    assert loaded.steps[0].label == "a"
    assert loaded.steps[0].duration_seconds == 10.0


def test_read_protocol_defaults_missing_step_keys(tmp_path: Path) -> None:
    """A step missing a required key must default it, not raise TypeError."""
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps({
        "name": "x",
        "steps": [{"start_seconds": 5, "duration_seconds": 10, "label": "a"}],  # no 'instruction'
    }))

    loaded = read_protocol_json(path)

    assert len(loaded.steps) == 1
    assert loaded.steps[0].label == "a"
    assert loaded.steps[0].instruction  # filled with the normalized fallback


def test_read_protocol_rejects_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps([1, 2, 3]))  # valid JSON, wrong shape

    with pytest.raises(ValueError):
        read_protocol_json(path)
