from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True)
class ProtocolStep:
    start_seconds: float
    duration_seconds: float
    label: str
    instruction: str

    def normalized(self) -> "ProtocolStep":
        return ProtocolStep(
            start_seconds=max(0.0, float(self.start_seconds)),
            duration_seconds=max(0.0, float(self.duration_seconds)),
            label=_clean(self.label, "step"),
            instruction=_clean(self.instruction, "Follow the protocol step."),
        )


@dataclass(frozen=True)
class TestProtocol:
    __test__: ClassVar[bool] = False

    name: str = "ADS1292 validation protocol"
    objective: str = ""
    operator_instructions: str = "Follow the listed protocol steps."
    steps: tuple[ProtocolStep, ...] = tuple()
    acceptance_notes: str = "Review quality gate and artifacts before accepting the run."

    def normalized(self) -> "TestProtocol":
        steps = tuple(step.normalized() for step in self.steps)
        return TestProtocol(
            name=_clean(self.name, "ADS1292 validation protocol"),
            objective=self.objective.strip(),
            operator_instructions=_clean(self.operator_instructions, "Follow the listed protocol steps."),
            steps=steps,
            acceptance_notes=_clean(
                self.acceptance_notes,
                "Review quality gate and artifacts before accepting the run.",
            ),
        )


def read_protocol_json(path: Path | str) -> TestProtocol:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{Path(path).name}: protocol JSON must be an object")
    raw_steps = data.get("steps", [])
    steps = tuple(_step_from_mapping(item) for item in raw_steps if isinstance(item, dict))
    return TestProtocol(
        name=str(data.get("name", "")),
        objective=str(data.get("objective", "")),
        operator_instructions=str(data.get("operator_instructions", "")),
        steps=steps,
        acceptance_notes=str(data.get("acceptance_notes", "")),
    ).normalized()


def _step_from_mapping(item: dict) -> ProtocolStep:
    """Build a ProtocolStep from an untrusted mapping: drop unknown keys and
    default missing ones, mirroring metadata.read_metadata_json. Without this a
    hand-edited or schema-evolved step crashes the whole load — and, via
    session packaging, the entire package build."""
    allowed = {field.name for field in ProtocolStep.__dataclass_fields__.values()}
    fields: dict[str, object] = {
        "start_seconds": 0.0,
        "duration_seconds": 0.0,
        "label": "",
        "instruction": "",
    }
    fields.update({key: value for key, value in item.items() if key in allowed})
    return ProtocolStep(**fields)


def write_protocol_json(path: Path | str, protocol: TestProtocol) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(protocol.normalized()), indent=2) + "\n")


def protocol_template() -> TestProtocol:
    return TestProtocol(
        name="MOTAC ECG validation",
        objective="Compare MOTAC gel electrode performance against a commercial Ag/AgCl control.",
        operator_instructions="Use battery power, verify RA/LA/RL contact, and record protocol events.",
        steps=(
            ProtocolStep(0.0, 30.0, "baseline", "Subject seated and still; verify stable ECG and contact."),
            ProtocolStep(30.0, 15.0, "motion", "Ask subject to move arm or torso gently to challenge adhesion."),
            ProtocolStep(45.0, 30.0, "recovery", "Subject returns to still posture; confirm QRS recovery."),
        ),
        acceptance_notes="Quality gate should pass; QRS should remain visible before, during, and after motion.",
    )


def _clean(value: str, fallback: str) -> str:
    value = value.strip()
    return value if value else fallback
