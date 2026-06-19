from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from ads1292_studio.models import Recording, StreamSample


CANONICAL_HEADER = [
    "timestamp",
    "ch1_counts",
    "ch2_counts",
    "board_heart_rate",
    "board_respiration_rate",
    "status_byte",
    "lead_off_bits",
]


def _int_field(row: dict[str, str], *names: str, default: int = 0) -> int:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return int(float(value))
    return default


def _float_field(row: dict[str, str], *names: str, default: float = 0.0) -> float:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return float(value)
    return default


def read_recording_csv(path: Path | str, sample_rate_hz: float = 500.0) -> Recording:
    csv_path = Path(path)
    samples: list[StreamSample] = []
    with csv_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            status_byte = _int_field(row, "status_byte", "lead_off")
            lead_off_bits = _int_field(row, "lead_off_bits", default=status_byte & 0x0F)
            samples.append(
                StreamSample(
                    timestamp=_float_field(row, "timestamp"),
                    ch1=_int_field(row, "ch1_counts", "ecg_counts"),
                    ch2=_int_field(row, "ch2_counts", "resp_counts"),
                    board_heart_rate=_int_field(row, "board_heart_rate", "heart_rate"),
                    board_respiration_rate=_int_field(
                        row,
                        "board_respiration_rate",
                        "respiration_rate",
                    ),
                    status_byte=status_byte | (lead_off_bits & 0x0F),
                )
            )
    return Recording(path=csv_path, samples=tuple(samples), sample_rate_hz=sample_rate_hz)


def write_recording_csv(path: Path | str, samples: Iterable[StreamSample]) -> None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", buffering=1) as handle:
        writer = csv.writer(handle)
        writer.writerow(CANONICAL_HEADER)
        for sample in samples:
            writer.writerow(
                [
                    f"{sample.timestamp:.6f}",
                    sample.ch1,
                    sample.ch2,
                    sample.board_heart_rate,
                    sample.board_respiration_rate,
                    sample.status_byte,
                    sample.lead_off_bits,
                ]
            )
        handle.flush()


class CsvRecorder:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._handle = None
        self._writer = None
        self.rows_written = 0

    def __enter__(self) -> "CsvRecorder":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", newline="", buffering=1)
        self._writer = csv.writer(self._handle)
        self._writer.writerow(CANONICAL_HEADER)
        self._handle.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is not None:
            self._handle.flush()
            self._handle.close()
        self._handle = None
        self._writer = None

    def write(self, sample: StreamSample) -> None:
        if self._writer is None:
            raise RuntimeError("CSV recorder is not open")
        self._writer.writerow(
            [
                f"{sample.timestamp:.6f}",
                sample.ch1,
                sample.ch2,
                sample.board_heart_rate,
                sample.board_respiration_rate,
                sample.status_byte,
                sample.lead_off_bits,
            ]
        )
        self.rows_written += 1
        if self._handle is not None:
            self._handle.flush()
