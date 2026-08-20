#!/usr/bin/env bash

# Compatibility wrapper for the installed UnicodeFix command.

set -euo pipefail

if ! command -v cleanup-text >/dev/null 2>&1; then
    echo "uniclean: cleanup-text is not installed or is not on PATH" >&2
    exit 127
fi

exec cleanup-text "$@"
