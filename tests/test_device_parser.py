from ads1292_studio.device import Ads1x9xDevice, parse_acquire_payload, parse_stream_payload


def _payload_with_trailer(trailer: tuple[int, int]) -> bytes:
    payload = bytearray([88, 21, 0x10])
    for index in range(14):
        ch1 = index - 7
        ch2 = 100 + index
        payload.extend(int(ch1).to_bytes(2, "little", signed=True))
        payload.extend(int(ch2).to_bytes(2, "little", signed=True))
    payload.extend(trailer)
    return bytes(payload)


def test_device_default_timeout_is_short_enough_to_notice_stop_promptly() -> None:
    device = Ads1x9xDevice("fake-port")

    assert device.timeout == 0.2


def test_parse_stream_payload_extracts_status_and_fourteen_sample_pairs() -> None:
    samples = parse_stream_payload(
        _payload_with_trailer((0x03, 0x03)),
        start_timestamp=10.0,
        sample_rate_hz=500.0,
        start_index=0,
    )

    assert len(samples) == 14
    assert samples[0].timestamp == 10.0
    assert samples[1].timestamp == 10.002
    assert samples[0].ch1 == -7
    assert samples[-1].ch2 == 113
    assert samples[0].board_heart_rate == 88
    assert samples[0].board_respiration_rate == 21
    assert samples[0].status_byte == 0x10
    assert samples[0].lead_off_bits == 0


def test_parse_stream_payload_accepts_ti_usb_linefeed_trailer() -> None:
    samples = parse_stream_payload(
        _payload_with_trailer((0x03, 0x0A)),
        start_timestamp=10.0,
        sample_rate_hz=500.0,
        start_index=0,
    )

    assert len(samples) == 14
    assert samples[-1].ch2 == 113


def test_parse_stream_payload_rejects_bad_trailer() -> None:
    try:
        parse_stream_payload(
            _payload_with_trailer((0x00, 0x03)),
            start_timestamp=10.0,
            sample_rate_hz=500.0,
            start_index=0,
        )
    except ValueError as exc:
        assert "bad stream trailer" in str(exc)
    else:
        raise AssertionError("bad stream trailer was accepted")


def _s24be(value: int) -> bytes:
    if value < 0:
        value += 1 << 24
    return int(value).to_bytes(3, "big", signed=False)


def test_parse_acquire_payload_extracts_eight_24_bit_sample_pairs() -> None:
    payload = bytearray([0xAB, 0xCD])
    expected_ch1: list[int] = []
    expected_ch2: list[int] = []
    for index in range(8):
        ch1 = -20_000 + index
        ch2 = 42_000 - index
        expected_ch1.append(ch1)
        expected_ch2.append(ch2)
        payload.extend(_s24be(ch1))
        payload.extend(_s24be(ch2))
    payload.append(0x03)

    samples = parse_acquire_payload(
        bytes(payload),
        start_timestamp=3.0,
        sample_rate_hz=500.0,
        start_index=16,
    )

    assert len(samples) == 8
    assert [sample.ch1_raw24 for sample in samples] == expected_ch1
    assert [sample.ch2_raw24 for sample in samples] == expected_ch2
    assert samples[0].timestamp == 3.032
    assert samples[1].timestamp == 3.034
    assert samples[0].status_byte == 0xABCD
    assert samples[-1].sample_index == 23


def test_parse_acquire_payload_rejects_bad_end_marker() -> None:
    payload = bytes([0x00, 0x00] + [0x00] * 48 + [0x0A])

    try:
        parse_acquire_payload(
            payload,
            start_timestamp=0.0,
            sample_rate_hz=500.0,
            start_index=0,
        )
    except ValueError as exc:
        assert "bad acquire trailer" in str(exc)
    else:
        raise AssertionError("bad acquire trailer was accepted")


def test_parse_stream_payload_rejects_truncated_frame() -> None:
    """A short USB frame must fail loudly, not silently decode garbage samples."""
    truncated = _payload_with_trailer((0x03, 0x03))[:40]  # < 61 bytes

    try:
        parse_stream_payload(truncated, start_timestamp=0.0, sample_rate_hz=500.0, start_index=0)
    except ValueError as exc:
        assert "too short" in str(exc)
    else:
        raise AssertionError("truncated stream payload was accepted")


def test_parse_acquire_payload_rejects_truncated_frame() -> None:
    truncated = bytes([0x00, 0x00] + [0x00] * 20 + [0x03])  # < 51 bytes

    try:
        parse_acquire_payload(truncated, start_timestamp=0.0, sample_rate_hz=500.0, start_index=0)
    except ValueError as exc:
        assert "too short" in str(exc)
    else:
        raise AssertionError("truncated acquire payload was accepted")
