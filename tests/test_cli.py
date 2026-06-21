from pathlib import Path

from ads1292_studio.acquisition import (
    build_acquisition_provenance,
    finalize_acquisition_provenance,
    write_acquisition_json,
)
from ads1292_studio import cli
from ads1292_studio.calibration import Calibration, read_calibration_json, write_calibration_json
from ads1292_studio.cli import main
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.events import EventMarker, write_events_json
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import StreamSample
from ads1292_studio.protocol import ProtocolStep, TestProtocol, read_protocol_json, write_protocol_json
from ads1292_studio.quality_gate import QualityGate, write_quality_gate_json
from ads1292_studio.recording_manifest import write_recording_manifest


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


def _write_complete_sidecars(path: Path) -> None:
    calibration = Calibration(label="cli-bench-cal")
    acquisition = build_acquisition_provenance(
        csv_path=path,
        acquisition_mode="live_stream",
        port="/dev/cu.usbmodem-test",
        sample_rate_hz=500.0,
        calibration=calibration,
        live_calibration=None,
        started_at="2026-06-21T00:00:00",
    )
    write_metadata_json(path.with_suffix(".json"), SessionMetadata(session_id=path.stem, electrode="MOTAC gel"))
    write_events_json(path.with_suffix(".events.json"), (EventMarker(0.5, "baseline", "quiet"),))
    write_calibration_json(path.with_suffix(".calibration.json"), calibration)
    write_acquisition_json(
        path.with_suffix(".acquisition.json"),
        finalize_acquisition_provenance(
            acquisition,
            ended_at="2026-06-21T00:00:01",
            finalized_at="2026-06-21T00:00:01",
            sample_count=500,
            first_timestamp_seconds=0.0,
            last_timestamp_seconds=0.998,
        ),
    )
    write_protocol_json(
        path.with_suffix(".protocol.json"),
        TestProtocol(
            name="CLI protocol",
            steps=(ProtocolStep(start_seconds=0.0, duration_seconds=1.0, label="baseline", instruction="Sit still."),),
        ),
    )
    write_quality_gate_json(path.with_suffix(".quality-gate.json"), QualityGate(min_duration_seconds=0.5))


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
    _write_complete_sidecars(csv_path)
    assert main(["package", str(csv_path), "--out", str(out_dir), "--title", "CLI Package"]) == 0
    manifest_path = next(out_dir.glob("*/manifest.json"))

    assert main(["verify-package", str(manifest_path)]) == 0


