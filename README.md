# UnicodeFix - *CodExorcism Edition+ v1.1.4*

*Last updated: 2025-12-30*

![UnicodeFix Hero Image](docs/controlling-unicode.png)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Release](https://img.shields.io/github/v/tag/unixwzrd/UnicodeFix?label=release)](https://github.com/unixwzrd/UnicodeFix/releases)

- [UnicodeFix - *CodExorcism Edition+ v1.1.4*](#unicodefix---codexorcism-edition-v114)
    - [**Finally - a tool that blasts AI fingerprints, torches those infuriating smart quotes, and leaves your code \& docs squeaky clean for real humans.**](#finally---a-tool-that-blasts-ai-fingerprints-torches-those-infuriating-smart-quotes-and-leaves-your-code--docs-squeaky-clean-for-real-humans)
  - [Why Is This Happening?](#why-is-this-happening)
  - [Installation](#installation)
  - [Usage](#usage)
    - [New options](#new-options)
      - [When to preserve invisible characters (`-i`)](#when-to-preserve-invisible-characters--i)
  - [Brief Examples](#brief-examples)
    - [Pipe / Filter (STDIN to STDOUT)](#pipe--filter-stdin-to-stdout)
    - [Batch Clean](#batch-clean)
    - [In-Place (Safe) Clean](#in-place-safe-clean)
    - [Preserve Temp File for Backup](#preserve-temp-file-for-backup)
    - [Audit only (no changes), human-readable](#audit-only-no-changes-human-readable)
    - [Audit as JSON](#audit-as-json)
    - [Audit with Semantic Metrics (experimental)](#audit-with-semantic-metrics-experimental)
    - [Report without blocking commits](#report-without-blocking-commits)
    - [Fail CI if anomalies exceed threshold](#fail-ci-if-anomalies-exceed-threshold)
    - [Using in vi/vim/macvim](#using-in-vivimmacvim)
  - [What's New / What's Cool](#whats-new--whats-cool)
    - [CodexExorcism+ Release (Sept 2025)](#codexexorcism-release-sept-2025)
    - [CodexExorcism Release (Sept 2025)](#codexexorcism-release-sept-2025-1)
    - [Previous Releases](#previous-releases)
    - [Keep It Fresh](#keep-it-fresh)
  - [Shortcut for macOS](#shortcut-for-macos)
    - [To add the Shortcut](#to-add-the-shortcut)
  - [What's in This Repository](#whats-in-this-repository)
  - [Testing and CI/CD](#testing-and-cicd)
  - [Contributing](#contributing)
  - [Support This and Other Projects](#support-this-and-other-projects)
  - [Changelog](#changelog)
  - [License](#license)

---

### **Finally - a tool that blasts AI fingerprints, torches those infuriating smart quotes, and leaves your code & docs squeaky clean for real humans.**

Ever open up a file and instantly know it came from ChatGPT, Copilot, or one of their AI cousins? (Yeah, so can everyone else now.)
UnicodeFix vaporizes all the weird dashes, curly quotes, invisible space ninjas, and digital "tells" that out you as an AI user - or just make your stuff fail linters and code reviews.

**Whether you're a student, a dev, or an open-source rebel: this is your "eraser for AI breadcrumbs."**

*Yes, it helps students cheat on their homework.*
It also makes blog posts and AI-proofed emails look like you sweated over every character.
Nearly a thousand people have grabbed it. Nobody's bought me a coffee yet, but hey… there's a first time for everything.

---

## Why Is This Happening?

Some folks think all this Unicode cruft is a side-effect of generative AI's training data. Others believe it's a deliberate move - baked-in "watermarks" to ID machine-generated text. Either way: these artifacts leave a trail. UnicodeFix wipes it.

Be careful, professors and reviewers may even start planting Unicode honeypots in starter code or essays - UnicodeFix torches those too. In this "AI Arms Race," `diff` and `vimdiff` are your night-vision goggles.

---

## Installation

Clone the repository and run the setup script:

```bash
git clone https://github.com/unixwzrd/UnicodeFix.git
cd UnicodeFix

# This will create a VENV for python 3.10+ and install the dependencies
./setup.sh

# This will install teh UnicodeFix package, you can install one of three ways -"
# For simply running the script, use the following command:
pip install .

# If you wish to do development, or want to use the package in your own projects, use the following command:
pip install -e .

# if you wish to use teh optional NLTK analytics, install the following optional extras for current and future NLP metrics:
pip install .[nlp]
```

The `setup.sh` script:

- Creates a Python virtual environment just for UnicodeFix
- Installs dependencies
- Adds handy startup config to your `.bashrc` for one-command usage

See [setup.sh](setup.sh) for the nitty-gritty.

For serious environment nerds: [VenvUtil](https://github.com/unixwzrd/venvutil) is my full-featured Python env toolkit.

---

## Usage

Once installed and activated:

```bash
(LLaSA-speech) [unixwzrd@xanax: bin]$ cleanup-text --help

usage: cleanup-text [-h] [-i] [-Q] [-D] [--keep-fullwidth-brackets] [-n] [-o OUTPUT] [-t] [-p] [infile ...]

Clean Unicode quirks from text. If no input files are given, reads from STDIN and writes to STDOUT (filter mode). If input files are given, creates cleaned files with .clean before the extension (e.g., foo.txt -> foo.clean.txt). Use -o - to force output to STDOUT for all input files, or -o <file> to specify a single output file (only with one
input file).

positional arguments:
  infile                Input file(s)

options:
  -h, --help            show this help message and exit
  -i, --invisible       Preserve invisible Unicode characters (zero-width, bidi controls, etc.)
  -Q, --keep-smart-quotes
                        Preserve Unicode smart quotes (do not convert to ASCII)
  -D, --keep-dashes     Preserve Unicode EN/EM dashes (do not convert to ASCII)
  --keep-fullwidth-brackets
                        Preserve fullwidth square brackets (【】) (do not fold to ASCII)
  -n, --no-newline      Do not add a newline at the end of the output file (suppress final newline).
  -o OUTPUT, --output OUTPUT
                        Output file name, or '-' for STDOUT. Only valid with one input file, or use '-' for STDOUT with multiple files.
  -t, --temp            In-place cleaning: Move each input file to .tmp, clean it, write cleaned output to original name, and delete .tmp after success.
  -p, --preserve-tmp    With -t, preserve the .tmp file after cleaning (do not delete it). Useful for backup or manual recovery.
```

### New options

- `-Q`, `--keep-smart-quotes`: Preserve Unicode smart quotes (curly single/double quotes). Useful when preparing prose/blog posts where typographic quotes are intentional. Default behavior converts them to ASCII for shell/CI safety.
- `-D`, `--keep-dashes`: Preserve EN/EM dashes. Useful when stylistic punctuation is desired in prose. Default behavior converts EM dash to ` - ` and EN dash to `-`.
- `--keep-fullwidth-brackets`: Preserve fullwidth square brackets (`【】`). By default, they are folded to ASCII `[]` to keep monospace alignment in terminals and fixed-width tables.
- `-R`, `--report`: Audit text for anomalies, human-readable.
- `-J`, `--json`: Audit text for anomalies, JSON format.
- `-T`, `--threshold`: Fail CI if anomalies exceed threshold.
- `--metrics`: Attach experimental semantic metrics (entropy, AI-score, etc.) to reports.
- `--metrics-help`: Print friendly descriptions of each metric and the ↑/↓ hints.
- `--exit-zero`: Force a zero exit code for report mode (handy for informative hooks/CI jobs).
- `-H`, `--help`: Show help message and exit.
- `-V`, `--version`: Show version and exit.

#### When to preserve invisible characters (`-i`)

In most code/CI workflows, invisible/bidi controls are accidental and should be removed (default). Rare cases to preserve (`-i`):

- Linguistic text where ZWJ/ZWNJ influence shaping
- Intentional watermarks/markers in text
- Forensic/debug inspections before deciding what to strip

## Brief Examples

### Pipe / Filter (STDIN to STDOUT)

```bash
cat file.txt | cleanup-text > cleaned.txt
```

### Batch Clean

```bash
cleanup-text *.txt
```

### In-Place (Safe) Clean

```bash
cleanup-text -t myfile.txt
```

### Preserve Temp File for Backup

```bash
cleanup-text -t -p myfile.txt
```

### Audit only (no changes), human-readable

```bash
cleanup-text --report foo.txt
```

### Audit as JSON

```bash
cleanup-text --report --json foo.txt
```

### Audit with Semantic Metrics (experimental)

```bash
cleanup-text --report --json --metrics foo.txt
```

Produces the JSON report plus a `metrics` section containing entropy, diversity, heuristic AI score, and more. Requires `pip install .[nlp]` for NLTK resources.

### Report without blocking commits

```bash
cleanup-text --report --metrics --exit-zero foo.txt
```

Emits the full report (and metrics if requested) but always returns exit code 0, so informational pre-commit hooks and dashboards can surface issues without aborting the workflow.

### Fail CI if anomalies exceed threshold

```bash
cleanup-text --report --threshold 1 some/*.txt
```

### Using in vi/vim/macvim

```vim
:%!cleanup-text
```

Works great for vi/Vim purists, VS Code hipsters, or anyone who just wants their text to behave like text.
Also handy if you’re trying to slip your AI-generated code past your CS prof without curly quotes giving you away.

You can run it from Vim, VS Code in Vim mode, or as a pre-commit. Use it for email, blog posts, whatever. Ignore the naysayers - this is *real-world convenience.*

See [cleanup-text.md](docs/cleanup-text.md) for deeper dives and arcane options.

- **Make sure your Python environment is activated** before launching your editor, or wrap it in a shell script that does it for you.
- Adjust your editor's shell settings as needed for best results.

---

## What's New / What's Cool

### CodexExorcism+ Release (Sept 2025)  

The follow-up release keeps the Unicode exorcism vibe but layers on early-stage semantics:  

- **Semantic metrics preview** – opt into `--metrics` for entropy, diversity, repetition, and a heuristic AI-likeness score right inside `--report` / `--json` output.  
- **Metrics legend on demand** – `--metrics-help` explains every stat plus the ↑/↓ hints.  
- **Hook-friendly reporting** – `--exit-zero` means pre-commit hooks can flag anomalies without blocking your commit.  
- **Slimmer all-in-one test harness** – `tests/test_all.sh` derives its run list from `data/`, handles STDIN/STDOUT quirks, and drops per-scenario diffs/word-count deltas.  

### CodexExorcism Release (Sept 2025)  

Exorcise your code from VS Code/Codex’s funky Unicode artifacts (NBSPs, bidi controls, smart quotes).  

- **Safer EOF handling in VS Code filter mode**  
- **Normalizes more sneaky Codex/AI fingerprints**
- **Ellipsis Eradication**

### Previous Releases

- **Normalizes EM/EN dashes to true ASCII - no more AI " - " nonsense**
- **Wipes AI "tells," watermarks, and digital fingerprints**
- **Fixes trailing whitespace, normalizes newlines, burns the digital junk**
- **Portable (Python 3.7+), cross-platform**
- **Integrated macOS Shortcut for right-click cleaning in Finder**
- **Can be used in CI/CD - but also by normal humans, not just pipeline freaks**

> *Fun fact*: Even Python will execute code with "curly quotes." Your IDE, email client, and browser all sneak these in. UnicodeFix hunts them down and torches them, ...so your coding homework looks *lovingly hand-crafted* at 4:37 a.m., rather than LLM spawn.

### Keep It Fresh

Pull requests/issues always welcome - especially if your AI friend slipped a new weird Unicode gremlin past me, I found a few more while preparing this release too...🙄

---

## Shortcut for macOS

UnicodeFix ships with a macOS Shortcut for direct Finder integration.

Right-click files, pick a Quick Action, and - bam - no terminal required.

### To add the Shortcut

1. Open the **Shortcuts** app.
2. Choose `File -> Import`.
   ![Shortcuts App Menu](docs/Screenshot%202025-04-25%20at%2005.50.57.png)
3. Select the Shortcut in `macOS/Strip Unicode.shortcut`.
   ![Import Shortcut](docs/Screenshot%202025-04-25%20at%2005.51.54.png)
4. Edit it to point to your local `cleanup-text.py`.
   ![Edit Shortcut Script Path](docs/Screenshot%202025-04-25%20at%2005.07.47.png)
5. Relaunch Finder (`Cmd+Opt+Esc` → select Finder → Relaunch) if needed.
6. After setup, right-click files, choose `Quick Actions`, select `Strip Unicode`.
   ![Select Shortcut File](docs/Screenshot%202025-04-25%20at%2005.47.51.png)

---

## What's in This Repository

- [bin/cleanup-text.py](bin/cleanup-text.py) - Main cleaning script
- [bin/cleanup-text](bin/cleanup-text) - Symlink for CLI usage
- [setup.sh](setup.sh) - Easy setup and env configuration
- [requirements.txt](requirements.txt) - Python dependencies
- [macOS/](macOS/) - Shortcuts, scripts for Finder
- [data/](data/) - Example test files
- [tests/](tests/) - Automated test suite for all features/edge cases
- [docs/](docs/) - Documentation and screenshots
- [LICENSE](LICENSE)
- [README.md](README.md) - This file

---

## Testing and CI/CD

UnicodeFix comes with a full, automated test suite:

- Drives every scenario against the canonical file list in `data/`
- Writes diffs and normalized word-count summaries into `test_output/<scenario>/`
- Run it with: `tests/test_all.sh`
- Clean up with: `tests/test_all.sh clean`
- STDIN/STDOUT coverage skips the binary fixtures (everything else still runs on them)
- Plug into your CI/CD pipeline or just use it as a "paranoia check" before shipping anything

**Pro tip:** Run the tests before you merge, publish, or email a "final" version.

See [docs/test-suite.md](docs/test-suite.md) for the deep dive.

---

## Contributing

Feedback, bug reports, and patches welcome.

If you've got a better integration path for your favorite platform, let's make it happen.
Pull requests with attitude, creativity, and clean diffs appreciated.

---

## Support This and Other Projects

If UnicodeFix (or my other projects) saved your bacon or made you smile, please consider fueling my caffeine habit and indie dev obsession...

- [Patreon](https://patreon.com/unixwzrd)
- [Ko-Fi](https://ko-fi.com/unixwzrd)
- [Buy Me a Coffee](https://buymeacoffee.com/unixwzrd)

Quite a bit of effort goes into preparing these releases. *One coffee = one more tool released to the wild...*🤔

Thank you for keeping solo development alive!

---

## Changelog

**See [CHANGELOG.md](CHANGELOG.md) for the latest drop.**

---

## License

Copyright 2025
[unixwzrd@unixwzrd.ai](mailto:unixwzrd@unixwzrd.ai)

[MIT License](LICENSE)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
