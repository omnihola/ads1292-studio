from pathlib import Path
from scripts.generate_golden_fixtures import main as generate_all
from scripts.validate_golden_fixtures import validate_root


def test_full_generation_validates_clean(tmp_path: Path):
    generate_all(tmp_path)
    errors = validate_root(tmp_path)
    assert errors == [], f"validator found problems: {errors}"


def test_missing_provenance_is_flagged(tmp_path: Path):
    generate_all(tmp_path)
    (tmp_path / "oracle.json").unlink()
    errors = validate_root(tmp_path)
    assert any("oracle.json" in e for e in errors)


def test_missing_tolerance_is_flagged(tmp_path: Path):
    generate_all(tmp_path)
    import json
    target = next((tmp_path / "dsp").glob("filtfilt_*.json"))
    obj = json.loads(target.read_text())
    obj.pop("tolerance", None)
    obj.pop("output_tolerances", None)
    target.write_text(json.dumps(obj))
    errors = validate_root(tmp_path)
    assert any("tolerance" in e for e in errors)
