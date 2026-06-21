from ads1292_studio.device import Ads1x9xDevice, parse_stream_payload


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
