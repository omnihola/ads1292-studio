from pathlib import Path

import numpy as np

from ads1292_studio.batch import aggregate_recordings, group_recordings_by_electrode, export_batch_summary
from ads1292_studio.csv_io import write_recording_csv
from ads1292_studio.metadata import SessionMetadata, write_metadata_json
from ads1292_studio.models import StreamSample


def synthetic_samples(scale: float, sample_rate_hz: float = 500.0) -> tuple[StreamSample, ...]:
    t = np.arange(0, 7, 1 / sample_rate_hz)
    ch1 = 10 * np.sin(2 * np.pi * 0.6 * t)
    ch2 = 5 * np.sin(2 * np.pi * 1.0 * t)
    for peak in np.arange(0.5, 6.8, 0.58):
        ch2 += scale * np.exp(-0.5 * ((t - peak) / 0.012) ** 2)
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


def write_recording(tmp_path: Path, name: str, electrode: str, scale: float) -> Path:
    path = tmp_path / f"{name}.csv"
    write_recording_csv(path, synthetic_samples(scale))
    write_metadata_json(
        path.with_suffix(".json"),
        SessionMetadata(session_id=name, subject_id="anon", electrode=electrode, montage="RA/LA/RL torso"),
    )
    return path


def test_aggregate_recordings_includes_metadata_and_quality(tmp_path: Path) -> None:
    control = write_recording(tmp_path, "control", "commercial Ag/AgCl", 420)
    motac = write_recording(tmp_path, "motac", "MOTAC gel + Ag/AgCl", 380)

    rows = aggregate_recordings([control, motac])

    assert [row.session_id for row in rows] == ["control", "motac"]
    assert [row.electrode for row in rows] == ["commercial Ag/AgCl", "MOTAC gel + Ag/AgCl"]
    assert all(row.ecg_source == "CH2" for row in rows)
    assert all(row.qrs_clear for row in rows)
    assert all(95 <= row.hr_median_bpm <= 110 for row in rows)


def test_export_batch_summary_writes_csv_html_and_png(tmp_path: Path) -> None:
    control = write_recording(tmp_path, "control", "commercial Ag/AgCl", 420)
    motac = write_recording(tmp_path, "motac", "MOTAC gel + Ag/AgCl", 380)
    out_dir = tmp_path / "batch"

    result = export_batch_summary([control, motac], out_dir=out_dir, title="MOTAC batch comparison")

    assert result.csv_path.exists()
    assert result.html_path.exists()
    assert result.png_path.exists()
    csv_text = result.csv_path.read_text()
    html = result.html_path.read_text()
    assert "commercial Ag/AgCl" in csv_text
    assert "MOTAC gel + Ag/AgCl" in html
    assert "MOTAC batch comparison" in html


def test_group_recordings_by_electrode_summarizes_quality(tmp_path: Path) -> None:
    control_one = write_recording(tmp_path, "control-1", "commercial Ag/AgCl", 420)
    control_two = write_recording(tmp_path, "control-2", "commercial Ag/AgCl", 410)
    motac = write_recording(tmp_path, "motac-1", "MOTAC gel + Ag/AgCl", 380)
    rows = aggregate_recordings([control_one, control_two, motac])

    summaries = group_recordings_by_electrode(rows)

    assert [summary.electrode for summary in summaries] == ["MOTAC gel + Ag/AgCl", "commercial Ag/AgCl"]
    control = next(summary for summary in summaries if summary.electrode == "commercial Ag/AgCl")
    assert control.recordings == 2
    assert control.usable_recordings == 2
    assert control.usable_percent == 100.0
    assert control.mean_contact_ok_percent == 100.0
    assert 95 <= control.mean_hr_median_bpm <= 110
    assert control.mean_r_peaks >= 10


def test_export_batch_summary_writes_group_summary_csv_and_html(tmp_path: Path) -> None:
    control_one = write_recording(tmp_path, "control-1", "commercial Ag/AgCl", 420)
    control_two = write_recording(tmp_path, "control-2", "commercial Ag/AgCl", 410)
    motac = write_recording(tmp_path, "motac-1", "MOTAC gel + Ag/AgCl", 380)
    out_dir = tmp_path / "batch"

    result = export_batch_summary([control_one, control_two, motac], out_dir=out_dir, title="MOTAC batch comparison")

    assert result.group_csv_path.exists()
    group_csv = result.group_csv_path.read_text()
    html = result.html_path.read_text()
    assert "electrode,recordings,usable_recordings,usable_percent" in group_csv
    assert "commercial Ag/AgCl,2,2,100.0" in group_csv
    assert "Group Summary" in html
    assert "Usable %" in html


def test_batch_skips_unreadable_files_instead_of_aborting(tmp_path):
    from ads1292_studio.batch import aggregate_recordings
    from ads1292_studio.csv_io import write_recording_csv
    from ads1292_studio.models import StreamSample

    good = tmp_path / "good-ads1292-studio.csv"
    write_recording_csv(good, [StreamSample(timestamp=0.0, ch1=1, ch2=2,
                                            board_heart_rate=0, board_respiration_rate=0, status_byte=0)])
    missing = tmp_path / "does-not-exist.csv"
    rows = aggregate_recordings([missing, good])  # missing must not abort
    assert len(rows) == 1
    assert rows[0].path == good
