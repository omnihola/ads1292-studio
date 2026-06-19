from __future__ import annotations

import argparse
from pathlib import Path
import time

import numpy as np

from ads1292_studio.batch import export_batch_summary
from ads1292_studio.calibration import calibration_template, read_calibration_json, write_calibration_json
from ads1292_studio.csv_io import CsvRecorder, read_recording_csv
from ads1292_studio.device import Ads1x9xDevice, find_ads_port, list_ads_ports
from ads1292_studio.events import event_template, read_events_json, write_events_json
from ads1292_studio.metadata import metadata_template, read_metadata_json, write_metadata_json
from ads1292_studio.protocol import protocol_template, read_protocol_json, write_protocol_json
from ads1292_studio.quality import compute_quality_metrics
from ads1292_studio.quality_gate import QualityGate, evaluate_quality_gate
from ads1292_studio.report import export_review_report
from ads1292_studio.session_package import export_session_package, verify_session_package
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
    metrics = compute_quality_metrics(recording.samples, sample_rate_hz=recording.sample_rate_hz, source=args.source)
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
    print(f"baseline_drift_counts={metrics.baseline_drift_counts:.1f}")
    print(f"noise_rms_counts={metrics.noise_rms_counts:.1f}")
    print(f"peak_to_peak_counts={metrics.peak_to_peak_counts:.1f}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    if args.write_meta_template:
        write_metadata_json(args.write_meta_template, metadata_template())
        print(f"metadata_template={args.write_meta_template}")
        return 0
    if args.write_events_template:
        write_events_json(args.write_events_template, event_template())
        print(f"events_template={args.write_events_template}")
        return 0
    if args.write_calibration_template:
        write_calibration_json(args.write_calibration_template, calibration_template())
        print(f"calibration_template={args.write_calibration_template}")
        return 0
    if args.write_protocol_template:
        write_protocol_json(args.write_protocol_template, protocol_template())
        print(f"protocol_template={args.write_protocol_template}")
        return 0
    if args.csv is None:
        raise SystemExit("CSV path is required unless writing a template")
    recording = read_recording_csv(args.csv)
    metadata = read_metadata_json(args.meta) if args.meta else None
    events = read_events_json(args.events) if args.events else tuple()
    calibration = read_calibration_json(args.calibration) if args.calibration else calibration_template()
    protocol = read_protocol_json(args.protocol) if args.protocol else None
    export = export_review_report(
        samples=recording.samples,
        out_dir=args.out,
        title=args.title,
        sample_rate_hz=recording.sample_rate_hz,
        source=args.source,
        metadata=metadata,
        events=events,
        calibration=calibration,
        protocol=protocol,
    )
    print(f"html={export.html_path}")
    print(f"ecg_png={export.ecg_png_path}")
    print(f"pqrst_png={export.pqrst_png_path}")
    print(f"ecg_source={export.metrics.ecg_source}")
    print(f"quality={export.metrics.quality_label}")
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    export = export_batch_summary(paths=args.csvs, out_dir=args.out, title=args.title)
    print(f"csv={export.csv_path}")
    print(f"group_csv={export.group_csv_path}")
    print(f"html={export.html_path}")
    print(f"png={export.png_path}")
    print(f"rows={len(export.rows)}")
    print(f"groups={len(export.group_summaries)}")
    return 0


def cmd_package(args: argparse.Namespace) -> int:
    export = export_session_package(csv_path=args.csv, out_dir=args.out, title=args.title, source=args.source)
    print(f"package={export.package_dir}")
    print(f"manifest={export.manifest_path}")
    print(f"report_html={export.report_html_path}")
    return 0


def cmd_verify_package(args: argparse.Namespace) -> int:
    result = verify_session_package(args.manifest)
    print(f"manifest={result.manifest_path}")
    print(f"checked_files={result.checked_files}")
    print(f"ok={result.ok}")
    for failure in result.failures:
        print(f"failure={failure}")
    return 0 if result.ok else 2


def cmd_qc(args: argparse.Namespace) -> int:
    recording = read_recording_csv(args.csv)
    metrics = compute_quality_metrics(recording.samples, sample_rate_hz=recording.sample_rate_hz, source=args.source)
    gate = QualityGate(
        min_duration_seconds=args.min_duration,
        min_contact_ok_percent=args.min_contact,
        min_r_peaks=args.min_r_peaks,
        min_hr_bpm=args.min_hr,
        max_hr_bpm=args.max_hr,
        require_qrs_clear=not args.allow_unclear_qrs,
        max_baseline_drift_counts=args.max_baseline_drift,
        max_noise_rms_counts=args.max_noise_rms,
        max_peak_to_peak_counts=args.max_peak_to_peak,
    )
    result = evaluate_quality_gate(metrics, gate)
    print(f"quality_gate={result.label}")
    print(f"ecg_source={metrics.ecg_source}")
    print(f"quality={metrics.quality_label}")
    print(f"baseline_drift_counts={metrics.baseline_drift_counts:.1f}")
    print(f"noise_rms_counts={metrics.noise_rms_counts:.1f}")
    print(f"peak_to_peak_counts={metrics.peak_to_peak_counts:.1f}")
    for failure in result.failures:
        print(f"failure={failure}")
    return 0 if result.passed else 2


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
    report = sub.add_parser("report")
    report.add_argument("csv", type=Path, nargs="?")
    report.add_argument("--out", type=Path, default=Path("reports"))
    report.add_argument("--title", default="ADS1292 Studio Review")
    report.add_argument("--source", choices=["Auto", "CH1", "CH2"], default="Auto")
    report.add_argument("--meta", type=Path)
    report.add_argument("--events", type=Path)
    report.add_argument("--calibration", type=Path)
    report.add_argument("--protocol", type=Path)
    report.add_argument("--write-meta-template", type=Path)
    report.add_argument("--write-events-template", type=Path)
    report.add_argument("--write-calibration-template", type=Path)
    report.add_argument("--write-protocol-template", type=Path)
    report.set_defaults(func=cmd_report)
    batch = sub.add_parser("batch")
    batch.add_argument("csvs", type=Path, nargs="+")
    batch.add_argument("--out", type=Path, default=Path("reports/batch"))
    batch.add_argument("--title", default="ADS1292 Batch Summary")
    batch.set_defaults(func=cmd_batch)
    package = sub.add_parser("package")
    package.add_argument("csv", type=Path)
    package.add_argument("--out", type=Path, default=Path("packages"))
    package.add_argument("--title", default="ADS1292 Session Package")
    package.add_argument("--source", choices=["Auto", "CH1", "CH2"], default="Auto")
    package.set_defaults(func=cmd_package)
    verify = sub.add_parser("verify-package")
    verify.add_argument("manifest", type=Path)
    verify.set_defaults(func=cmd_verify_package)
    qc = sub.add_parser("qc")
    qc.add_argument("csv", type=Path)
    qc.add_argument("--source", choices=["Auto", "CH1", "CH2"], default="Auto")
    qc.add_argument("--min-duration", type=float, default=8.0)
    qc.add_argument("--min-contact", type=float, default=95.0)
    qc.add_argument("--min-r-peaks", type=int, default=5)
    qc.add_argument("--min-hr", type=float, default=35.0)
    qc.add_argument("--max-hr", type=float, default=180.0)
    qc.add_argument("--max-baseline-drift", type=float)
    qc.add_argument("--max-noise-rms", type=float)
    qc.add_argument("--max-peak-to-peak", type=float)
    qc.add_argument("--allow-unclear-qrs", action="store_true")
    qc.set_defaults(func=cmd_qc)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
