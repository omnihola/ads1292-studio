from __future__ import annotations

from collections import deque
from typing import Iterable

from ads1292_studio.models import StreamSample


def live_buffer_samples(
    indices: Iterable[int],
    ch1: Iterable[float],
    ch2: Iterable[float],
    status: Iterable[int],
    *,
    sample_rate_hz: float,
) -> tuple[StreamSample, ...]:
    """Rebuild StreamSamples from the bounded live ring buffers for export.

    Timestamps use the ABSOLUTE stored sample index (``index / rate``), not the
    position within the retained window. The live deques are bounded
    (``maxlen``), so once acquisition exceeds that length the oldest samples are
    dropped and the window no longer starts at index 0. Event markers are
    recorded as ``sample_index / rate`` (absolute), so rebuilding with
    ``enumerate()`` would re-zero the window and misplace — or drop — event
    overlays in the exported report. Using ``indices`` keeps one shared origin.
    """
    return tuple(
        StreamSample(
            timestamp=index / sample_rate_hz,
            ch1=int(c1),
            ch2=int(c2),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=int(st),
            sample_index=int(index),
        )
        for index, c1, c2, st in zip(indices, ch1, ch2, status)
    )


def append_live_sample_batch(
    samples: tuple[StreamSample, ...],
    *,
    start_index: int,
    indices: deque[int],
    ch1: deque[float],
    ch2: deque[float],
    status: deque[int],
    board_hr: deque[int],
    board_rr: deque[int],
) -> tuple[int, StreamSample | None]:
    next_index = start_index
    latest = samples[-1] if samples else None
    for sample in samples:
        indices.append(next_index)
        next_index += 1
        ch1.append(sample.ch1)
        ch2.append(sample.ch2)
        status.append(sample.lead_off_bits)
        board_hr.append(sample.board_heart_rate)
        board_rr.append(sample.board_respiration_rate)
    return next_index, latest
