#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHONPATH="${PYTHONPATH:-}:src" conda run -n sensor python -m ads1292_studio
