from pathlib import Path
import json
from scripts.fixture_provenance import build_provenance, write_provenance, REQUIRED_PROVENANCE_KEYS


def test_provenance_has_all_required_keys():
    manifest = build_provenance(sample_rate_hz=500.0, generation_command="python -m scripts.generate_golden_fixtures")
    for key in REQUIRED_PROVENANCE_KEYS:
        assert key in manifest, f"missing provenance key: {key}"
    assert manifest["sample_rate_hz"] == 500.0
    assert manifest["python_version"].count(".") >= 2


def test_write_provenance_round_trips(tmp_path: Path):
    path = write_provenance(tmp_path, sample_rate_hz=500.0, generation_command="cmd")
    assert path.name == "oracle.json"
    loaded = json.loads(path.read_text())
    assert loaded["fixture_generation_command"] == "cmd"
