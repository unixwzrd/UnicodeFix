# Changelog for UnicodeFix

Last updated: 2026-01-08

## 20260108_02 - v1.1.9

### **CI/CD Pipeline & Python 3.9 Compatibility**

- **GitHub Actions CI/CD**: Comprehensive automated testing pipeline running on every push and pull request
  - **Test matrix**: Ubuntu latest and macOS latest × Python 3.9, 3.10, 3.11, and 3.12 (8 combinations)
  - **Test jobs**: Python unit tests (pytest with coverage), integration test suite, newline preservation validation
  - **Linting jobs**: Code formatting (black), linting (ruff), shell script linting (shellcheck)
  - **All tests passing**: Verified working across all OS and Python version combinations
- **Python 3.9 compatibility fixes**: Replaced Python 3.10+ type hint syntax with Python 3.9-compatible alternatives
  - Changed `int | str` to `Union[int, str]` from `typing` module
  - Changed `int | None` to `Optional[int]` from `typing` module
  - Changed `list[str]` to `List[str]` and `dict[str, dict]` to `Dict[str, dict]` for type hints
  - All code now compatible with Python 3.9 through 3.12
- **Enhanced test coverage**: Added 7 comprehensive newline preservation tests to prevent regression
- **Test suite robustness**: Fixed bash script issues for strict mode (`set -euo pipefail`)
  - Fixed unbound variable errors with empty arrays using `declare -a` and safe length checks
  - Fixed shellcheck warnings and syntax errors
  - Improved glob pattern handling with `nullglob` for better compatibility
- **Development dependencies**: Added `dev` optional dependencies group to `pyproject.toml`
  - Includes: `black>=24.0`, `ruff>=0.1.0`, `pytest>=7.0`, `pytest-cov>=4.0`
  - Install with: `pip install -e ".[dev]"`
- **Code formatting**: All Python files formatted with black to meet style standards
- **CI workflow improvements**: Better PATH handling, fallback to `python -m unicodefix.cli` when `cleanup-text` not in PATH

## 20260108_00 - v1.1.8

### **Critical Bug Fix: Newline Preservation**

- **Fixed newline stripping bug:** The character validation logic was incorrectly removing newlines (`\n`), carriage returns (`\r`), and tabs (`\t`) because `unicodedata.name()` raises `ValueError` for these control characters and they're not "printable". Fixed by explicitly preserving these essential control characters before the validation check.
- **Impact:** Files were being collapsed into single lines. This is now fixed and newlines are properly preserved.
- **Root cause:** The invalid character filtering code was checking `char.isprintable()` for characters without Unicode names, which excluded essential control characters like newlines.

## 20260107_02 - v1.1.7

### **Fixed CLI Indentation Errors**

- **Fixed syntax errors in `cli.py`**: Corrected indentation issues in the `try/except` block within the `process_file` function that were causing syntax errors and preventing the CLI from running correctly
- **Proper exception handling**: Fixed misaligned exception handling blocks that were causing `IndentationError` exceptions
- **Code quality**: All linter errors resolved, ensuring the CLI module can be imported and executed without syntax errors

## 20260107_01 - v1.1.6

### **Enhanced Invalid Unicode Character Filtering**

- **Added comprehensive invalid character removal**: Now removes characters that raise `ValueError` when looking up Unicode name (invalid/unassigned code points)
- **Private Use Area filtering**: Removes private use area characters (U+E000-U+F8FF, U+F0000-U+FFFFD, U+100000-U+10FFFD) which are often artifacts from encoding issues
- **Unassigned character removal**: Filters out unassigned characters (category "Cn") above ASCII range
- **Surrogate character filtering**: Removes surrogate characters (U+D800-U+DFFF) that shouldn't appear in valid UTF-8 strings
- **Preserves valid ASCII**: Basic printable ASCII characters (code < 128) are preserved even if they lack Unicode metadata
- **Better handling of corrupted encoding**: Catches edge cases where invalid bytes are decoded incorrectly, preventing display of garbage characters like `e249`, `9980`, `bfef` sequences

These changes improve the robustness of text cleaning, especially when processing text from language models or corrupted input sources.

## 2026-01-07

### Unicode normalization fix (v1.1.5)

- **Fixed replacement character removal**: Explicitly removed Unicode replacement characters (U+FFFD) from the text to prevent them from being displayed in the output.
- **Improved fallback logic**: Enhanced pattern matching to catch quote-like characters by Unicode name patterns, not just category, ensuring no quotes slip through by default.
- **Extended ASCII preservation**: Quotes in extended ASCII range (like « and ») are now normalized while preserving intentional extended ASCII characters (é, ñ, etc.).

## 2025-12-30

### Aggressive Unicode normalization fix (v1.1.4)

- **Fixed quote normalization**: Expanded comprehensive mapping to catch ALL Unicode quote and apostrophe variants, including Hebrew (geresh/gershayim), Greek (psili/dasia), modifier letters, and fullwidth variants. Default behavior now aggressively normalizes all quote-like characters to ASCII ' and ".
- **Improved fallback logic**: Enhanced pattern matching to catch quote-like characters by Unicode name patterns, not just category, ensuring no quotes slip through by default.
- **Extended ASCII preservation**: Quotes in extended ASCII range (like « and ») are now normalized while preserving intentional extended ASCII characters (é, ñ, etc.).
- README: clarified installation modes (standard, editable, and NLP extras), tightened wording, and refreshed badges/links.
- Setup: improved guidance printed by `setup.sh` after environment creation; clarified quick start steps.
- Requirements: synced with current packaging to ensure local venv installs match `pyproject.toml` expectations.
- Normalization: fold fullwidth square brackets 【】 to ASCII [] by default; add `--keep-fullwidth-brackets` to preserve them; dagger `†` remains untouched.
- **Breaking change**: Default behavior is now more aggressive—all Unicode quotes are normalized unless `-Q` flag is used. This aligns with the package name "UnicodeFix"—fixing Unicode by default, not preserving it.

