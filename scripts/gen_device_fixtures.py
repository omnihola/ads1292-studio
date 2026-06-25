from __future__ import annotations

from pathlib import Path

from ads1292_studio.device import (
    END,
    parse_acquire_payload,
    parse_stream_payload,
)
from scripts.fixture_io import dump_fixture, to_hex

SAMPLE_RATE = 500.0


def _stream_payload_bytes() -> bytes:
    # 3-byte header (hr, resp, status) + 14 samples * 4 bytes (ch1 LE, ch2 LE) + 2-byte trailer.
    header = bytes([72, 18, 0x05])  # heart_rate=72, resp=18, status=0x05 (lead_off bits 0101)
    body = bytearray()
    for i in range(14):
        ch1 = 100 + i
        ch2 = -200 + i
        body += bytes([ch1 & 0xFF, (ch1 >> 8) & 0xFF, ch2 & 0xFF, (ch2 >> 8) & 0xFF])
    return header + bytes(body) + bytes([END, END])


def _acquire_payload_bytes() -> bytes:
    # 2-byte status + 8 samples * 6 bytes (ch1 24b BE, ch2 24b BE) + 1-byte END trailer.
    status = bytes([0x00, 0x05])
    body = bytearray()
    for i in range(8):
        ch1 = 1000 + i
        ch2 = -2000 - i
        body += (ch1 & 0xFFFFFF).to_bytes(3, "big")
        body += (ch2 & 0xFFFFFF).to_bytes(3, "big")
    return status + bytes(body) + bytes([END])


def _sample_dict(sample) -> dict:
    keys = ("timestamp", "ch1", "ch2", "board_heart_rate", "board_respiration_rate",
            "status_byte", "sample_index", "ch1_raw24", "ch2_raw24")
    out = {}
    for key in keys:
        if hasattr(sample, key):
            out[key] = getattr(sample, key)
    out["lead_off_bits"] = sample.lead_off_bits
    return out


def generate(root: Path) -> list[Path]:
    out_dir = Path(root) / "device_parser"
    written: list[Path] = []

    stream_bytes = _stream_payload_bytes()
    stream_samples = parse_stream_payload(stream_bytes, start_timestamp=0.0,
                                          sample_rate_hz=SAMPLE_RATE, start_index=0)
    written.append(_write(out_dir / "stream_payload_nominal.json", {
        "schema_version": 1, "category": "device_parser", "name": "stream_payload_nominal",
        "oracle": {"function": "ads1292_studio.device.parse_stream_payload"},
        "input": {"payload_hex": to_hex(stream_bytes), "start_timestamp": 0.0,
                  "sample_rate_hz": SAMPLE_RATE, "start_index": 0},
        "output": {"samples": [_sample_dict(s) for s in stream_samples]},
        "tolerance": {"kind": "exact"},
        "notes": "14 stream samples, int16 LE ch1/ch2, lead_off_bits from status low nibble",
    }))

    acquire_bytes = _acquire_payload_bytes()
    acquire_samples = parse_acquire_payload(acquire_bytes, start_timestamp=0.0,
                                            sample_rate_hz=SAMPLE_RATE, start_index=0)
    written.append(_write(out_dir / "acquire_payload_nominal.json", {
        "schema_version": 1, "category": "device_parser", "name": "acquire_payload_nominal",
        "oracle": {"function": "ads1292_studio.device.parse_acquire_payload"},
        "input": {"payload_hex": to_hex(acquire_bytes), "start_timestamp": 0.0,
                  "sample_rate_hz": SAMPLE_RATE, "start_index": 0},
        "output": {"samples": [_sample_dict(s) for s in acquire_samples]},
        "tolerance": {"kind": "exact"},
        "notes": "8 raw samples, int24 BE ch1/ch2, 16-bit status word",
    }))

    # Error oracles: capture exception type + message substring.
    written.append(_write_error(out_dir / "stream_bad_trailer.json", "stream_bad_trailer",
        "ads1292_studio.device.parse_stream_payload",
        stream_bytes[:-2] + bytes([0x00, 0x00]), "trailer"))
    written.append(_write_error(out_dir / "stream_too_short.json", "stream_too_short",
        "ads1292_studio.device.parse_stream_payload",
        stream_bytes[:40], "too short"))
    written.append(_write_error(out_dir / "acquire_bad_trailer.json", "acquire_bad_trailer",
        "ads1292_studio.device.parse_acquire_payload",
        acquire_bytes[:-1] + bytes([0x00]), "trailer"))
    return written


def _write(path: Path, payload: dict) -> Path:
    dump_fixture(payload, path)
    return path


def _write_error(path: Path, name: str, function: str, payload: bytes, message_contains: str) -> Path:
    func = {"ads1292_studio.device.parse_stream_payload": parse_stream_payload,
            "ads1292_studio.device.parse_acquire_payload": parse_acquire_payload}[function]
    try:
        func(payload, start_timestamp=0.0, sample_rate_hz=SAMPLE_RATE, start_index=0)
        raise AssertionError(f"expected {function} to raise on crafted payload")
    except ValueError as exc:
        assert message_contains in str(exc), f"message {str(exc)!r} lacks {message_contains!r}"
    dump_fixture({
        "schema_version": 1, "category": "device_parser", "name": name,
        "oracle": {"function": function},
        "input": {"payload_hex": to_hex(payload), "start_timestamp": 0.0,
                  "sample_rate_hz": SAMPLE_RATE, "start_index": 0},
        "output": {"raises": "ValueError", "message_contains": message_contains},
        "tolerance": {"kind": "exact"},
        "notes": "error oracle: malformed payload must raise ValueError",
    }, path)
    return path
