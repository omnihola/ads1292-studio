from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class EventMarker:
    timestamp_seconds: float
    label: str = "event"
    notes: str = ""
    duration_seconds: float = 0.0

    def normalized(self) -> "EventMarker":
        timestamp = max(0.0, float(self.timestamp_seconds))
        duration = max(0.0, float(self.duration_seconds))
        label = self.label.strip() or "event"
        return EventMarker(
            timestamp_seconds=timestamp,
            label=label,
            notes=self.notes.strip(),
            duration_seconds=duration,
        )

    @property
    def end_seconds(self) -> float:
        normalized = self.normalized()
        return normalized.timestamp_seconds + normalized.duration_seconds


def read_events_json(path: Path | str) -> tuple[EventMarker, ...]:
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data.get("events", [])
    allowed = {field.name for field in EventMarker.__dataclass_fields__.values()}
    return tuple(
        EventMarker(**{key: value for key, value in item.items() if key in allowed}).normalized()
        for item in data
        if isinstance(item, dict)
    )


def write_events_json(path: Path | str, events: Iterable[EventMarker]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = [asdict(event.normalized()) for event in events]
    output.write_text(json.dumps(normalized, indent=2) + "\n")


def event_from_interval(
    *,
    start_seconds: float,
    end_seconds: float,
    label: str,
    notes: str = "",
) -> EventMarker:
    start = max(0.0, float(start_seconds))
    end = max(0.0, float(end_seconds))
    ordered_start = min(start, end)
    ordered_end = max(start, end)
    return EventMarker(
        timestamp_seconds=ordered_start,
        duration_seconds=ordered_end - ordered_start,
        label=label,
        notes=notes,
    ).normalized()


def event_template() -> tuple[EventMarker, ...]:
    return (
        EventMarker(timestamp_seconds=5.0, duration_seconds=3.0, label="motion", notes="subject moved arm"),
        EventMarker(timestamp_seconds=20.0, duration_seconds=5.0, label="deep breath", notes="respiration challenge"),
    )
