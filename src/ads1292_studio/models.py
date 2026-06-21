from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AdsPort:
    device: str
    description: str
    hwid: str


@dataclass(frozen=True)
class StreamStartResult:
    ok: bool
    error: str | None = None


@dataclass(frozen=True)
class StreamSample:
    timestamp: float
    ch1: int
    ch2: int
    board_heart_rate: int
    board_respiration_rate: int
    status_byte: int

    @property
    def lead_off_bits(self) -> int:
        return self.status_byte & 0x0F


@dataclass(frozen=True)
class RawSample:
    timestamp: float
    sample_index: int
    ch1_raw24: int
    ch2_raw24: int
    status_byte: int
    ch1_uv: float | None = None
    ch2_uv: float | None = None

    @property
    def lead_off_bits(self) -> int:
        return self.status_byte & 0x0F

    def as_stream_sample(self) -> StreamSample:
        return StreamSample(
            timestamp=self.timestamp,
            ch1=self.ch1_raw24,
            ch2=self.ch2_raw24,
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=self.status_byte,
        )


@dataclass(frozen=True)
class Recording:
    path: Path | None
    samples: tuple[StreamSample, ...]
    sample_rate_hz: float = 500.0

    @property
    def duration_seconds(self) -> float:
        if len(self.samples) < 2:
            return 0.0
        return self.samples[-1].timestamp - self.samples[0].timestamp


@dataclass(frozen=True)
class ChannelChoice:
    channel: str
    score_ch1: float
    score_ch2: float
    confidence: float


@dataclass(frozen=True)
class HeartRateSummary:
    median_bpm: float
    min_bpm: float
    max_bpm: float
    valid_rr_count: int


@dataclass(frozen=True)
class PqrstReview:
    qrs_clear: bool
    p_tentative: bool
    t_tentative: bool
    beats_used: int
    average_beat: tuple[float, ...]
    time_ms: tuple[float, ...]


@dataclass(frozen=True)
class ReviewResult:
    source: ChannelChoice
    peaks: tuple[int, ...]
    heart_rate: HeartRateSummary
    pqrst: PqrstReview
