from pathlib import Path

from ads1292_studio.acquisition import (
    ACQUISITION_SCHEMA,
    build_acquisition_provenance,
    format_acquisition_summary,
    read_acquisition_json,
    write_acquisition_json,
)
from ads1292_studio.calibration import Calibration, LiveStreamCalibration


def test_acquisition_provenance_round_trip_preserves_live_and_raw_scale(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "2026-06-21-120000-ads1292-studio.csv"
    raw_calibration = Calibration(vref_mv=2420.0, pga_gain=6.0, adc_bits=24, label="ADS1292 raw")
    live_calibration = LiveStreamCalibration(
        mean_uv_per_count=1.895,
        std_uv_per_count=0.002,
        cv_percent=0.11,
        runs=5,
        test_signal_pp_uv=2016.6666667,
    )

    provenance = build_acquisition_provenance(
        csv_path=csv_path,
        acquisition_mode="live_stream",
        port="/dev/cu.usbmodem214301",
        sample_rate_hz=500.0,
        calibration=raw_calibration,
        live_calibration=live_calibration,
        started_at="2026-06-21T12:00:00",
    )
    write_acquisition_json(csv_path.with_suffix(".acquisition.json"), provenance)

    loaded = read_acquisition_json(csv_path.with_suffix(".acquisition.json"))

    assert loaded.schema == ACQUISITION_SCHEMA
    assert loaded.csv_name == csv_path.name
    assert loaded.acquisition_mode == "live_stream"
    assert loaded.csv_schema == "ads1292-studio-live-stream-v1"
    assert loaded.port == "/dev/cu.usbmodem214301"
    assert loaded.sample_rate_hz == 500.0
    assert loaded.channel_map["ch2_counts"] == "CH2 ECG Lead I (LA-RA)"
    assert loaded.channel_map["ch1_counts"] == "CH1 respiration/raw impedance"
    assert loaded.live_calibration["mean_uv_per_count"] == 1.895
    assert loaded.live_calibration["runs"] == 5
    assert loaded.raw_adc["pga_gain"] == 6.0
    assert loaded.raw_adc["raw_lsb_uv_per_count"] == raw_calibration.microvolts_per_count


def test_acquisition_provenance_marks_raw_adc_schema(tmp_path: Path) -> None:
    csv_path = tmp_path / "2026-06-21-120000-ads1292-raw.csv"

    provenance = build_acquisition_provenance(
        csv_path=csv_path,
        acquisition_mode="raw",
        port="/dev/cu.usbmodem214301",
        sample_rate_hz=500.0,
        calibration=Calibration(),
        live_calibration=None,
        started_at="2026-06-21T12:00:00",
    )

    assert provenance.acquisition_mode == "raw_adc_24bit"
    assert provenance.csv_schema == "ads1292-studio-raw-adc-v1"
    assert provenance.live_calibration == {}


def test_format_acquisition_summary_exposes_scientific_record_fields(tmp_path: Path) -> None:
    csv_path = tmp_path / "2026-06-21-120000-ads1292-studio.csv"
    provenance = build_acquisition_provenance(
        csv_path=csv_path,
        acquisition_mode="live_stream",
        port="/dev/cu.usbmodem214301",
        sample_rate_hz=500.0,
        calibration=Calibration(vref_mv=2420.0, pga_gain=6.0, adc_bits=24, label="ADS1292 raw"),
        live_calibration=LiveStreamCalibration(
            mean_uv_per_count=1.895,
            std_uv_per_count=0.002,
            cv_percent=0.11,
            runs=5,
            test_signal_pp_uv=2016.6666667,
        ),
        started_at="2026-06-21T12:00:00",
    )

    summary = format_acquisition_summary(provenance)

    assert "live_stream" in summary
    assert "/dev/cu.usbmodem214301" in summary
    assert "500 Hz" in summary
    assert "Live scale 1.895 uV/count" in summary
    assert "Raw LSB 0.048081 uV/count" in summary
