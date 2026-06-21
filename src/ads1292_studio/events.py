from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable


EVENT_ANNOTATIONS_SCHEMA = "ads1292-event-annotations-v1"
EVENT_TIMESTAMP_REFERENCE = "relative_seconds_from_recording_start"


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
    return tuple(
        _event_from_mapping(item)
        for item in data
        if isinstance(item, dict)
    )


def write_events_json(path: Path | str, events: Iterable[EventMarker]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = [_event_json_entry(event) for event in events]
    payload = {
        "schema": EVENT_ANNOTATIONS_SCHEMA,
        "timestamp_reference": EVENT_TIMESTAMP_REFERENCE,
        "events": normalized,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n")


EVENTS_CSV_HEADER = ["start_seconds", "end_seconds", "duration_seconds", "event_type", "label", "notes"]


def write_events_csv(path: Path | str, events: Iterable[EventMarker]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVENTS_CSV_HEADER)
        writer.writeheader()
        for event in events:
            marker = event.normalized()
            writer.writerow(
                {
                    "start_seconds": f"{marker.timestamp_seconds:.6f}",
                    "end_seconds": f"{marker.end_seconds:.6f}",
                    "duration_seconds": f"{marker.duration_seconds:.6f}",
                    "event_type": _event_type(marker),
                    "label": marker.label,
                    "notes": marker.notes,
                }
            )


def read_events_csv(path: Path | str) -> tuple[EventMarker, ...]:
    csv_path = Path(path)
    with csv_path.open(newline="") as handle:
        return tuple(
            _event_from_mapping(row)
            for row in csv.DictReader(handle)
        )


def _event_type(event: EventMarker) -> str:
    return "interval" if event.normalized().duration_seconds > 0 else "point"


def _event_json_entry(event: EventMarker) -> dict[str, object]:
    marker = event.normalized()
    return {
        "timestamp_seconds": marker.timestamp_seconds,
        "start_seconds": marker.timestamp_seconds,
        "end_seconds": marker.end_seconds,
        "duration_seconds": marker.duration_seconds,
        "event_type": _event_type(marker),
        "label": marker.label,
        "notes": marker.notes,
    }


def _event_from_mapping(item: dict) -> EventMarker:
    timestamp = item.get("timestamp_seconds", item.get("start_seconds", 0.0))
    duration = item.get("duration_seconds")
    if duration in (None, ""):
        start = float(item.get("start_seconds", timestamp) or 0.0)
        end = float(item.get("end_seconds", start) or start)
        duration = max(0.0, end - start)
        timestamp = start
    return EventMarker(
        timestamp_seconds=float(timestamp or 0.0),
        duration_seconds=float(duration or 0.0),
        label=str(item.get("label", "")),
        notes=str(item.get("notes", "")),
    ).normalized()


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