def test_cli_verify_recording_returns_success(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_small_csv(csv_path)
    _write_complete_sidecars(csv_path)
    manifest_path = write_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")

    assert main(["verify-recording", str(manifest_path)]) == 0

    output = capsys.readouterr().out
    assert "ok=True" in output
    assert "checked_files=7" in output


def test_cli_verify_recording_returns_failure_for_stale_manifest(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_small_csv(csv_path)
    _write_complete_sidecars(csv_path)
    manifest_path = write_recording_manifest(csv_path, created_at="2026-06-21T13:00:00")
    csv_path.write_text(csv_path.read_text() + "1.000000,0,1000,0,0,0,0\n")

    assert main(["verify-recording", str(manifest_path)]) == 2

    output = capsys.readouterr().out
    assert "ok=False" in output
    assert "failure=raw_csv: sha256 mismatch for recording.csv" in output


def test_cli_manifest_writes_recording_manifest(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "recording.csv"
    _write_small_csv(csv_path)
    _write_complete_sidecars(csv_path)

    assert main(["manifest", str(csv_path)]) == 0

    output = capsys.readouterr().out
    manifest_path = csv_path.with_suffix(".manifest.json")
    assert f"manifest={manifest_path}" in output
    assert manifest_path.exists()
    assert main(["verify-recording", str(manifest_path)]) == 0


def test_cli_index_writes_session_library(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "recording.csv"
    out_dir = tmp_path / "index"
    _write_small_csv(csv_path)

    assert main(["index", str(tmp_path), "--out", str(out_dir), "--title", "CLI Session Index"]) == 0
    captured = capsys.readouterr().out

    csv_outputs = list(out_dir.glob("*.csv"))
    html_outputs = list(out_dir.glob("*.html"))
    assert len(csv_outputs) == 3
    assert len(html_outputs) == 3
    index_csv = next(
        path
        for path in csv_outputs
        if not path.stem.endswith("-sidecar-plan") and not path.stem.endswith("-manifest-plan")
    )
    index_html = next(
        path
        for path in html_outputs
        if not path.stem.endswith("-sidecar-plan") and not path.stem.endswith("-manifest-plan")
    )
    assert "recording.csv" in index_csv.read_text()
    assert "CLI Session Index" in index_html.read_text()
    assert "package_ready=0" in captured
    assert "incomplete_records=1" in captured
    assert "needs_signal_review=0" in captured
    assert "action_package_record=0" in captured
    assert "action_complete_sidecars=1" in captured
    assert "action_review_signal=0" in captured
    assert "sidecar_plan_csv=" in captured
    assert "sidecar_plan_html=" in captured
    assert "sidecar_plan_rows=6" in captured
    assert "sidecar_template_dir=" in captured
    assert "sidecar_template_files=6" in captured
    assert "sidecar_apply_script=" in captured
    assert "manifest_plan_csv=" in captured
    assert "manifest_plan_html=" in captured
    assert "manifest_apply_script=" in captured
    assert "manifest_plan_rows=1" in captured
    sidecar_plan = next(out_dir.glob("*-sidecar-plan.csv"))
    apply_script = next(out_dir.glob("*-apply-sidecars.sh"))
    manifest_plan = next(out_dir.glob("*-manifest-plan.csv"))
    manifest_apply_script = next(out_dir.glob("*-apply-manifests.sh"))
    template_dir = next(out_dir.glob("*-sidecar-templates"))
    sidecar_plan_text = sidecar_plan.read_text()
    manifest_plan_text = manifest_plan.read_text()
    assert "recording.csv,metadata," in sidecar_plan_text
    assert "recording.csv,acquisition," in sidecar_plan_text
    assert str(template_dir / "recording.json") in sidecar_plan_text
    assert str(template_dir / "recording.acquisition.json") in sidecar_plan_text
    assert str(template_dir / "recording.protocol.json") in sidecar_plan_text
    assert (template_dir / "recording.json").exists()
    assert (template_dir / "recording.acquisition.json").exists()
    assert (template_dir / "recording.protocol.json").exists()
    assert str(template_dir / "recording.json") in apply_script.read_text()
    assert "recording.csv,missing," in manifest_plan_text
    assert "python -m ads1292_studio manifest" in manifest_apply_script.read_text()


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


class _CliStreamSpyDevice:
    instances: list["_CliStreamSpyDevice"] = []

    def __init__(self, port: str, *args, **kwargs) -> None:
        self.port = port
        self.should_continue: object = "UNSET"
        _CliStreamSpyDevice.instances.append(self)

    def __enter__(self) -> "_CliStreamSpyDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def query_firmware(self) -> str:
        return "1.0"

    def start_stream(self) -> None:
        return None

    def stop_stream(self) -> None:
        return None

    def iter_stream_samples(self, *, should_continue=None):
        self.should_continue = should_continue
        return
        yield  # pragma: no cover - makes this a generator that yields nothing


def test_cli_stream_passes_deadline_predicate_to_device(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "Ads1x9xDevice", _CliStreamSpyDevice)
    _CliStreamSpyDevice.instances.clear()

    rc = cli.main(["stream", "--port", "fake-port", "--seconds", "0"])

    assert rc == 0
    assert _CliStreamSpyDevice.instances, "cmd_stream never constructed a device"
    assert callable(_CliStreamSpyDevice.instances[0].should_continue)
