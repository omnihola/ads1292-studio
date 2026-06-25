from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_dsp_fixtures import generate


def test_generates_coeffs_and_filter_outputs(tmp_path: Path):
    paths = generate(tmp_path)
    names = {p.stem for p in paths}
    assert "coeffs_bandpass_500hz" in names
    assert "coeffs_notch_60hz_500hz" in names
    assert "filtfilt_bandpass_long" in names
    assert "filtfilt_bandpass_short_window" in names

    coeffs = load_fixture(tmp_path / "dsp" / "coeffs_bandpass_500hz.json")
    assert len(coeffs["output"]["b"]) == 5  # butter order 2 band -> 5 taps
    assert len(coeffs["output"]["a"]) == 5

    flt = load_fixture(tmp_path / "dsp" / "filtfilt_bandpass_long.json")
    assert len(flt["input"]["signal"]) == len(flt["output"]["filtered"])
    assert flt["tolerance"]["kind"] == "abs"
