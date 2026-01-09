#!/usr/bin/env bash
set -euo pipefail
## cleanup-text test harness
# Usage:
#   tests/test_all.sh            Run all scenarios
#   tests/test_all.sh clean      Remove test_output/
#   tests/test_all.sh --help     Show this help
#
# Scenarios:
#   default       plain run, writes *.clean.*
#   batch         globbed invocation
#   invisible     -i in-place (-t)
#   nonewline     -n in-place (-t)
#   customout     -o into scenario dir
#   temp          -t copy per scenario
#   preservetmp   -t -p copy per scenario
#   stdout        stdin→stdout capture
#   keep_quotes   -Q in-place (-t)
#   keep_dashes   -D in-place (-t)
#   report_*      report-only modes (no diffs)

DATA_DIR="data"
OUT_DIR="test_output"
WC_BASE="tests/wcfiles.data"

usage() {
  grep '^#' "$0" | sed 's/^# //;s/^#//'
  exit 0
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage
if [[ "${1:-}" == "clean" ]]; then
  rm -rf "$OUT_DIR"
  echo "[i] ${OUT_DIR} removed"
  exit 0
fi

declare -a SOURCES FILENAMES BASES EXTS CLEAN_NAMES OUT_NAMES
while IFS= read -r path; do
  fname=$(basename "$path")
  [[ "$fname" == .* ]] && continue
  SOURCES+=("$path")
  FILENAMES+=("$fname")
  base="${fname%.*}"
  ext=""
  if [[ "$fname" == *.* ]]; then
    ext=".${fname##*.}"
  fi
  BASES+=("$base")
  EXTS+=("$ext")
  CLEAN_NAMES+=("${base}.clean${ext}")
  OUT_NAMES+=("${base}.out${ext}")
done < <(find "$DATA_DIR" -maxdepth 1 -type f ! -name '*.clean.*' | sort)

SCENARIOS=(
  "default::clean"
  "batch::batch"
  "invisible:-i:inplace"
  "nonewline:-n:inplace"
  "customout::custom_out"
  "temp:-t:inplace"
  "preservetmp:-t -p:inplace"
  "stdout::stdout"
  "keep_quotes:-Q:inplace"
  "keep_dashes:-D:inplace"
  "report_human:--report:report"
  "report_json:--report --json:report_json"
  "report_threshold1:--report --threshold 1:report_json"
  "report_stdin_json:--report --json:report_stdin"
)

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo "[i] Test files in $DATA_DIR:"
for name in "${FILENAMES[@]}"; do
  echo "  $name"
done
echo

for spec in "${SCENARIOS[@]}"; do
  IFS=':' read -r name opts mode <<< "$spec"
  dir="$OUT_DIR/$name"
  rm -rf "$dir"
  mkdir -p "$dir"
  wc_post="$dir/wcpost.txt"
  : > "$wc_post"
  declare -a targets=()

  echo "[i] Running: $name (${opts:-no opts})"
  IFS=' ' read -r -a opt_array <<< "$opts"

  if [[ "$mode" == "clean" || "$mode" == "batch" ]]; then
    for produced in "${CLEAN_NAMES[@]}"; do
      rm -f "$DATA_DIR/$produced"
    done
  fi

  if [[ "$mode" == "batch" && ${#SOURCES[@]} -gt 0 ]]; then
    ( cd "$DATA_DIR" && cleanup-text "${opt_array[@]}" ./* )
  fi

  for idx in "${!SOURCES[@]}"; do
    src="${SOURCES[idx]}"
    fname="${FILENAMES[idx]}"
    clean_name="${CLEAN_NAMES[idx]}"
    out_name="${OUT_NAMES[idx]}"
    target=""

    case "$mode" in
      clean)
        cleanup-text "${opt_array[@]}" "$src"
        produced="$DATA_DIR/$clean_name"
        if [[ -f "$produced" ]]; then
          target="$dir/$clean_name"
          mv "$produced" "$target"
        fi
        ;;
      batch)
        produced="$DATA_DIR/$clean_name"
        if [[ -f "$produced" ]]; then
          target="$dir/$clean_name"
          mv "$produced" "$target"
        fi
        ;;
      inplace)
        target="$dir/$fname"
        cp "$src" "$target"
        local_opts=("${opt_array[@]}")
        needs_t=1
        for opt in "${local_opts[@]}"; do
          if [[ "$opt" == "-t" ]]; then
            needs_t=0
            break
          fi
        done
        (( needs_t )) && local_opts+=("-t")
        cleanup-text "${local_opts[@]}" "$target"
        ;;
      stdout)
        if [[ "${EXTS[idx]}" == ".bin" ]]; then
          continue
        fi
        target="$dir/$fname"
        cleanup-text "${opt_array[@]}" < "$src" > "$target"
        ;;
      custom_out)
        target="$dir/$out_name"
        cleanup-text "${opt_array[@]}" "$src" -o "$target"
        ;;
      report)
        if cleanup-text "${opt_array[@]}" "$src" > "$dir/$fname.report"; then
          :
        else
          status=$?
          printf '[w] cleanup-text exited %s for %s (%s)\n' "$status" "$fname" "$name" >&2
        fi
        ;;
      report_json)
        if cleanup-text "${opt_array[@]}" "$src" > "$dir/$fname.json"; then
          :
        else
          status=$?
          printf '[w] cleanup-text exited %s for %s (%s)\n' "$status" "$fname" "$name" >&2
        fi
        ;;
      report_stdin)
        if cleanup-text "${opt_array[@]}" < "$src" > "$dir/$fname.json"; then
          :
        else
          status=$?
          printf '[w] cleanup-text exited %s for %s (%s)\n' "$status" "$fname" "$name" >&2
        fi
        ;;
    esac

    if [[ -n "$target" && -f "$target" ]]; then
      diff -u "$src" "$target" > "$dir/$fname.diff" || true
      targets+=("$target:$fname")
    fi
  done

  if (( ${#targets[@]} )); then
    for entry in "${targets[@]}"; do
      IFS=':' read -r tgt label <<< "$entry"
      wc "$tgt" | awk -v name="$label" '{ $NF=name; print }' >> "$wc_post"
    done
    diff -u "$WC_BASE" "$wc_post" > "$dir/wcdiff.txt" || true
  else
    rm -f "$wc_post"
  fi

  echo "[i] Done: $name"
  echo
done

# Validation: Check that newlines are preserved in cleaned files
echo "[i] Validating newline preservation..."
validation_failed=0
# Set nullglob to handle empty globs gracefully (saves current state)
if shopt -q nullglob 2>/dev/null; then
  nullglob_was_set=true
else
  nullglob_was_set=false
  shopt -s nullglob
fi
for dir in "$OUT_DIR"/default "$OUT_DIR"/batch "$OUT_DIR"/temp "$OUT_DIR"/invisible; do
  if [ ! -d "$dir" ]; then
    continue
  fi
  # Check each file type separately to avoid shellcheck issues with glob patterns
  for ext in txt py c md; do
    for file in "$dir"/*."$ext"; do
      # With nullglob, loop won't execute if no matches, but check anyway
      [ ! -f "$file" ] && continue
      # Check that file has at least one line (has newlines)
      line_count=$(wc -l < "$file" 2>/dev/null || echo "0")
      if [ "$line_count" -lt 1 ]; then
        echo "[✗] ERROR: $(basename "$file") in $(basename "$dir") has no lines (newlines may have been stripped)"
        validation_failed=1
      fi
      # Check that file doesn't appear to be a single collapsed line
      if [ "$line_count" -eq 0 ] && [ -s "$file" ]; then
        content_lines=$(wc -l < "$file" 2>/dev/null || echo "0")
        if [ "$content_lines" -eq 0 ]; then
          echo "[✗] WARNING: $(basename "$file") in $(basename "$dir") has content but no newlines"
        fi
      fi
    done
  done
done
# Restore nullglob setting
if [ "$nullglob_was_set" = false ]; then
  shopt -u nullglob
fi

if [ $validation_failed -eq 0 ]; then
  echo "[✓] Newline preservation validation passed"
else
  echo "[✗] Newline preservation validation failed"
  exit 1
fi

echo "[i] All scenarios complete → $OUT_DIR"
