from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_rpeak_fixtures import generate


def test_freezes_rpeak_chain_intermediates(tmp_path: Path):
    paths = generate(tmp_path)
    assert any(p.stem == "rpeak_chain_clean_72bpm" for p in paths)
    fx = load_fixture(tmp_path / "rpeak" / "rpeak_chain_clean_72bpm.json")
    out = fx["output"]
    assert "filtered" in out and "centered" in out
    assert "prominence" in out and "distance" in out
    assert "polarity" in out  # "positive" or "negative"
    assert isinstance(out["peaks"], list)
    assert all(isinstance(i, int) for i in out["peaks"])
    assert fx["output_tolerances"]["peaks"]["kind"] == "exact"
