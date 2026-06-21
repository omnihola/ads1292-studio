from datetime import datetime
from pathlib import Path

from ads1292_studio.recording_paths import recording_csv_path


def test_recording_csv_path_uses_microseconds_to_avoid_same_second_collisions() -> None:
    first = recording_csv_path(
        started_at=datetime(2026, 6, 21, 12, 0, 0, 1000),
        acquisition_mode="live",
        root=Path("recordings"),
    )
    second = recording_csv_path(
        started_at=datetime(2026, 6, 21, 12, 0, 0, 2000),
        acquisition_mode="live",
        root=Path("recordings"),
    )

    assert first != second
    assert first.parent == Path("recordings") / "live"
    assert second.parent == Path("recordings") / "live"
    assert first.name == "2026-06-21-120000-001000-ads1292-studio.csv"
    assert second.name == "2026-06-21-120000-002000-ads1292-studio.csv"


def test_recording_csv_path_defaults_live_recordings_to_documents_ecg_live() -> None:
    path = recording_csv_path(
        started_at=datetime(2026, 6, 21, 12, 0, 0, 1000),
        acquisition_mode="live",
    )

    assert path.parent == Path.home() / "Documents" / "ECG" / "live"
    assert path.name == "2026-06-21-120000-001000-ads1292-studio.csv"


def test_recording_csv_path_defaults_raw_recordings_to_documents_ecg_raw() -> None:
    path = recording_csv_path(
        started_at=datetime(2026, 6, 21, 12, 0, 0, 1000),
        acquisition_mode="raw",
    )

    assert path.parent == Path.home() / "Documents" / "ECG" / "raw"
    assert path.name == "2026-06-21-120000-001000-ads1292-raw.csv"


def test_recording_csv_path_marks_raw_recordings() -> None:
    path = recording_csv_path(
        started_at=datetime(2026, 6, 21, 12, 0, 0, 1000),
        acquisition_mode="raw",
        root=Path("recordings"),
    )

    assert path.parent == Path("recordings") / "raw"
    assert path.name == "2026-06-21-120000-001000-ads1292-raw.csv"
