#!/usr/bin/env bash

# Uniclean is a wrapper fro cleanup-text.py which ensures the proper virtual environment
# is activated and the script is run from the root of the project.

# Activate the virtual environment
source "${HOME}/.bashrc"

# Run the cleanup-text.py script
cleanup-text.py "$@"