## 2025-09-18

### Test Harness Simplification & Metrics Preview

- Rebuilt `tests/test_all.sh` to derive its file list directly from `data/`, drive glob/batch runs with a single command, and rely on `-t` for in-place scenarios.
- STDIN/STDOUT scenario now skips binary fixtures to avoid Python's UTF-8 decoding errors, while every other scenario still exercises them.
- Normalized diffs and `wc` comparisons are produced per scenario without duplicating helper logic.
- Updated README, docs/cleanup-text.md, and docs/test-suite.md with the new run commands, behavior notes, cleanup instructions, and the preview `--metrics` documentation.
- Bumped version to 1.1.0 and documented the experimental semantic metrics (`--metrics`, `--metrics-help`).
- Added `--exit-zero` so report/metrics runs can inform pre-commit hooks without aborting the workflow.
- Installation is now Pip based.

## 2025-09-07

### CodExorcism Release

- Expanded quote normalization: map additional Unicode quote/prime/angle/fullwidth marks to ASCII ' and " for shell-safe output
- Added new options:
  - `-Q` / `--keep-smart-quotes`: preserve Unicode curly/smart quotes
  - `-D` / `--keep-dashes`: preserve EN/EM dashes
- Normalize ellipses: `…` (U+2026) and `⋯` (U+22EF) → `...`; `‥` (U+2025) → `..`
- Normalize Unicode spaces: replace NBSP (U+00A0), NARROW NBSP (U+202F), EN/EM/THIN spaces (U+2000–U+200A), IDEOGRAPHIC SPACE (U+3000), etc., with ASCII space
- Remove bidi/zero-width controls: strip LRM/RLM, embeddings/overrides/isolates, ZWSP/ZWNJ/ZWJ, BOM
- Refined VS Code filter handling: only apply newline compensation in filter mode; never in file-write modes; respect CI/CD env
- Note: These artifacts were observed in content produced by Codex/VS Code extensions
- No breaking changes; behavior unchanged for already-clean inputs

## 2025-07-28

### **Extended ASCII Preservation Fix**

- **Switched from Unidecode to ftfy:** Replaced aggressive Unicode-to-ASCII conversion with intelligent text fixing
- **Preserves Extended ASCII:** Now correctly preserves 8-bit extended ASCII characters (128-255) like é, ñ, ü, etc.
- **Smarter Unicode Handling:** Only converts problematic Unicode characters while preserving intentional extended ASCII usage
- **Updated Dependencies:** Replaced `Unidecode` dependency with `ftfy` in requirements.txt
- **Maintains AI Artifact Removal:** Still removes smart quotes, EM/EN dashes, and other "AI tells" as designed

## 2025-07-23

### **Test Suite Fixes & Validation**

- **Fixed Default Scenario:** Corrected test script to properly handle default behavior (creates `.clean.ext` files) without using `-o` flag that caused errors with multiple files
- **Cascading File Prevention:** Added filtering to prevent processing already-cleaned `.clean.ext` files in subsequent test runs
- **Comprehensive Test Validation:** All 7 test scenarios now pass successfully:
  - Default: Creates `.clean.ext` files correctly
  - Invisible (`-i`): Preserves invisible Unicode characters (higher word counts)
  - Nonewline (`-n`): Suppresses final newline (lower character counts)
  - Customout: Uses `-o` option for custom output names
  - Temp (`-t`): In-place cleaning with temp file deletion
  - Preservetmp (`-t -p`): In-place cleaning with temp file preservation
  - Stdout: STDIN/STDOUT filter mode
- **Verified Unicode Cleaning:** Confirmed proper conversion of smart quotes, EM/EN dashes, and non-breaking hyphens across all scenarios
- **Test Output Organization:** Each scenario creates organized output with cleaned files, diffs, and word count comparisons in `test_output/` directory

## 2025-07-22

### **Major Release - "Enough of Your AI Nonsense" Edition**

- **CLI Supercharged:** Added new power flags:
  `-i` / `--invisible` (preserve zero-width/invisible Unicode)
  `-n` / `--no-newline` (suppress final newline at EOF)
  `-o` / `--output` (custom output file or STDOUT)
  `-t` / `--temp` (safe in-place cleaning)
  `-p` / `--preserve-tmp` (backup your .tmp files if you're paranoid)
- **AI Artifact Killer:** Cranked up removal of invisible Unicode, "AI tells," EM/EN dashes, curly/smart quotes, and digital fingerprints from text, code, and prose.
- **Cleaner Output:** Output files now use `.clean` before the extension for extra safety.
- **Help & Error Output:** Help and error messages are clearer, less cryptic, and actually readable.
- **Epic Test Suite:** All-new `tests/test_all.sh` script automates batch tests, diffs, word counts, and deep-clean scenarios - review everything in `test_output/` before you ship or commit.
- **Docs & Best Practices:** README and docs overhauled with real-world examples, pro tips, and fresh install/usage details (plus a *lot* more attitude).
- **CI/CD Ready:** Use in your pre-commit, CI pipeline, or just blast through homework/AI-proofreading artifacts for fun.
- **Because I got tired of looking at garbage code.**

*If you're tired of code and docs that look like they were written by a bot, this release is for you.*

## 2025-04-27 20250427_01-update

- Update README
- Update cleanup-text.py to handle trailing whitespace
- Whitespace on empty lines (newline preserved)

## 2025-04-26 20250427_00-release

- Added STDIO pipe handling as a filter

## 2025-04-26

- Initial release
