from ads1292_studio.device import parse_stream_payload


def test_parse_stream_payload_extracts_status_and_fourteen_sample_pairs() -> None:
    payload = bytearray([88, 21, 0x10])
    for index in range(14):
        ch1 = index - 7
        ch2 = 100 + index
        payload.extend(int(ch1).to_bytes(2, "little", signed=True))
        payload.extend(int(ch2).to_bytes(2, "little", signed=True))
    payload.extend([0x03, 0x03])

    samples = parse_stream_payload(bytes(payload), start_timestamp=10.0, sample_rate_hz=500.0, start_index=0)

    assert len(samples) == 14
    assert samples[0].timestamp == 10.0
    assert samples[1].timestamp == 10.002
    assert samples[0].ch1 == -7
    assert samples[-1].ch2 == 113
    assert samples[0].board_heart_rate == 88
    assert samples[0].board_respiration_rate == 21
    assert samples[0].status_byte == 0x10
    assert samples[0].lead_off_bits == 0
