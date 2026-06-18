from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AdsPort:
    device: str
    description: str
    hwid: str


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
