from pathlib import Path

from ads1292_studio.calibration import Calibration, read_calibration_json, write_calibration_json
from ads1292_studio.cli import main
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.models import StreamSample


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
