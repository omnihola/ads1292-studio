from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class SessionMetadata:
    session_id: str = ""
    subject_id: str = "anonymous"
    electrode: str = ""
    montage: str = "RA/LA/RL torso"
    operator: str = ""
    notes: str = ""

    def normalized(self) -> "SessionMetadata":
        return SessionMetadata(
            session_id=_clean(self.session_id, "untitled-session"),
            subject_id=_clean(self.subject_id, "anonymous"),
            electrode=_clean(self.electrode, "unspecified electrode"),
            montage=_clean(self.montage, "unspecified montage"),
            operator=_clean(self.operator, "unspecified operator"),
            notes=self.notes.strip(),
        )


def _clean(value: str, fallback: str) -> str:
    value = value.strip()
    return value if value else fallback


def read_metadata_json(path: Path | str) -> SessionMetadata:
    data = json.loads(Path(path).read_text())
    allowed = {field.name for field in SessionMetadata.__dataclass_fields__.values()}
    filtered = {key: value for key, value in data.items() if key in allowed}
    return SessionMetadata(**filtered).normalized()


def write_metadata_json(path: Path | str, metadata: SessionMetadata) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(asdict(metadata.normalized()), indent=2) + "\n")


def metadata_template() -> SessionMetadata:
    return SessionMetadata(
        session_id="YYYYMMDD-run-001",
        subject_id="anonymous",
        electrode="commercial Ag/AgCl control or MOTAC gel + Ag/AgCl",
        montage="RA/LA/RL torso",
        operator="",
        notes="posture, movement condition, skin prep, gel formulation, electrode placement",
    )
