# Test Suite for cleanup-text

## Overview

The test suite for `cleanup-text` is designed to systematically verify all features, options, and edge cases of the tool. It ensures that the script works as expected across a variety of scenarios, and that it safely handles files without overwriting your original data.

## What the Test Script Does
- Processes all files in the `data/` directory using every major option and combination
- Outputs results to `test_output/` with subdirectories for each scenario
- Saves per-file diffs and batch word count summaries for easy review
- Supports a `clean` option to remove all test output
- Provides a help message for usage

## How to Run the Test Suite

From the project root directory:

```sh
./test/test_all.sh
```

- This will process every file in `data/` through all test scenarios.
- Results are written to `test_output/` with a subdirectory for each scenario (e.g., `default`, `invisible`, `nonewline`, etc.).
- Each scenario directory contains:
  - Cleaned output files
  - `.diff` files showing changes from the original
  - `wcpost.txt` (word counts after cleaning)
  - `wcdiff.txt` (diff of word counts before/after)

### Cleaning Up Test Output

To remove all test output and start fresh:

```sh
./test/test_all.sh clean
```

### Getting Help

```sh
./test/test_all.sh --help
```

## Test Scenarios

The script tests the following scenarios:
- **default:** Standard cleaning (removes Unicode quirks, normalizes text)
- **invisible:** Preserves invisible Unicode characters (`-i`)
- **nonewline:** Suppresses final newline at EOF (`-n`)
- **customout:** Uses a custom output file name (`-o`)
- **temp:** In-place cleaning with temp file safety (`-t`)
- **preservetmp:** In-place cleaning, preserves temp file for backup (`-t -p`)
- **stdout:** Cleans via STDIN/STDOUT mode

## Interpreting Results
- **Diffs:** Each `.diff` file shows the exact changes made to each file in each scenario.
- **Word Counts:** `wcpost.txt` shows word/line/character counts after cleaning. `wcdiff.txt` shows the difference from the original.
- **No Change:** If a file is already clean, the script will note "No change (already clean?)".
- **Cleaned:** If a file was modified, the script will note "Cleaned".

## Best Practices
- Always back up your data before running tests.
- Review diffs and word counts to verify results.
- Use the test suite to validate changes before integrating into CI/CD pipelines.
- Never run the test script from inside the `test/` directory - always run from the project root.

## CI/CD Integration
- The test suite can be integrated into your CI/CD pipeline to ensure all code and text files are clean and free of AI artifacts before deployment or publication.

## See Also
- [docs/cleanup-text.md](cleanup-text.md) for full documentation of all features and options.
