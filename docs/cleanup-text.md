# Unicode Text Cleaner (`cleanup-text`) - v1.1.4

*Last updated: 2025-11-15*

A robust command-line tool to normalize and clean problematic Unicode characters, invisible characters, and formatting quirks from text files. Designed to make code and text more human, linter-friendly, and free of "AI tells" or watermarks.

## Features

- Converts smart quotes, EM/EN dashes, and non-breaking hyphens to ASCII equivalents
- Removes zero-width and other invisible Unicode characters (unless `-i` is used)
- Strips trailing whitespace from all lines
- Ensures (or suppresses) a single newline at EOF
- Batch processing of multiple files
- In-place cleaning with temp file safety
- Flexible output options (custom file, STDOUT, in-place)
- Comprehensive test suite for all features

## Usage

```sh
cleanup-text [options] [infile ...]
```

### Options

**Cleaning Options:**

- `-i`, `--invisible`              Preserve invisible Unicode characters (zero-width, non-breaking, etc.)
- `-Q`, `--keep-smart-quotes`      Preserve Unicode smart quotes (curly quotes, angle quotes, etc.)
- `-D`, `--keep-dashes`            Preserve Unicode EN/EM dashes
- `--keep-fullwidth-brackets`      Preserve fullwidth square brackets (【】)
- `-n`, `--no-newline`             Do not add a newline at the end of the output file (suppress final newline)

**Output Options:**

- `-o`, `--output`                 Output file name, or '-' for STDOUT. Only valid with one input file, or use '-' for STDOUT with multiple files.
- `-t`, `--temp`                   In-place cleaning: move each input file to .tmp, clean it, write cleaned output to original name, and delete .tmp after success.
- `-p`, `--preserve-tmp`           With -t, preserve the .tmp file after cleaning (do not delete it). Useful for backup or manual recovery.
- `-q`, `--quiet`                  Suppress status lines on stderr

**Report/Audit Options:**

- `--report`                       Generate a human-readable audit summary (no changes made to files)
- `--json`                         With --report, emit audit results as JSON
- `--csv`                          With --report, emit audit results as CSV (one row per file)
- `--label`                        When reading from STDIN ('-'), use this display name in report/CSV
- `--threshold` N                  With --report, exit 1 if total anomalies >= N
- `--metrics`                      With --report, include experimental semantic metrics (entropy, AI score, diversity, etc.)
- `--metrics-help`                 Print a legend explaining each metric and the ↑/↓ cues
- `--exit-zero`                    Force report mode to exit with status 0 (useful for informative hooks/CI jobs)
- `--no-color`                     Disable ANSI colors (plain output)

**General:**

- `-h`, `--help`                   Show help message and exit

### Behavior

**Input/Output:**

- **No input files:** Reads from STDIN and writes to STDOUT (filter mode)
- **Input files:** Creates cleaned files with `.clean` before the extension (e.g., `foo.txt` → `foo.clean.txt`)
- **-o -:** Forces output to STDOUT for all input files
- **-o <file>:** Writes to a single output file (only with one input file)
- **-t:** In-place cleaning with temp file safety
- **-t -p:** In-place cleaning, but preserves the temp file for manual recovery
- **-n:** Suppresses the final newline at EOF

**Preservation Flags:**

- **-Q:** Preserves Unicode smart quotes (useful for documents where typography matters)
- **-D:** Preserves EN/EM dashes (useful for documents where proper typography is desired)
- **--keep-fullwidth-brackets:** Preserves fullwidth brackets (useful for documents with CJK text)
- **-i:** Preserves invisible characters (rare, mainly for debugging)

**Report Mode:**

- **--report:** Generates an audit without modifying files. Use with `--json` or `--csv` for machine-readable output.
- **--threshold N:** Exits with code 1 if total anomalies >= N (useful for CI/CD)
- **--exit-zero:** Always exits with code 0 even if threshold exceeded (useful for pre-commit warnings)
- **--metrics:** Requires NLP extras (`pip install .[nlp]`) for semantic analysis
- **--metrics-help:** Print legend without running a report

### Semantic Metrics (preview)

Enabling `--metrics` while running in report mode appends a `metrics` block that captures entropy, ASCII ratio, type/token diversity, heuristic AI-likeness scoring, and more. The feature requires the optional NLP extras (`pip install .[nlp]`) to supply the NLTK resources used for tokenization. Use `--metrics-help` for a quick legend explaining each metric and the ↑/↓ direction hints shown in the report. Pair with `--exit-zero` if you want to surface the data without failing pre-commit.

## Test Suite

A comprehensive test script is provided in `tests/test_all.sh` to verify all features and options.

### Running the Test Suite

From the project root:

```sh
tests/test_all.sh
```

- Builds its file list directly from `data/`, so you always exercise the current fixtures.
- Generates canonical diffs (`*.diff`) and normalized `wcpost.txt` / `wcdiff.txt` files per scenario.
- The STDIN/STDOUT scenario skips binary fixtures (everything else still covers them).
- To clean up all test output:

```sh
tests/test_all.sh clean
```

- For help:

```sh
tests/test_all.sh --help
```

## Best Practices

- Always back up your data before batch processing or in-place cleaning.
- Review diffs and word counts in `test_output/` to verify results.
- Use the `-i` flag if you need to preserve invisible Unicode characters for special use cases.
- Use the `-n` flag if you need to suppress the final newline (rare).

## Alignment & Fullwidth Brackets

- Fullwidth square brackets are now folded to ASCII by default to preserve monospace alignment in terminals and fixed-width tables:
  - `【` → `[`, `】` → `]`
  - Use `--keep-fullwidth-brackets` to preserve `【】`.
  - The dagger glyph `†` (e.g., `†L147-L156`) is preserved.
- A small helper exists for display-only folding:
  - `unicodefix.transforms.fold_for_terminal_display(text)` applies the same folding without other cleaning.
  - Useful when you want ASCII rendering for terminals while keeping the original text for auditing/search.
- Patterns:
  1) Global pre-clean before render (default behavior).
  2) Render-time folding behind a toggle (use the helper).

## Changelog

See `CHANGELOG.md` for a summary of recent changes.

## License

See `LICENSE` for details.
