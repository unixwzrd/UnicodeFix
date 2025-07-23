# Unicode Text Cleaner (`cleanup-text`)

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
- `-i`, `--invisible`      Preserve invisible Unicode characters (zero-width, non-breaking, etc.)
- `-n`, `--no-newline`     Do not add a newline at the end of the output file (suppress final newline)
- `-o`, `--output`         Output file name, or '-' for STDOUT. Only valid with one input file, or use '-' for STDOUT with multiple files.
- `-t`, `--temp`           In-place cleaning: move each input file to .tmp, clean it, write cleaned output to original name, and delete .tmp after success.
- `-p`, `--preserve-tmp`   With -t, preserve the .tmp file after cleaning (do not delete it). Useful for backup or manual recovery.
- `-h`, `--help`           Show help message and exit

### Behavior
- **No input files:** Reads from STDIN and writes to STDOUT (filter mode)
- **Input files:** Creates cleaned files with `.clean` before the extension (e.g., `foo.txt` → `foo.clean.txt`)
- **-o -:** Forces output to STDOUT for all input files
- **-o <file>:** Writes to a single output file (only with one input file)
- **-t:** In-place cleaning with temp file safety
- **-t -p:** In-place cleaning, but preserves the temp file for manual recovery
- **-n:** Suppresses the final newline at EOF

## Test Suite
A comprehensive test script is provided in `test/test_all.sh` to verify all features and options.

### Running the Test Suite
From the project root:

```sh
./test/test_all.sh
```

- Results are written to `test_output/` with subdirectories for each scenario.
- Diffs and word count summaries are provided for easy verification.
- To clean up all test output:

```sh
./test/test_all.sh clean
```

- For help:

```sh
./test/test_all.sh --help
```

## Best Practices
- Always back up your data before batch processing or in-place cleaning.
- Review diffs and word counts in `test_output/` to verify results.
- Use the `-i` flag if you need to preserve invisible Unicode characters for special use cases.
- Use the `-n` flag if you need to suppress the final newline (rare).

## Changelog
See `CHANGELOG.md` for a summary of recent changes.

## License
See `LICENSE` for details.
