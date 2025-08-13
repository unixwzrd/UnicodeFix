# Changelog for UnicodeFix

## 2025-08-12

### Minor patch
- Expanded quote normalization: map additional Unicode quote/prime/angle/fullwidth marks to ASCII ' and " for shell-safe output
- Refined VS Code filter handling: only apply newline compensation in filter mode; never in file-write modes; respect CI/CD env
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
- **Epic Test Suite:** All-new `test/test_all.sh` script automates batch tests, diffs, word counts, and deep-clean scenarios - review everything in `test_output/` before you ship or commit.
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
