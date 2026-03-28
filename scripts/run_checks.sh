#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

echo "Running Black..."
python -m black --check src tests

echo "Running Ruff..."
python -m ruff check src tests

echo "Running pytest..."
pytest -q
