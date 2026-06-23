from collections import deque

from ads1292_studio.gui_samples import append_live_sample_batch, live_buffer_samples
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


def test_live_buffer_samples_uses_absolute_index_for_timestamps() -> None:
    """After the ring buffer wraps, the first retained sample is NOT index 0.

    Rebuilding export samples must use the absolute stored index for timestamps
    so they share one time origin with event markers (recorded as
    sample_index / rate). enumerate() would re-zero the window and misplace
    event overlays in the exported report.
    """
    indices = deque([5000, 5500, 6000])  # wrapped: window no longer starts at 0
    ch1 = deque([10, 11, 12])
    ch2 = deque([-1, -2, -3])
    status = deque([1, 2, 3])

    out = live_buffer_samples(indices, ch1, ch2, status, sample_rate_hz=500.0)

    assert [s.timestamp for s in out] == [10.0, 11.0, 12.0]  # absolute, not 0/0.001/0.002
    assert [s.ch1 for s in out] == [10, 11, 12]
    assert [s.ch2 for s in out] == [-1, -2, -3]
    assert [s.status_byte for s in out] == [1, 2, 3]
    assert [s.sample_index for s in out] == [5000, 5500, 6000]


def test_live_buffer_samples_empty_returns_empty() -> None:
    out = live_buffer_samples(deque(), deque(), deque(), deque(), sample_rate_hz=500.0)
    assert out == ()
