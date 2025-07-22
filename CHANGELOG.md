# Changelog for UnicodeFix

## 2025-07-22

**Major Release – “Enough of Your AI Nonsense” Edition**

- **CLI Supercharged:** Added new power flags:  
  `-i` / `--invisible` (preserve zero-width/invisible Unicode)  
  `-n` / `--no-newline` (suppress final newline at EOF)  
  `-o` / `--output` (custom output file or STDOUT)  
  `-t` / `--temp` (safe in-place cleaning)  
  `-p` / `--preserve-tmp` (backup your .tmp files if you’re paranoid)
- **AI Artifact Killer:** Cranked up removal of invisible Unicode, “AI tells,” EM/EN dashes, curly/smart quotes, and digital fingerprints from text, code, and prose.
- **Cleaner Output:** Output files now use `.clean` before the extension for extra safety.
- **Help & Error Output:** Help and error messages are clearer, less cryptic, and actually readable.
- **Epic Test Suite:** All-new `test/test_all.sh` script automates batch tests, diffs, word counts, and deep-clean scenarios—review everything in `test_output/` before you ship or commit.
- **Docs & Best Practices:** README and docs overhauled with real-world examples, pro tips, and fresh install/usage details (plus a *lot* more attitude).
- **CI/CD Ready:** Use in your pre-commit, CI pipeline, or just blast through homework/AI-proofreading artifacts for fun.
- **Because I got tired of looking at garbage code.**

*If you’re tired of code and docs that look like they were written by a bot, this release is for you.*

## 2025-04-27 20250427_01-update
- Update README
- Update cleanup-text.py to handle trailing whitespace
- Whitespace on empty lines (newline preserved)

## 2025-04-26 20250427_00-release
- Added STDIO pipe handling as a filter

## 2025-04-26
- Initial release
