#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

python_bin="${UNICODEFIX_PYTHON:-}"
if [[ -z "${python_bin}" ]]; then
    python_bin="$(git config --local --get unicodefix.python 2>/dev/null || true)"
fi
if [[ -z "${python_bin}" && -x "${repo_root}/.venv/bin/python" ]]; then
    python_bin="${repo_root}/.venv/bin/python"
fi
if [[ -z "${python_bin}" && -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    python_bin="${VIRTUAL_ENV}/bin/python"
fi
if [[ -z "${python_bin}" && -n "${CONDA_PREFIX:-}" && -x "${CONDA_PREFIX}/bin/python" ]]; then
    python_bin="${CONDA_PREFIX}/bin/python"
fi
if [[ -z "${python_bin}" ]]; then
    python_bin="$(command -v python 2>/dev/null || command -v python3 2>/dev/null || true)"
fi
if [[ -z "${python_bin}" || ! -x "${python_bin}" ]]; then
    echo "Unable to locate the configured UnicodeFix Python interpreter." >&2
    echo "Run ./setup.sh --dev or set UNICODEFIX_PYTHON to a suitable interpreter." >&2
    exit 1
fi
if ! "${python_bin}" -c 'import black, pytest, ruff' >/dev/null 2>&1; then
    echo "${python_bin} does not contain the UnicodeFix development checks." >&2
    echo "Run ./setup.sh --dev or set UNICODEFIX_PYTHON to a suitable interpreter." >&2
    exit 1
fi

echo "Running Black..."
"${python_bin}" -m black --check src tests research

echo "Running Ruff..."
"${python_bin}" -m ruff check src tests research

echo "Running pytest..."
"${python_bin}" -m pytest -q
