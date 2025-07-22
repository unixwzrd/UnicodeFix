#!/usr/bin/env bash

# Test script for cleanup-text
# Systematically tests all major options and outputs results to test_output/<scenario>/
# Prints word counts and diffs for each scenario for easy verification.
# Usage: ./test_all.sh [clean|-h|--help]
#   If 'clean' is given as the first argument, deletes test_output/ and exits.
#   If '-h' or '--help' is given, prints this help message and exits.

DATA_DIR="data"
OUT_DIR="test_output"

# Print help message
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
  grep '^#' "$0" | sed 's/^# //;s/^#//'
  exit 0
fi

# Clean up output directory if 'clean' is given
if [[ "$1" == "clean" ]]; then
  echo "[i] Cleaning up $OUT_DIR..."
  rm -rf "$OUT_DIR"
  echo "[i] Done."
  exit 0
fi

# Define test scenarios: name, options
SCENARIOS=(
  "default::"
  "invisible:-i"
  "nonewline:-n"
  "customout:"
  "temp:-t"
  "preservetmp:-t -p"
  "stdout:STDIN"
)

# Clean and recreate output directory
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# List files to be tested
echo "[i] Test files in $DATA_DIR:"
ls -1 "$DATA_DIR"
echo

# Save original word counts (excluding non-regular files)
ls -1v "$DATA_DIR" | grep -vE '\.diff$|^wc' | xargs -I{} wc "$DATA_DIR/{}" > "$OUT_DIR/wcpre.txt"
echo "[i] Original word counts:"
cat "$OUT_DIR/wcpre.txt"
echo

for scenario in "${SCENARIOS[@]}"; do
  name="${scenario%%:*}"
  opts="${scenario#*:}"
  dir="$OUT_DIR/$name"
  mkdir -p "$dir"
  echo "[i] Running scenario: $name (options: $opts)"

  for file in "$DATA_DIR"/*; do
    fname=$(basename "$file")
    base="${fname%.*}"
    ext="${fname##*.}"
    if [[ "$base" == "$fname" ]]; then
      ext=""
    else
      ext=".$ext"
    fi
    out="$dir/$fname"
    diffout="$dir/$fname.diff"

    case "$name" in
      customout)
        cleanup-text "$file" -o "$out"
        ;;
      temp)
        cp "$file" "$out"
        cleanup-text $opts "$out"
        ;;
      preservetmp)
        cp "$file" "$out"
        cleanup-text $opts "$out"
        ;;
      stdout)
        cleanup-text < "$file" > "$out"
        ;;
      *)
        cleanup-text $opts "$file" -o "$out"
        ;;
    esac

    diff "$file" "$out" > "$diffout" || true
    if diff -q "$file" "$out" > /dev/null; then
      echo "  [$name/$fname] [!] No change (already clean?)"
    else
      echo "  [$name/$fname] [✓] Cleaned"
    fi
  done

  echo
  echo "[i] Files in scenario '$name':"
  ls -1v "$dir"
  echo
  echo "[i] Word counts for scenario '$name':"
  ls -1v "$dir" | grep -vE '\.diff$|^wc' | xargs -I{} wc "$dir/{}" > "$dir/wcpost.txt"
  cat "$dir/wcpost.txt"
  echo
  echo "[i] Diff of word counts (original vs. '$name'):"
  diff "$OUT_DIR/wcpre.txt" "$dir/wcpost.txt" > "$dir/wcdiff.txt" || true
  cat "$dir/wcdiff.txt"
  echo
  echo "[i] Done with scenario: $name"
  echo

done

echo "[i] All test scenarios complete. Check $OUT_DIR for results." 