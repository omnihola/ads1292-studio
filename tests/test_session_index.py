from pathlib import Path

import numpy as np

from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import StreamSample
from ads1292_studio.session_index import export_session_index, scan_recording_directory


def _samples() -> tuple[StreamSample, ...]:
    sample_rate_hz = 500.0
    t = np.arange(0, 7, 1 / sample_rate_hz)
    ch1 = 10 * np.sin(2 * np.pi * 0.6 * t)
    ch2 = 5 * np.sin(2 * np.pi * 1.0 * t)
    for peak in np.arange(0.5, 6.8, 0.58):
        ch2 += 420 * np.exp(-0.5 * ((t - peak) / 0.012) ** 2)
    return tuple(
        StreamSample(
            timestamp=index / sample_rate_hz,
            ch1=int(round(one)),
            ch2=int(round(two)),
            board_heart_rate=0,
            board_respiration_rate=0,
            status_byte=0,
        )
        for index, (one, two) in enumerate(zip(ch1, ch2))
    )


def _write_recording(root: Path, relative: str, electrode: str) -> Path:
    path = root / relative
    write_recording_csv(path, _samples())
    write_metadata_json(
        path.with_suffix(".json"),
        SessionMetadata(
            session_id=path.stem,
            subject_id="anonymous",
            electrode=electrode,
            montage="RA/LA/RL torso",
            operator="tester",
        ),
    )
    return path


def test_scan_recording_directory_discovers_recordings_and_ignores_exports(tmp_path: Path) -> None:
    _write_recording(tmp_path, "baseline/control.csv", "commercial Ag/AgCl")
    _write_recording(tmp_path, "motac.csv", "MOTAC gel + Ag/AgCl")
    (tmp_path / "old-session-index.csv").write_text("not,a,recording\n")

    rows = scan_recording_directory(tmp_path)

    assert [row.relative_path for row in rows] == ["baseline/control.csv", "motac.csv"]
    assert [row.electrode for row in rows] == ["commercial Ag/AgCl", "MOTAC gel + Ag/AgCl"]
    assert all(row.ecg_source == "CH2" for row in rows)
    assert all(row.status == "usable" for row in rows)


def test_export_session_index_writes_csv_and_html(tmp_path: Path) -> None:
    _write_recording(tmp_path, "control.csv", "commercial Ag/AgCl")
    _write_recording(tmp_path, "motac.csv", "MOTAC gel + Ag/AgCl")
    out_dir = tmp_path / "index"

    export = export_session_index(tmp_path, out_dir=out_dir, title="MOTAC Session Library")

    assert export.csv_path.exists()
    assert export.html_path.exists()
    assert len(export.rows) == 2
    csv_text = export.csv_path.read_text()
    html = export.html_path.read_text()
    assert "relative_path,session_id,subject_id,electrode" in csv_text
    assert "commercial Ag/AgCl" in csv_text
    assert "MOTAC Session Library" in html
    assert "Usable recordings" in html
