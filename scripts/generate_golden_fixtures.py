from __future__ import annotations

from pathlib import Path

from scripts import (
    gen_device_fixtures, gen_dsp_fixtures, gen_rpeak_fixtures,
    gen_review_fixtures, gen_spectrum_fixtures, gen_file_fixtures,
)
from scripts.fixture_provenance import write_provenance

GENERATORS = (
    gen_device_fixtures.generate, gen_dsp_fixtures.generate, gen_rpeak_fixtures.generate,
    gen_review_fixtures.generate, gen_spectrum_fixtures.generate, gen_file_fixtures.generate,
)
COMMAND = "python -m scripts.generate_golden_fixtures"


def main(root: Path) -> None:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for generate in GENERATORS:
        generate(root)
    write_provenance(root, sample_rate_hz=500.0, generation_command=COMMAND)


if __name__ == "__main__":
    main(Path("tests/fixtures/golden"))
