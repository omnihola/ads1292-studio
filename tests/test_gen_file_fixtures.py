# tests/test_gen_file_fixtures.py
from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_file_fixtures import generate


def test_freezes_csv_text_h5_sidecar_and_xlsx_semantic(tmp_path: Path):
    paths = generate(tmp_path)
    files_dir = tmp_path / "files"
    assert (files_dir / "live_recording.csv").exists()
    assert (files_dir / "live_recording_sidecar.json").exists()
    assert (files_dir / "recording.h5").exists()
    assert (files_dir / "recording.xlsx").exists()
    assert (files_dir / "recording_xlsx_sidecar.json").exists()

    live = load_fixture(files_dir / "live_recording_sidecar.json")
    assert live["csv_header"][0] == "timestamp"
    assert "ch2_counts" in live["csv_header"]

    h5 = load_fixture(files_dir / "recording_h5_sidecar.json")
    assert "datasets" in h5 and "attrs" in h5
    assert all("sha256" in d for d in h5["datasets"].values())
    assert h5["verify_ok"] is True

    xlsx = load_fixture(files_dir / "recording_xlsx_sidecar.json")
    assert len(xlsx["sheet_names"]) == 2
    assert xlsx["events_header"]            # exact header row, frozen
    assert xlsx["data_header"][0] == "timestamp"
    assert xlsx["point_event_row"][-3] == "point"     # type column
    assert xlsx["interval_event_row"][-3] == "interval"
    assert xlsx["data_first_row"] and xlsx["data_last_row"]
    assert xlsx["tolerance"]["kind"] == "semantic"
