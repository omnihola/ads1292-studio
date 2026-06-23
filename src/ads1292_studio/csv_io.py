from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ads1292_studio.calibration import Calibration, LiveStreamCalibration
from ads1292_studio.models import RawSample, Recording, StreamSample


CANONICAL_HEADER = [
    "timestamp",
    "sample_index",
    "ch1_counts",
    "ch2_counts",
    "board_heart_rate",
    "board_respiration_rate",
    "status_byte",
    "lead_off_bits",
]

LIVE_CALIBRATION_COLUMNS = [
    "live_scale_uv_per_count",
    "live_scale_std_uv_per_count",
    "live_scale_cv_percent",
    "live_scale_runs",
    "live_test_signal_pp_uv",
    "live_scale_type",
]

RAW_HEADER = [
    "timestamp",
    "sample_index",
    "ch1_raw24",
    "ch2_raw24",
    "ch1_uv",
    "ch2_uv",
    "status_byte",
    "lead_off_bits",
    "vref_mv",
    "pga_gain",
    "adc_bits",
    "raw_lsb_uv_per_count",
    "acquisition_mode",
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


def _stream_sample_index(sample: StreamSample, fallback: int) -> int:
    return int(sample.sample_index) if sample.sample_index is not None else int(fallback)


def _resolve_column_indices(header: list[str], names: tuple[str, ...]) -> tuple[int, ...]:
    """Column indices for the given logical field names, in priority order.

    Resolving names->indices ONCE from the header (instead of a dict lookup per
    field per row) is what makes the streamed read fast; returning all matching
    indices preserves the per-row fallback (an empty primary cell falls back to
    the next name for that row)."""
    position = {name: index for index, name in enumerate(header)}
    return tuple(position[name] for name in names if name in position)


def _row_first_nonempty(row: list[str], columns: tuple[int, ...]) -> str | None:
    for index in columns:
        if index < len(row):
            value = row[index]
            if value not in (None, ""):
                return value
    return None


def _row_int(row: list[str], columns: tuple[int, ...], default: int = 0) -> int:
    value = _row_first_nonempty(row, columns)
    return int(float(value)) if value is not None else default


def _row_float(row: list[str], columns: tuple[int, ...], default: float = 0.0) -> float:
    value = _row_first_nonempty(row, columns)
    return float(value) if value is not None else default


def read_recording_csv(path: Path | str, sample_rate_hz: float = 500.0) -> Recording:
    csv_path = Path(path)
    samples: list[StreamSample] = []
    with csv_path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        ts_cols = _resolve_column_indices(header, ("timestamp",))
        ch1_cols = _resolve_column_indices(header, ("ch1_counts", "ecg_counts", "ch1_raw24"))
        ch2_cols = _resolve_column_indices(header, ("ch2_counts", "resp_counts", "ch2_raw24"))
        hr_cols = _resolve_column_indices(header, ("board_heart_rate", "heart_rate"))
        rr_cols = _resolve_column_indices(header, ("board_respiration_rate", "respiration_rate"))
        status_cols = _resolve_column_indices(header, ("status_byte", "lead_off"))
        lead_off_cols = _resolve_column_indices(header, ("lead_off_bits",))
        index_cols = _resolve_column_indices(header, ("sample_index", "index"))
        for row_index, row in enumerate(reader):
            status_byte = _row_int(row, status_cols)
            lead_off_value = _row_first_nonempty(row, lead_off_cols)
            if lead_off_value is not None:
                # preserve all upper status bits (raw status is 16-bit); only the
                # low nibble carries the lead-off flags
                status_byte = (status_byte & ~0x0F) | (int(float(lead_off_value)) & 0x0F)
            samples.append(
                StreamSample(
                    timestamp=_row_float(row, ts_cols),
                    ch1=_row_int(row, ch1_cols),
                    ch2=_row_int(row, ch2_cols),
                    board_heart_rate=_row_int(row, hr_cols),
                    board_respiration_rate=_row_int(row, rr_cols),
                    status_byte=status_byte,
                    sample_index=_row_int(row, index_cols, default=row_index),
                )
            )
    return Recording(path=csv_path, samples=tuple(samples), sample_rate_hz=sample_rate_hz)


@dataclass(frozen=True)
class RawRecording:
    path: Path | None
    samples: tuple[RawSample, ...]
    sample_rate_hz: float = 500.0


def read_raw_recording_csv(path: Path | str, sample_rate_hz: float = 500.0) -> RawRecording:
    csv_path = Path(path)
    samples: list[RawSample] = []
    with csv_path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            status_byte = _int_field(row, "status_byte", "lead_off")
            if row.get("lead_off_bits") not in (None, ""):
                status_byte = (status_byte & 0xFFF0) | (_int_field(row, "lead_off_bits") & 0x0F)
            samples.append(
                RawSample(
                    timestamp=_float_field(row, "timestamp"),
                    sample_index=_int_field(row, "sample_index", "index"),
                    ch1_raw24=_int_field(row, "ch1_raw24", "ch1_counts"),
                    ch2_raw24=_int_field(row, "ch2_raw24", "ch2_counts"),
                    ch1_uv=_float_field(row, "ch1_uv", default=0.0),
                    ch2_uv=_float_field(row, "ch2_uv", default=0.0),
                    status_byte=status_byte,
                )
            )
    return RawRecording(path=csv_path, samples=tuple(samples), sample_rate_hz=sample_rate_hz)


def write_recording_csv(path: Path | str, samples: Iterable[StreamSample]) -> None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", buffering=1) as handle:
        writer = csv.writer(handle)
        writer.writerow(CANONICAL_HEADER)
        for row_index, sample in enumerate(samples):
            writer.writerow(
                [
                    f"{sample.timestamp:.6f}",
                    _stream_sample_index(sample, row_index),
                    sample.ch1,
                    sample.ch2,
                    sample.board_heart_rate,
                    sample.board_respiration_rate,
                    sample.status_byte,
                    sample.lead_off_bits,
                ]
            )
        handle.flush()


def _raw_row(sample: RawSample, calibration: Calibration) -> list[object]:
    scale = calibration.normalized().microvolts_per_count
    ch1_uv = sample.ch1_uv if sample.ch1_uv is not None else sample.ch1_raw24 * scale
    ch2_uv = sample.ch2_uv if sample.ch2_uv is not None else sample.ch2_raw24 * scale
    normalized = calibration.normalized()
    return [
        f"{sample.timestamp:.6f}",
        sample.sample_index,
        sample.ch1_raw24,
        sample.ch2_raw24,
        f"{ch1_uv:.17g}",
        f"{ch2_uv:.17g}",
        sample.status_byte,
        sample.lead_off_bits,
        f"{normalized.vref_mv:g}",
        f"{normalized.pga_gain:g}",
        normalized.adc_bits,
        f"{normalized.microvolts_per_count:.9f}",
        "raw_adc_24bit",
    ]


def write_raw_recording_csv(
    path: Path | str,
    samples: Iterable[RawSample],
    *,
    calibration: Calibration | None = None,
) -> None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = (calibration or Calibration()).normalized()
    with csv_path.open("w", newline="", buffering=1) as handle:
        writer = csv.writer(handle)
        writer.writerow(RAW_HEADER)
        for sample in samples:
            writer.writerow(_raw_row(sample, normalized))
        handle.flush()


class CsvRecorder:
    def __init__(
        self,
        path: Path | str,
        *,
        live_calibration: LiveStreamCalibration | None = None,
        flush_every_rows: int = 50,
    ) -> None:
        self.path = Path(path)
        self.live_calibration = live_calibration.normalized() if live_calibration else None
        self.flush_every_rows = max(1, int(flush_every_rows))
        self._handle = None
        self._writer = None
        self.rows_written = 0

    def __enter__(self) -> "CsvRecorder":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", newline="", buffering=1)
        self._writer = csv.writer(self._handle)
        self._writer.writerow(self._header())
        self._handle.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is not None:
            try:
                self._handle.flush()
            finally:
                self._handle.close()  # always release the handle, even if flush fails
        self._handle = None
        self._writer = None

    def write(self, sample: StreamSample) -> None:
        if self._writer is None:
            raise RuntimeError("CSV recorder is not open")
        row = [
            f"{sample.timestamp:.6f}",
            _stream_sample_index(sample, self.rows_written),
            sample.ch1,
            sample.ch2,
            sample.board_heart_rate,
            sample.board_respiration_rate,
            sample.status_byte,
            sample.lead_off_bits,
        ]
        if self.live_calibration is not None:
            row.extend(self._live_calibration_row())
        self._writer.writerow(row)
        self.rows_written += 1
        if self._handle is not None and self.rows_written % self.flush_every_rows == 0:
            self._handle.flush()

    def _header(self) -> list[str]:
        if self.live_calibration is None:
            return list(CANONICAL_HEADER)
        return list(CANONICAL_HEADER + LIVE_CALIBRATION_COLUMNS)

    def _live_calibration_row(self) -> list[object]:
        if self.live_calibration is None:
            return []
        calibration = self.live_calibration
        return [
            f"{calibration.mean_uv_per_count:.9f}",
            f"{calibration.std_uv_per_count:.9f}",
            f"{calibration.cv_percent:.6f}",
            calibration.runs,
            f"{calibration.test_signal_pp_uv:.6f}",
            calibration.scale_type,
        ]


class RawCsvRecorder:
    def __init__(
        self,
        path: Path | str,
        *,
        calibration: Calibration | None = None,
        flush_every_rows: int = 50,
    ) -> None:
        self.path = Path(path)
        self.calibration = (calibration or Calibration()).normalized()
        self.flush_every_rows = max(1, int(flush_every_rows))
        self._handle = None
        self._writer = None
        self.rows_written = 0

    def __enter__(self) -> "RawCsvRecorder":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("w", newline="", buffering=1)
        self._writer = csv.writer(self._handle)
        self._writer.writerow(RAW_HEADER)
        self._handle.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is not None:
            try:
                self._handle.flush()
            finally:
                self._handle.close()  # always release the handle, even if flush fails
        self._handle = None
        self._writer = None

    def write(self, sample: RawSample) -> None:
        if self._writer is None:
            raise RuntimeError("Raw CSV recorder is not open")
        self._writer.writerow(_raw_row(sample, self.calibration))
        self.rows_written += 1
        if self._handle is not None and self.rows_written % self.flush_every_rows == 0:
            self._handle.flush()
