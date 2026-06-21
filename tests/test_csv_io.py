from pathlib import Path

from ads1292_studio.calibration import Calibration, LiveStreamCalibration
from ads1292_studio.csv_io import (
    CsvRecorder,
    RawCsvRecorder,
    read_recording_csv,
    read_raw_recording_csv,
    write_recording_csv,
    write_raw_recording_csv,
)
from ads1292_studio.models import RawSample, StreamSample


def test_csv_round_trip_preserves_raw_channels_and_lead_bits(tmp_path: Path) -> None:
    path = tmp_path / "recording.csv"
    samples = [
        StreamSample(
            timestamp=1.0,
            ch1=-12,
            ch2=345,
            board_heart_rate=88,
            board_respiration_rate=22,
            status_byte=0x10,
        ),
        StreamSample(
            timestamp=1.002,
            ch1=-10,
            ch2=355,
            board_heart_rate=88,
            board_respiration_rate=22,
            status_byte=0x05,
        ),
    ]

    write_recording_csv(path, samples)
    loaded = read_recording_csv(path)
    text = path.read_text()

    assert text.splitlines()[0].startswith("timestamp,sample_index,ch1_counts")
    assert "1.000000,0,-12,345" in text
    assert "1.002000,1,-10,355" in text
    assert [sample.ch1 for sample in loaded.samples] == [-12, -10]
    assert [sample.ch2 for sample in loaded.samples] == [345, 355]
    assert [sample.status_byte for sample in loaded.samples] == [0x10, 0x05]
    assert [sample.lead_off_bits for sample in loaded.samples] == [0, 5]


def test_csv_reader_accepts_legacy_ecg_resp_headers(tmp_path: Path) -> None:
    path = tmp_path / "legacy.csv"
    path.write_text(
        "timestamp,ecg_counts,resp_counts,heart_rate,respiration_rate,lead_off\n"
        "1.0,7,99,80,20,16\n"
    )

    loaded = read_recording_csv(path)

    assert len(loaded.samples) == 1
    assert loaded.samples[0].ch1 == 7
    assert loaded.samples[0].ch2 == 99
    assert loaded.samples[0].status_byte == 16
    assert loaded.samples[0].lead_off_bits == 0


def test_csv_reader_accepts_new_live_sample_index_column(tmp_path: Path) -> None:
    path = tmp_path / "indexed.csv"
    path.write_text(
        "timestamp,sample_index,ch1_counts,ch2_counts,board_heart_rate,board_respiration_rate,status_byte,lead_off_bits\n"
        "1.0,500,7,99,80,20,16,0\n"
    )

    loaded = read_recording_csv(path)

    assert len(loaded.samples) == 1
    assert loaded.samples[0].timestamp == 1.0
    assert loaded.samples[0].ch1 == 7
    assert loaded.samples[0].ch2 == 99


def test_csv_reader_combines_canonical_lead_off_bits_when_status_byte_omits_them(tmp_path: Path) -> None:
    path = tmp_path / "recording.csv"
    path.write_text(
        "timestamp,ch1_counts,ch2_counts,board_heart_rate,board_respiration_rate,status_byte,lead_off_bits\n"
        "1.0,7,99,80,20,16,5\n"
    )

    loaded = read_recording_csv(path)

    assert loaded.samples[0].status_byte == 21
    assert loaded.samples[0].lead_off_bits == 5


def test_csv_reader_prefers_canonical_lead_off_bits_over_stale_status_low_nibble(tmp_path: Path) -> None:
    path = tmp_path / "recording.csv"
    path.write_text(
        "timestamp,ch1_counts,ch2_counts,board_heart_rate,board_respiration_rate,status_byte,lead_off_bits\n"
        "1.0,7,99,80,20,21,0\n"
    )

    loaded = read_recording_csv(path)

    assert loaded.samples[0].status_byte == 16
    assert loaded.samples[0].lead_off_bits == 0


