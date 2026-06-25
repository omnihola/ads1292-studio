from pathlib import Path
from scripts.fixture_io import load_fixture
from scripts.gen_device_fixtures import generate


def test_generates_stream_and_acquire_and_errors(tmp_path: Path):
    paths = generate(tmp_path)
    names = {p.stem for p in paths}
    assert "stream_payload_nominal" in names
    assert "acquire_payload_nominal" in names
    assert "stream_bad_trailer" in names
    assert "stream_too_short" in names
    assert "acquire_bad_trailer" in names

    nominal = load_fixture(tmp_path / "device_parser" / "stream_payload_nominal.json")
    assert len(nominal["output"]["samples"]) == 14
    assert nominal["output"]["samples"][0]["ch1"] is not None

    bad = load_fixture(tmp_path / "device_parser" / "stream_bad_trailer.json")
    assert bad["output"]["raises"] == "ValueError"
    assert "trailer" in bad["output"]["message_contains"]
