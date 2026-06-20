from __future__ import annotations

import time
from typing import Iterable

import serial
from serial.tools import list_ports

from ads1292_studio.models import AdsPort, StreamSample


VID_TI = 0x2047
PID_ADS1X9X = 0x0300
SERIAL_CANDIDATE_MARKERS = ("usbmodem", "usbserial")

START = 0x02
END = 0x03

CMD_REG_READ = 0x92
CMD_DATA_STREAMING = 0x93
CMD_ACQUIRE_DATA = 0x94
CMD_QUERY_FIRMWARE_VERSION = 0x99


def _is_ads_candidate_port(port: object) -> bool:
    device = str(getattr(port, "device", "") or "")
    description = str(getattr(port, "description", "") or "")
    is_ti_ads = (
        getattr(port, "vid", None) == VID_TI
        and getattr(port, "pid", None) == PID_ADS1X9X
    )
    is_named_ads = "ADS1x9x" in description
    is_usb_serial_candidate = any(
        marker in device.lower()
        for marker in SERIAL_CANDIDATE_MARKERS
    )
    return is_ti_ads or is_named_ads or is_usb_serial_candidate


def _int16_le(lo: int, hi: int) -> int:
    value = (hi << 8) | lo
    if value & 0x8000:
        value -= 0x10000
    return value


def list_ads_ports() -> list[AdsPort]:
    ports: list[AdsPort] = []
    for port in list_ports.comports():
        if _is_ads_candidate_port(port):
            ports.append(AdsPort(port.device, port.description or "", port.hwid or ""))
    return ports


def find_ads_port() -> str | None:
    ports = list_ads_ports()
    if ports:
        return ports[0].device
    return None


def parse_stream_payload(
    payload: bytes,
    start_timestamp: float,
    sample_rate_hz: float,
    start_index: int,
) -> tuple[StreamSample, ...]:
    if len(payload) < 59:
        raise ValueError(f"stream payload too short: {len(payload)} bytes")
    board_heart_rate = payload[0]
    board_respiration_rate = payload[1]
    status_byte = payload[2]
    samples: list[StreamSample] = []
    for index in range(14):
        base = 3 + index * 4
        timestamp = round(start_timestamp + ((start_index + index) / sample_rate_hz), 6)
        samples.append(
            StreamSample(
                timestamp=timestamp,
                ch1=_int16_le(payload[base], payload[base + 1]),
                ch2=_int16_le(payload[base + 2], payload[base + 3]),
                board_heart_rate=board_heart_rate,
                board_respiration_rate=board_respiration_rate,
                status_byte=status_byte,
            )
        )
    return tuple(samples)


class Ads1x9xDevice:
    def __init__(
        self,
        port: str,
        baudrate: int = 9600,
        timeout: float = 0.2,
        sample_rate_hz: float = 500.0,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.sample_rate_hz = sample_rate_hz
        self.serial: serial.Serial | None = None
        self.streaming = False
        self._stream_t0: float | None = None
        self._stream_sample_index = 0

    def __enter__(self) -> "Ads1x9xDevice":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self) -> None:
        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.timeout,
            write_timeout=self.timeout,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False,
        )
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()

    def close(self) -> None:
        if self.serial is None:
            return
        if self.streaming:
            try:
                self.stop_stream()
            except Exception:
                pass
        self.serial.close()
        self.serial = None

    def _require_serial(self) -> serial.Serial:
        if self.serial is None:
            raise RuntimeError("Device is not open")
        return self.serial

    def write_cmd(self, cmd: int, param0: int = 0, param1: int = 0) -> None:
        ser = self._require_serial()
        packet = bytes([START, cmd & 0xFF, param0 & 0xFF, param1 & 0xFF, END, END, 0x0A])
        ser.write(packet)
        ser.flush()

    def _read_exact(self, nbytes: int) -> bytes:
        ser = self._require_serial()
        data = ser.read(nbytes)
        if len(data) != nbytes:
            raise TimeoutError(f"Expected {nbytes} bytes, got {len(data)}")
        return data

    def read_frame(self) -> tuple[int, bytes]:
        while True:
            byte = self._read_exact(1)[0]
            if byte == START:
                break
        frame_type = self._read_exact(1)[0]
        if frame_type == CMD_DATA_STREAMING:
            payload = self._read_exact(61)
        elif frame_type in (CMD_REG_READ, CMD_QUERY_FIRMWARE_VERSION):
            payload = self._read_exact(5)
        elif frame_type == CMD_ACQUIRE_DATA:
            payload = self._read_exact(51)
        else:
            payload = self._read_exact(1)
        return frame_type, payload

    def query_firmware(self) -> str:
        self.write_cmd(CMD_QUERY_FIRMWARE_VERSION)
        deadline = time.monotonic() + 2.0
        last_unexpected = ""
        while time.monotonic() < deadline:
            frame_type, payload = self.read_frame()
            if frame_type == CMD_QUERY_FIRMWARE_VERSION:
                if len(payload) >= 2:
                    return f"{payload[0]}.{payload[1]}"
                return payload.hex(" ")
            last_unexpected = f"0x{frame_type:02X}: {payload.hex(' ')}"
        return f"no firmware response; last frame {last_unexpected}"

    def read_register(self, register: int) -> int:
        self.write_cmd(CMD_REG_READ, register, 0)
        frame_type, payload = self.read_frame()
        if frame_type != CMD_REG_READ or len(payload) < 2:
            raise RuntimeError(f"Unexpected register response: 0x{frame_type:02X} {payload.hex(' ')}")
        return payload[1]

    def start_stream(self) -> None:
        self._stream_t0 = time.time()
        self._stream_sample_index = 0
        self.write_cmd(CMD_DATA_STREAMING, 0, 0)
        self.streaming = True

    def stop_stream(self) -> None:
        self.write_cmd(CMD_DATA_STREAMING, 0, 0)
        self.streaming = False

    def iter_stream_samples(self) -> Iterable[StreamSample]:
        while True:
            frame_type, payload = self.read_frame()
            if frame_type != CMD_DATA_STREAMING or len(payload) < 59:
                continue
            if self._stream_t0 is None:
                self._stream_t0 = time.time()
            samples = parse_stream_payload(
                payload,
                start_timestamp=self._stream_t0,
                sample_rate_hz=self.sample_rate_hz,
                start_index=self._stream_sample_index,
            )
            self._stream_sample_index += len(samples)
            yield from samples
