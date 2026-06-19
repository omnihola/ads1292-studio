from __future__ import annotations

from collections import deque

from ads1292_studio.models import StreamSample


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
