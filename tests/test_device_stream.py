import itertools

import pytest

from ads1292_studio.device import Ads1x9xDevice


_START = 0x02
_DATA_STREAMING = 0x93
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


def test_iter_stream_samples_propagates_non_timeout_errors() -> None:
    device = Ads1x9xDevice("fake-port")
    device.serial = _RaisingSerial(RuntimeError("device disconnected"))

    with pytest.raises(RuntimeError, match="device disconnected"):
        list(itertools.islice(device.iter_stream_samples(), 1))
