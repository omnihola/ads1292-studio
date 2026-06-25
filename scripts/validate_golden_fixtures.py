from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.fixture_provenance import REQUIRED_PROVENANCE_KEYS
from scripts._xlsx_read import read_xlsx_semantic

# Two fixture shapes exist:
#  - "envelope" fixtures (device/dsp/rpeak/review/spectrum): need input + output.
#  - "file_*" sidecars (file_csv_live/file_hdf5/file_xlsx): flat, category-specific.
COMMON_KEYS = ("schema_version", "category", "name", "oracle")
ENVELOPE_KEYS = ("input", "output")
FILE_SIDECAR_KEYS = {
    "file_csv_live": ("csv_header", "csv_first_rows"),
    "file_csv_raw": ("csv_header", "csv_first_rows"),
    "file_hdf5": ("artifact", "datasets", "attrs"),
    "file_xlsx": ("artifact", "sheet_names", "events_header", "point_event_row",
                  "interval_event_row", "data_header", "data_first_row", "data_last_row"),
    "file_bundle": ("artifact", "top_keys"),
}


def validate_root(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []

    manifest_path = root / "oracle.json"
    if not manifest_path.exists():
        errors.append("missing provenance: oracle.json")
    else:
        manifest = json.loads(manifest_path.read_text())
        for key in REQUIRED_PROVENANCE_KEYS:
            if key not in manifest:
                errors.append(f"oracle.json missing key: {key}")

    # Collect all sidecar artifacts (file paths that are referenced as artifacts)
    artifacts_to_skip = set()
    for path in sorted(root.rglob("*_sidecar.json")):
        try:
            obj = json.loads(path.read_text())
            if "artifact" in obj:
                artifact_path = path.parent / obj["artifact"]
                artifacts_to_skip.add(artifact_path)
        except Exception:
            pass

    for path in sorted(root.rglob("*.json")):
        if path.name == "oracle.json" or path in artifacts_to_skip:
            continue
        obj = json.loads(path.read_text())
        rel = path.relative_to(root)
        category = obj.get("category", "")

        for key in COMMON_KEYS:
            if key not in obj:
                errors.append(f"{rel}: missing envelope key '{key}'")
        if not ("tolerance" in obj or "output_tolerances" in obj):
            errors.append(f"{rel}: missing tolerance / output_tolerances")

        if category in FILE_SIDECAR_KEYS:
            for key in FILE_SIDECAR_KEYS[category]:
                if key not in obj:
                    errors.append(f"{rel}: file sidecar missing '{key}'")
            if category == "file_xlsx":
                errors.extend(_validate_xlsx(path, obj, rel))
        else:
            for key in ENVELOPE_KEYS:
                if key not in obj:
                    errors.append(f"{rel}: missing envelope key '{key}'")
    return errors


def _validate_xlsx(sidecar_path: Path, obj: dict, rel: Path) -> list[str]:
    """Re-open the committed workbook and confirm the frozen semantics still hold."""
    artifact = sidecar_path.parent / obj["artifact"]
    if not artifact.exists():
        return [f"{rel}: xlsx artifact not found: {obj['artifact']}"]
    actual = read_xlsx_semantic(artifact)
    problems: list[str] = []
    if actual["sheet_names"] != obj["sheet_names"]:
        problems.append(f"{rel}: xlsx sheet names drifted")
    events_name, data_name = actual["sheet_names"][0], actual["sheet_names"][1]
    events_rows = actual["sheets"][events_name]
    data_rows = actual["sheets"][data_name]
    if events_rows[0] != obj["events_header"]:
        problems.append(f"{rel}: xlsx events header drifted")
    if data_rows[0] != obj["data_header"]:
        problems.append(f"{rel}: xlsx data header drifted")
    if data_rows[1] != obj["data_first_row"] or data_rows[-1] != obj["data_last_row"]:
        problems.append(f"{rel}: xlsx data first/last row drifted")
    if obj["point_event_row"] not in events_rows or obj["interval_event_row"] not in events_rows:
        problems.append(f"{rel}: xlsx event rows drifted")
    return problems


if __name__ == "__main__":
    problems = validate_root(Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/golden"))
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("all golden fixtures valid")
