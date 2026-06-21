import itertools

import pytest

from ads1292_studio.device import Ads1x9xDevice
from ads1292_studio.models import StreamSample


_START = 0x02
_DATA_STREAMING = 0x93
_ACQUIRE_DATA = 0x94
_END = 0x03


def _data_payload(*, ch1_base: int) -> bytes:
    """Build a 61-byte streaming payload (3 header + 14*4 samples + 2 trailing)."""
    payload = bytearray([60, 12, 0x00])  # heart rate, respiration rate, status
    for index in range(14):
        payload += int(ch1_base + index).to_bytes(2, "little", signed=True)
        payload += int(1000 + index).to_bytes(2, "little", signed=True)
    payload += bytes([_END, _END])
    return bytes(payload)


class _ScriptedSerial:
    """Serial stub returning pre-sized chunks in order.

    A scripted chunk of ``b""`` mimics a pyserial read timeout: it returns fewer
    bytes than requested, which ``Ads1x9xDevice._read_exact`` turns into a
    ``TimeoutError``.
    """

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    def read(self, _nbytes: int) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

    def write(self, data: bytes) -> int:
        self.written = getattr(self, "written", b"") + data
        return len(data)

    def flush(self) -> None:
        return None

    def reset_input_buffer(self) -> None:
        return None

    def reset_output_buffer(self) -> None:
        return None


class _RaisingSerial:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def read(self, _nbytes: int) -> bytes:
        raise self._error


def test_iter_stream_samples_survives_transient_read_timeout() -> None:
    device = Ads1x9xDevice("fake-port")
    device.serial = _ScriptedSerial(
        [
            bytes([_START]), bytes([_DATA_STREAMING]), _data_payload(ch1_base=0),
            b"",  # transient timeout sandwiched between two healthy frames
            bytes([_START]), bytes([_DATA_STREAMING]), _data_payload(ch1_base=100),
        ]
    )

    samples = list(itertools.islice(device.iter_stream_samples(), 28))

    assert len(samples) == 28
    assert samples[0].ch1 == 0
    assert samples[14].ch1 == 100  # the frame after the timeout still arrives


def test_iter_stream_samples_stops_when_should_continue_returns_false() -> None:
    device = Ads1x9xDevice("fake-port")
    device.serial = _ScriptedSerial(
        [bytes([_START]), bytes([_DATA_STREAMING]), _data_payload(ch1_base=0)]
    )
    calls = {"n": 0}

    def should_continue() -> bool:
        calls["n"] += 1
        return calls["n"] <= 1  # allow one frame, then ask the stream to stop

    samples = list(device.iter_stream_samples(should_continue=should_continue))

    assert len(samples) == 14
    assert calls["n"] == 2


def test_stream_started_samples_use_relative_timestamps() -> None:
    device = Ads1x9xDevice("fake-port")
    device.serial = _ScriptedSerial(
        [bytes([_START]), bytes([_DATA_STREAMING]), _data_payload(ch1_base=0)]
    )

    device.start_stream()
    samples = device.read_stream_sample_batch()

    assert samples[0].timestamp == 0.0
    assert samples[1].timestamp == 0.002


def test_iter_stream_samples_propagates_non_timeout_errors() -> None:
    device = Ads1x9xDevice("fake-port")
    device.serial = _RaisingSerial(RuntimeError("device disconnected"))

    with pytest.raises(RuntimeError, match="device disconnected"):
        list(itertools.islice(device.iter_stream_samples(), 1))


def _s24be(value: int) -> bytes:
    if value < 0:
        value += 1 << 24
    return int(value).to_bytes(3, "big", signed=False)


def _acquire_payload() -> bytes:
    payload = bytearray([0x12, 0x30])
    for index in range(8):
        payload.extend(_s24be(100 + index))
        payload.extend(_s24be(-200 - index))
    payload.append(_END)
    return bytes(payload)


def test_acquire_raw_samples_tolerates_transient_empty_serial_reads() -> None:
    device = Ads1x9xDevice("fake-port")
    device.serial = _ScriptedSerial(
        [
            b"",
            bytes([_START]),
            bytes([_ACQUIRE_DATA]),
            bytes([0x00]),
            bytes([0x08]),
            bytes([_END]),
            b"",
            bytes([_START]),
            bytes([_ACQUIRE_DATA]),
            _acquire_payload(),
        ]
    )

    samples = device.acquire_raw_samples(8)

    assert len(samples) == 8
    assert samples[0].ch1_raw24 == 100
    assert samples[0].ch2_raw24 == -200
    assert samples[-1].ch1_raw24 == 107


def test_run_live_stream_calibration_uses_internal_test_signal_and_restores_registers() -> None:
    device = Ads1x9xDevice("fake-port")
    registers = {0x02: 0xE0, 0x05: 0x00}
    writes: list[tuple[int, int]] = []
    stream_starts = 0
    stream_stops = 0
    batches = [
        tuple(
            StreamSample(
                timestamp=float(index),
                ch1=0,
                ch2=0 if index % 2 == 0 else 1064,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            )
            for index in range(20)
        )
        for _ in range(2)
    ]

    def read_register(register: int) -> int:
        return registers[register]

    def write_register(register: int, value: int) -> None:
        writes.append((register, value))
        registers[register] = value

    def start_stream() -> None:
        nonlocal stream_starts
        stream_starts += 1

    def stop_stream() -> None:
        nonlocal stream_stops
        stream_stops += 1

    def read_stream_sample_batch() -> tuple[StreamSample, ...]:
        return batches.pop(0) if batches else tuple()

    device.read_register = read_register  # type: ignore[method-assign]
    device.write_register = write_register  # type: ignore[method-assign]
    device.start_stream = start_stream  # type: ignore[method-assign]
    device.stop_stream = stop_stream  # type: ignore[method-assign]
    device.read_stream_sample_batch = read_stream_sample_batch  # type: ignore[method-assign]

    calibration = device.run_live_stream_calibration(runs=2, samples_per_run=20)

    assert stream_starts == 2
    assert stream_stops == 2
    assert calibration.runs == 2
    assert 1.89 < calibration.mean_uv_per_count < 1.90
    assert writes[:2] == [(0x02, 0xE3), (0x05, 0x05)]
    assert writes[-2:] == [(0x05, 0x00), (0x02, 0xE0)]
