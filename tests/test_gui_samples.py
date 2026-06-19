from collections import deque

from ads1292_studio.gui_samples import append_live_sample_batch
from ads1292_studio.models import StreamSample


def _sample(index: int, *, status_byte: int = 0) -> StreamSample:
    return StreamSample(
        timestamp=index / 500.0,
        ch1=index + 10,
        ch2=index + 20,
        board_heart_rate=70 + index,
        board_respiration_rate=12 + index,
        status_byte=status_byte,
    )


def test_append_live_sample_batch_updates_buffers_and_returns_latest() -> None:
    indices: deque[int] = deque(maxlen=10)
    ch1: deque[float] = deque(maxlen=10)
    ch2: deque[float] = deque(maxlen=10)
    status: deque[int] = deque(maxlen=10)
    board_hr: deque[int] = deque(maxlen=10)
    board_rr: deque[int] = deque(maxlen=10)
    samples = (_sample(0, status_byte=0x11), _sample(1, status_byte=0x2F))

    next_index, latest = append_live_sample_batch(
        samples,
        start_index=5,
        indices=indices,
        ch1=ch1,
        ch2=ch2,
        status=status,
        board_hr=board_hr,
        board_rr=board_rr,
    )

    assert next_index == 7
    assert latest == samples[-1]
    assert list(indices) == [5, 6]
    assert list(ch1) == [10, 11]
    assert list(ch2) == [20, 21]
    assert list(status) == [0x01, 0x0F]
    assert list(board_hr) == [70, 71]
    assert list(board_rr) == [12, 13]


def test_append_live_sample_batch_keeps_empty_batch_noop() -> None:
    indices: deque[int] = deque([1], maxlen=10)
    ch1: deque[float] = deque([2.0], maxlen=10)
    ch2: deque[float] = deque([3.0], maxlen=10)
    status: deque[int] = deque([4], maxlen=10)
    board_hr: deque[int] = deque([5], maxlen=10)
    board_rr: deque[int] = deque([6], maxlen=10)

    next_index, latest = append_live_sample_batch(
        tuple(),
        start_index=9,
        indices=indices,
        ch1=ch1,
        ch2=ch2,
        status=status,
        board_hr=board_hr,
        board_rr=board_rr,
    )

    assert next_index == 9
    assert latest is None
    assert list(indices) == [1]
    assert list(ch1) == [2.0]
    assert list(ch2) == [3.0]
    assert list(status) == [4]
    assert list(board_hr) == [5]
    assert list(board_rr) == [6]
