from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable


EVENT_ANNOTATIONS_SCHEMA = "ads1292-event-annotations-v1"
EVENT_TIMESTAMP_REFERENCE = "relative_seconds_from_recording_start"
EVENT_SAMPLE_INDEX_REFERENCE = "zero_based_sample_index_at_recording_sample_rate"
DEFAULT_EVENT_SAMPLE_RATE_HZ = 500.0


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


def write_events_json(
    path: Path | str,
    events: Iterable[EventMarker],
    *,
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = _normalized_sample_rate(sample_rate_hz)
    normalized = [_event_json_entry(event, sample_rate_hz=sample_rate) for event in events]
    payload = {
        "schema": EVENT_ANNOTATIONS_SCHEMA,
        "timestamp_reference": EVENT_TIMESTAMP_REFERENCE,
        "sample_rate_hz": sample_rate,
        "sample_index_reference": EVENT_SAMPLE_INDEX_REFERENCE,
        "events": normalized,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n")


EVENTS_CSV_HEADER = [
    "event_id",
    "start_seconds",
    "end_seconds",
    "duration_seconds",
    "start_sample_index",
    "end_sample_index",
    "duration_samples",
    "event_type",
    "label",
    "notes",
]


def write_events_csv(
    path: Path | str,
    events: Iterable[EventMarker],
    *,
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = _normalized_sample_rate(sample_rate_hz)
    with output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVENTS_CSV_HEADER)
        writer.writeheader()
        for event in events:
            marker = event.normalized()
            sample_indices = _event_sample_indices(marker, sample_rate)
            writer.writerow(
                {
                    "start_seconds": f"{marker.timestamp_seconds:.6f}",
                    "end_seconds": f"{marker.end_seconds:.6f}",
                    "duration_seconds": f"{marker.duration_seconds:.6f}",
                    "event_id": event_id(marker, sample_rate_hz=sample_rate),
                    "start_sample_index": sample_indices["start_sample_index"],
                    "end_sample_index": sample_indices["end_sample_index"],
                    "duration_samples": sample_indices["duration_samples"],
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


def format_event_log_text(
    events: Iterable[EventMarker],
    *,
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
) -> str:
    normalized = tuple(event.normalized() for event in events)
    if not normalized:
        return "No event annotations.\n"
    rows = [
        "#\tID\tStart (s)\tEnd (s)\tDuration (s)\t"
        "Start sample\tEnd sample\tDuration samples\tType\tLabel\tNotes"
    ]
    sample_rate = _normalized_sample_rate(sample_rate_hz)
    for position, event in enumerate(normalized, start=1):
        sample_indices = event_sample_indices(event, sample_rate)
        rows.append(
            "\t".join(
                (
                    str(position),
                    event_id(event, sample_rate_hz=sample_rate),
                    f"{event.timestamp_seconds:.2f}",
                    f"{event.end_seconds:.2f}",
                    f"{event.duration_seconds:.2f}",
                    str(sample_indices["start_sample_index"]),
                    str(sample_indices["end_sample_index"]),
                    str(sample_indices["duration_samples"]),
                    _event_type(event),
                    event.label,
                    event.notes,
                )
            )
        )
    return "\n".join(rows) + "\n"


def event_sample_indices(
    event: EventMarker,
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
) -> dict[str, int]:
    return _event_sample_indices(event, _normalized_sample_rate(sample_rate_hz))


def event_id(
    event: EventMarker,
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
) -> str:
    sample_rate = _normalized_sample_rate(sample_rate_hz)
    marker = event.normalized()
    sample_indices = _event_sample_indices(marker, sample_rate)
    label_slug = _slug(marker.label)
    fingerprint = "|".join(
        (
            str(sample_indices["start_sample_index"]),
            str(sample_indices["end_sample_index"]),
            _event_type(marker),
            marker.label,
            marker.notes,
        )
    )
    digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:8]
    return (
        f"evt-{sample_indices['start_sample_index']:07d}-"
        f"{sample_indices['end_sample_index']:07d}-{label_slug}-{digest}"
    )


def _event_type(event: EventMarker) -> str:
    return "interval" if event.normalized().duration_seconds > 0 else "point"


def _event_json_entry(
    event: EventMarker,
    *,
    sample_rate_hz: float = DEFAULT_EVENT_SAMPLE_RATE_HZ,
) -> dict[str, object]:
    marker = event.normalized()
    return {
        "event_id": event_id(marker, sample_rate_hz=sample_rate_hz),
        "timestamp_seconds": marker.timestamp_seconds,
        "start_seconds": marker.timestamp_seconds,
        "end_seconds": marker.end_seconds,
        "duration_seconds": marker.duration_seconds,
        **_event_sample_indices(marker, _normalized_sample_rate(sample_rate_hz)),
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


def remove_event_at_index(
    events: Iterable[EventMarker],
    index_1based: int,
) -> tuple[tuple[EventMarker, ...], EventMarker | None]:
    """Remove the annotation at a 1-based position (as shown in the event log).

    Returns the remaining events plus the removed marker, or the unchanged events
    and ``None`` when the index is out of range.
    """
    normalized = tuple(event.normalized() for event in events)
    if index_1based < 1 or index_1based > len(normalized):
        return normalized, None
    removed = normalized[index_1based - 1]
    remaining = normalized[: index_1based - 1] + normalized[index_1based:]
    return remaining, removed


def event_template() -> tuple[EventMarker, ...]:
    return (
        EventMarker(timestamp_seconds=5.0, duration_seconds=3.0, label="motion", notes="subject moved arm"),
        EventMarker(timestamp_seconds=20.0, duration_seconds=5.0, label="deep breath", notes="respiration challenge"),
    )


def _event_sample_indices(event: EventMarker, sample_rate_hz: float) -> dict[str, int]:
    marker = event.normalized()
    start_index = _seconds_to_sample_index(marker.timestamp_seconds, sample_rate_hz)
    end_index = _seconds_to_sample_index(marker.end_seconds, sample_rate_hz)
    return {
        "start_sample_index": start_index,
        "end_sample_index": end_index,
        "duration_samples": max(0, end_index - start_index),
    }


def _seconds_to_sample_index(seconds: float, sample_rate_hz: float) -> int:
    return max(0, int(round(float(seconds) * sample_rate_hz)))


def _normalized_sample_rate(sample_rate_hz: float) -> float:
    rate = float(sample_rate_hz)
    return rate if rate > 0 else DEFAULT_EVENT_SAMPLE_RATE_HZ


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:32] or "event"
