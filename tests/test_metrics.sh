#!/usr/bin/env bash

mode="human"   # default
[ "$1" == "--csv" ] && mode="csv"

for f in data/test_ai*.txt; do
    if [ "$mode" = "csv" ]; then
        cleanup-text --report --metrics --csv "$f"
        cleanup-text "$f" -o - | cleanup-text --report --metrics --csv --label "$f"
    else
        echo "Original Version== $f"
        cleanup-text --report --metrics "$f"
        echo "Cleaned Version== $f"
        cleanup-text "$f" -o - | cleanup-text --report --metrics --label "$f"
        echo -e "\n\n\n"
    fi
done