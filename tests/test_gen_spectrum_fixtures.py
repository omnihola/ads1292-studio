from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_spectrum_fixtures import generate


def test_freezes_spectrum_and_histogram(tmp_path: Path):
    paths = generate(tmp_path)
    assert any(p.stem == "spectrum_clean_72bpm_ch2" for p in paths)
    fx = load_fixture(tmp_path / "spectrum" / "spectrum_clean_72bpm_ch2.json")
    out = fx["output"]
    assert len(out["ecg_frequency_hz"]) == len(out["ecg_power"])
    assert len(out["histogram_bin_edges"]) == len(out["histogram_counts"]) + 1
