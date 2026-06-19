from pathlib import Path

from ads1292_studio.calibration import Calibration, read_calibration_json, write_calibration_json
from ads1292_studio.cli import main
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol, read_protocol_json, write_protocol_json


def _write_small_csv(path: Path) -> None:
    samples = tuple(
        StreamSample(
            timestamp=index / 500.0,
            ch1=0,
            ch2=1000 if index % 50 == 0 else 0,
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index in range(500)
    )
    write_recording_csv(path, samples)


def test_cli_writes_calibration_template(tmp_path: Path) -> None:
    path = tmp_path / "calibration-template.json"

    assert main(["report", "--write-calibration-template", str(path)]) == 0

    assert read_calibration_json(path).label == "ADS1292 default"


def test_cli_report_uses_calibration_json(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    calibration_path = tmp_path / "calibration.json"
    out_dir = tmp_path / "report"
    _write_small_csv(csv_path)
    write_calibration_json(
        calibration_path,
        Calibration(vref_mv=1210.0, pga_gain=3.0, adc_bits=24, label="half-vref-gain-3"),
    )

    assert (
        main(
            [
                "report",
                str(csv_path),
                "--calibration",
                str(calibration_path),
                "--out",
                str(out_dir),
                "--title",
                "CLI Calibration",
            ]
        )
        == 0
    )

    html = next(out_dir.glob("*.html")).read_text()
    assert "half-vref-gain-3" in html
    assert "1.210 V" in html


def test_cli_writes_protocol_template(tmp_path: Path) -> None:
    path = tmp_path / "protocol-template.json"

    assert main(["report", "--write-protocol-template", str(path)]) == 0

    assert read_protocol_json(path).steps[0].label == "baseline"


def test_cli_report_uses_protocol_json(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    protocol_path = tmp_path / "protocol.json"
    out_dir = tmp_path / "report"
    _write_small_csv(csv_path)
    write_protocol_json(
        protocol_path,
        TestProtocol(
            name="CLI protocol",
            objective="Confirm protocol appears in report.",
            steps=(ProtocolStep(start_seconds=0.0, duration_seconds=1.0, label="baseline", instruction="Sit still."),),
        ),
    )

    assert main(["report", str(csv_path), "--protocol", str(protocol_path), "--out", str(out_dir)]) == 0

    html = next(out_dir.glob("*.html")).read_text()
    assert "Test Protocol" in html
    assert "CLI protocol" in html


def test_cli_package_writes_manifest(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    out_dir = tmp_path / "packages"
    _write_small_csv(csv_path)

    assert main(["package", str(csv_path), "--out", str(out_dir), "--title", "CLI Package"]) == 0

    manifest_paths = list(out_dir.glob("*/manifest.json"))
    assert len(manifest_paths) == 1
    manifest = manifest_paths[0].read_text()
    assert '"raw_csv"' in manifest
    assert '"report_html"' in manifest


def test_cli_verify_package_returns_success(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    out_dir = tmp_path / "packages"
    _write_small_csv(csv_path)
    assert main(["package", str(csv_path), "--out", str(out_dir), "--title", "CLI Package"]) == 0
    manifest_path = next(out_dir.glob("*/manifest.json"))

    assert main(["verify-package", str(manifest_path)]) == 0


def test_cli_index_writes_session_library(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "recording.csv"
    out_dir = tmp_path / "index"
    _write_small_csv(csv_path)

    assert main(["index", str(tmp_path), "--out", str(out_dir), "--title", "CLI Session Index"]) == 0
    captured = capsys.readouterr().out

    csv_outputs = list(out_dir.glob("*.csv"))
    html_outputs = list(out_dir.glob("*.html"))
    assert len(csv_outputs) == 1
    assert len(html_outputs) == 1
    assert "recording.csv" in csv_outputs[0].read_text()
    assert "CLI Session Index" in html_outputs[0].read_text()
    assert "package_ready=0" in captured
    assert "incomplete_records=1" in captured
    assert "needs_signal_review=0" in captured


def test_cli_qc_returns_success_for_good_recording(tmp_path: Path) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_small_csv(csv_path)

    assert main(["qc", str(csv_path), "--min-duration", "0.5", "--min-r-peaks", "1", "--allow-unclear-qrs"]) == 0


def test_cli_qc_returns_failure_for_artifact_threshold(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_small_csv(csv_path)

    result = main(
        [
            "qc",
            str(csv_path),
            "--min-duration",
            "0.5",
            "--min-r-peaks",
            "1",
            "--allow-unclear-qrs",
            "--max-peak-to-peak",
            "500",
        ]
    )

    output = capsys.readouterr().out
    assert result == 2
    assert "quality_gate=Fail" in output
    assert "failure=peak-to-peak" in output


def test_cli_qc_with_protocol_reports_segment_failures(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "recording.csv"
    protocol_path = tmp_path / "protocol.json"
    _write_small_csv(csv_path)
    write_protocol_json(
        protocol_path,
        TestProtocol(
            name="late protocol",
            steps=(ProtocolStep(start_seconds=10.0, duration_seconds=1.0, label="late", instruction="No data."),),
        ),
    )

    result = main(
        [
            "qc",
            str(csv_path),
            "--protocol",
            str(protocol_path),
            "--min-duration",
            "0.5",
            "--min-r-peaks",
            "1",
            "--allow-unclear-qrs",
        ]
    )

    output = capsys.readouterr().out
    assert result == 2
    assert "quality_gate=Pass" in output
    assert "protocol_segment_gate=Fail" in output
    assert "segment_failure=late: no data" in output


def test_cli_review_prints_artifact_metrics(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_small_csv(csv_path)

    assert main(["review", str(csv_path), "--source", "CH2"]) == 0

    output = capsys.readouterr().out
    assert "baseline_drift_counts=" in output
    assert "noise_rms_counts=" in output
    assert "peak_to_peak_counts=" in output
