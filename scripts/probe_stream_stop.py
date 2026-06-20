#!/usr/bin/env python3
"""Probe whether stop_stream() actually halts the ADS1292R ECG-FE data stream.

start_stream() and stop_stream() currently send the identical bytes (0x93,0,0).
This script settles, empirically and non-destructively, whether the firmware
treats 0x93 as a start/stop *toggle* (current code is correct) or whether stop
needs a distinct command (current code is a bug).

It only: queries the firmware version, starts streaming, reads frames, and stops
streaming. It writes no registers and changes no device configuration.

    python3 scripts/probe_stream_stop.py                       # auto-detect port
    python3 scripts/probe_stream_stop.py /dev/cu.usbmodemXXXX  # explicit port
"""
from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from ads1292_studio.device import (  # noqa: E402
    CMD_DATA_STREAMING,
    Ads1x9xDevice,
    find_ads_port,
)


def count_data_frames(device: Ads1x9xDevice, seconds: float) -> int:
    """Count streaming data frames seen within `seconds`, sending no commands."""
    end = time.monotonic() + seconds
    frames = 0
    while time.monotonic() < end:
        try:
            frame_type, payload = device.read_frame()
        except TimeoutError:
            continue
        if frame_type == CMD_DATA_STREAMING and len(payload) >= 59:
            frames += 1
    return frames


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else find_ads_port()
    if not port:
        print("No ADS1x9x port found. Plug in the board or pass the port explicitly.")
        return 1
    print(f"Port: {port}")

    try:
        device = Ads1x9xDevice(port)
        device.open()
    except Exception as exc:  # noqa: BLE001 - report any open failure plainly
        print(f"Could not open {port}: {exc}")
        print("Is the GUI app or another process holding the port? Close it and retry.")
        return 1

    try:
        print(f"Firmware: {device.query_firmware()}")

        device.start_stream()
        time.sleep(0.3)  # let streaming spin up
        before = count_data_frames(device, 1.0)
        print(f"[after START]  data frames in 1.0s: {before}")

        device.stop_stream()  # the identical 0x93,0,0 bytes under test
        time.sleep(0.3)  # let any in-flight frames arrive
        device.serial.reset_input_buffer()  # discard them; measure only NEW data
        after = count_data_frames(device, 1.0)
        print(f"[after STOP]   data frames in 1.0s: {after}")

        print("\n--- verdict ---")
        if before > 0 and after == 0:
            print("TOGGLE CONFIRMED: stop_stream() halts the stream -> current code is CORRECT.")
            return 0
        if before > 0 and after > 0:
            print("BUG: stream keeps flowing after stop_stream() -> 0x93 is NOT a toggle;")
            print("     a distinct stop command/param is required.")
            return 2
        print("INCONCLUSIVE: no data after START. Check board power/leads, or that")
        print("     streaming actually began, then re-run.")
        return 3
    finally:
        device.close()


if __name__ == "__main__":
    raise SystemExit(main())
