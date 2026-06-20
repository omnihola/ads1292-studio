from pathlib import Path

from ads1292_studio.csv_io import CsvRecorder, read_recording_csv, write_recording_csv
from ads1292_studio.models import StreamSample


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


def test_csv_recorder_normalizes_flush_batch_size(tmp_path: Path) -> None:
    path = tmp_path / "recording.csv"

    recorder = CsvRecorder(path, flush_every_rows=0)

    assert recorder.flush_every_rows == 1
