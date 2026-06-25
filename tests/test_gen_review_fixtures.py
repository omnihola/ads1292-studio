from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_review_fixtures import generate


def test_freezes_hr_pqrst_quality_snr(tmp_path: Path):
    paths = generate(tmp_path)
    names = {p.stem for p in paths}
    assert "hr_summary_clean_72bpm" in names
    assert "pqrst_clean_72bpm" in names
    assert "quality_metrics_clean_72bpm" in names
    assert "realtime_snr_clean_72bpm" in names

    hr = load_fixture(tmp_path / "review" / "hr_summary_clean_72bpm.json")
    assert "peaks" in hr["input"]          # upstream frozen peaks
    assert "median_bpm" in hr["output"]

    snr = load_fixture(tmp_path / "review" / "realtime_snr_clean_72bpm.json")
    assert "snr_db" in snr["output"] and "noise_rms_counts" in snr["output"]
