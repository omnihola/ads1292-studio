from __future__ import annotations

import argparse
from pathlib import Path
import time

import numpy as np

from ads1292_studio.csv_io import CsvRecorder, read_recording_csv
from ads1292_studio.device import Ads1x9xDevice, find_ads_port, list_ads_ports
from ads1292_studio.signal_processing import review_channels


def cmd_ports(_args: argparse.Namespace) -> int:
    ports = list_ads_ports()
    if not ports:
        print("No ADS1x9x ports found")
        return 1
    for port in ports:
        print(f"{port.device}\t{port.description}\t{port.hwid}")
    return 0


def _port_from_args(args: argparse.Namespace) -> str:
    port = args.port or find_ads_port()
    if not port:
        raise SystemExit("No port specified and no ADS1x9x port found")
    return port


def cmd_firmware(args: argparse.Namespace) -> int:
    with Ads1x9xDevice(_port_from_args(args)) as device:
        print(device.query_firmware())
    return 0


def cmd_stream(args: argparse.Namespace) -> int:
    port = _port_from_args(args)
    deadline = time.monotonic() + args.seconds
    with Ads1x9xDevice(port) as device:
        recorder_cm = CsvRecorder(args.csv) if args.csv else None
        recorder = recorder_cm.__enter__() if recorder_cm else None
        try:
            device.start_stream()
            count = 0
            for sample in device.iter_stream_samples():
                if recorder:
                    recorder.write(sample)
                count += 1
                if time.monotonic() >= deadline:
                    break
            print(f"samples={count}")
        finally:
            try:
                device.stop_stream()
            finally:
                if recorder_cm:
                    recorder_cm.__exit__(None, None, None)
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    recording = read_recording_csv(args.csv)
    ch1 = np.array([sample.ch1 for sample in recording.samples], dtype=float)
    ch2 = np.array([sample.ch2 for sample in recording.samples], dtype=float)
    result = review_channels(ch1, ch2, sample_rate_hz=recording.sample_rate_hz, source=args.source)
    print(f"samples={len(recording.samples)}")
    print(f"duration_s={recording.duration_seconds:.3f}")
    print(f"ecg_source={result.source.channel}")
    print(f"score_ch1={result.source.score_ch1:.2f}")
    print(f"score_ch2={result.source.score_ch2:.2f}")
    print(f"r_peaks={len(result.peaks)}")
    print(f"hr_median_bpm={result.heart_rate.median_bpm:.1f}")
    print(f"qrs_clear={result.pqrst.qrs_clear}")
    print(f"p_tentative={result.pqrst.p_tentative}")
    print(f"t_tentative={result.pqrst.t_tentative}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ADS1292 Studio CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ports").set_defaults(func=cmd_ports)
    firmware = sub.add_parser("firmware")
    firmware.add_argument("--port")
    firmware.set_defaults(func=cmd_firmware)
    stream = sub.add_parser("stream")
    stream.add_argument("--port")
    stream.add_argument("--seconds", type=float, default=10.0)
    stream.add_argument("--csv", type=Path)
    stream.set_defaults(func=cmd_stream)
    review = sub.add_parser("review")
    review.add_argument("csv", type=Path)
    review.add_argument("--source", choices=["Auto", "CH1", "CH2"], default="Auto")
    review.set_defaults(func=cmd_review)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
