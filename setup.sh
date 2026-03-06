#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./setup.sh [--dev] [--nlp]

Bootstraps UnicodeFix using pyproject.toml as the only dependency source.

Options:
  --dev   Install development dependencies and use editable mode.
  --nlp   Install optional NLP/metrics dependencies.
  -h      Show this help text.
EOF
}

extras=()
editable=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev)
            editable=1
            extras+=("dev")
            ;;
        --nlp|--metrics)
            extras+=("nlp")
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

env_label=""
created_env=0

if [[ -n "${CONDA_PREFIX:-}" && -n "${CONDA_DEFAULT_ENV:-}" ]]; then
    env_label="active Conda environment '${CONDA_DEFAULT_ENV}'"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
    env_label="active virtualenv '${VIRTUAL_ENV}'"
else
    venv_dir="${UNICODEFIX_VENV_DIR:-.venv}"
    if [[ ! -d "${venv_dir}" ]]; then
        python3 -m venv "${venv_dir}"
        created_env=1
    fi
    # shellcheck disable=SC1090
    source "${venv_dir}/bin/activate"
    env_label="local virtualenv '${venv_dir}'"
fi

python -m pip install --upgrade pip

spec="."
if [[ ${#extras[@]} -gt 0 ]]; then
    extras_csv="$(IFS=,; echo "${extras[*]}")"
    spec=".[${extras_csv}]"
fi

if [[ ${editable} -eq 1 ]]; then
    python -m pip install -e "${spec}"
else
    python -m pip install "${spec}"
fi

echo "UnicodeFix installed into ${env_label}."
if [[ ${created_env} -eq 1 ]]; then
    echo "Activate it with: source ${venv_dir}/bin/activate"
fi
echo "Run: cleanup-text --help"
