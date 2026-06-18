from pathlib import Path

from ads1292_studio.csv_io import read_recording_csv, write_recording_csv
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