def test_csv_recorder_flushes_in_batches_and_on_close(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "recording.csv"
    samples = [
        StreamSample(
            timestamp=float(index),
            ch1=index,
            ch2=index + 100,
            board_heart_rate=70,
            board_respiration_rate=18,
            status_byte=index,
        )
        for index in range(5)
    ]

    with CsvRecorder(path, flush_every_rows=3) as recorder:
        flush_calls = 0
        original_flush = recorder._handle.flush

        def counted_flush() -> None:
            nonlocal flush_calls
            flush_calls += 1
            original_flush()

        monkeypatch.setattr(recorder._handle, "flush", counted_flush)
        for sample in samples:
            recorder.write(sample)
        assert flush_calls == 1

    loaded = read_recording_csv(path)

    assert recorder.rows_written == 5
    assert flush_calls == 3
    assert len(loaded.samples) == 5
    assert loaded.samples[-1].ch2 == 104
    assert loaded.samples[-1].lead_off_bits == 4
    lines = path.read_text().splitlines()
    assert lines[0].startswith("timestamp,sample_index,ch1_counts")
    assert lines[1].startswith("0.000000,0,0,100")
    assert lines[-1].startswith("4.000000,4,4,104")


def test_csv_recorder_normalizes_flush_batch_size(tmp_path: Path) -> None:
    path = tmp_path / "recording.csv"

    recorder = CsvRecorder(path, flush_every_rows=0)

    assert recorder.flush_every_rows == 1


def test_csv_recorder_writes_live_stream_calibration_columns(tmp_path: Path) -> None:
    path = tmp_path / "live-calibrated.csv"
    calibration = LiveStreamCalibration(
        mean_uv_per_count=1.895,
        std_uv_per_count=0.001,
        cv_percent=0.05,
        runs=5,
        test_signal_pp_uv=2016.6666667,
    )

    with CsvRecorder(path, live_calibration=calibration) as recorder:
        recorder.write(
            StreamSample(
                timestamp=0.0,
                ch1=1,
                ch2=2,
                board_heart_rate=0,
                board_respiration_rate=0,
                status_byte=0,
            )
        )

    text = path.read_text()

    assert "live_scale_uv_per_count" in text
    assert "live_scale_type" in text
    assert "1.895" in text
    assert "live_processed" in text


def test_raw_csv_round_trip_preserves_24_bit_counts_and_microvolts(tmp_path: Path) -> None:
    path = tmp_path / "raw.csv"
    calibration = Calibration(vref_mv=2420.0, pga_gain=6.0, adc_bits=24, label="raw test")
    samples = (
        RawSample(timestamp=0.0, sample_index=0, ch1_raw24=-1000, ch2_raw24=2000, status_byte=0x10),
        RawSample(timestamp=0.002, sample_index=1, ch1_raw24=-999, ch2_raw24=1999, status_byte=0x15),
    )

    write_raw_recording_csv(path, samples, calibration=calibration)
    loaded = read_raw_recording_csv(path)

    assert [sample.ch1_raw24 for sample in loaded.samples] == [-1000, -999]
    assert [sample.ch2_raw24 for sample in loaded.samples] == [2000, 1999]
    assert [sample.status_byte for sample in loaded.samples] == [0x10, 0x15]
    assert loaded.samples[0].ch2_uv == 2000 * calibration.microvolts_per_count


def test_raw_csv_recorder_flushes_and_writes_raw_header(tmp_path: Path) -> None:
    path = tmp_path / "raw.csv"
    with RawCsvRecorder(path, calibration=Calibration(), flush_every_rows=1) as recorder:
        recorder.write(RawSample(timestamp=0.0, sample_index=0, ch1_raw24=1, ch2_raw24=-2, status_byte=0))

    text = path.read_text()

    assert "ch1_raw24,ch2_raw24,ch1_uv,ch2_uv" in text
    assert recorder.rows_written == 1


def test_canonical_csv_loader_accepts_raw_acquisition_files_for_review(tmp_path: Path) -> None:
    path = tmp_path / "raw.csv"
    write_raw_recording_csv(
        path,
        (RawSample(timestamp=0.0, sample_index=0, ch1_raw24=123, ch2_raw24=-456, status_byte=0x05),),
        calibration=Calibration(),
    )

    loaded = read_recording_csv(path)

    assert loaded.samples[0].ch1 == 123
    assert loaded.samples[0].ch2 == -456
    assert loaded.samples[0].lead_off_bits == 5
