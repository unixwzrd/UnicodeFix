# UnicodeFix — *Ghostmark Edition v2.0.0* — it finds what your editor does not show.

*Last updated: 2026-08-20*

![UnicodeFix — Filtering AI Artifacts](docs/unicodefix-banner-titled.png)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#installation) [![Platforms](https://img.shields.io/badge/Platforms-macOS%20%7C%20Ubuntu-informational)](#installation) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Release](https://img.shields.io/github/v/tag/unixwzrd/UnicodeFix?label=release)](https://github.com/unixwzrd/UnicodeFix/releases) [![CI](https://github.com/unixwzrd/UnicodeFix/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)

Invisible characters. Provenance wrappers. Configured statistical watermarks. Hard-wrapped Markdown. Source comments carrying hidden payloads. UnicodeFix audits the evidence, shows exactly where it lives, previews the cleanup, and removes only what it can identify safely.

Everything runs locally after installation. Your text is not uploaded to a detector, vendor, or model service.

- [Meet Ghostmark](#meet-ghostmark)
- [Why now?](#why-now)
- [What UnicodeFix can find](#what-unicodefix-can-find)
- [Three practical modes](#three-practical-modes)
- [Installation](#installation)
- [Quick use](#quick-use)
- [What a finding means](#what-a-finding-means)
- [Privacy, provenance, and proof](#privacy-provenance-and-proof)
- [Markdown and source safety](#markdown-and-source-safety)
- [Shortcut for macOS](#shortcut-for-macos)
- [Local watermark and authorship profiles](#local-watermark-and-authorship-profiles)
- [Brief examples](#brief-examples)
- [What's in this repository](#whats-in-this-repository)
- [Testing and CI/CD](#testing-and-cicd)
- [Contributing](#contributing)
- [Support this and other projects](#support-this-and-other-projects)
- [Changelog](#changelog)
- [License](#license)

---

## Meet Ghostmark

The **Ghostmark Edition** is UnicodeFix's evidence-based 2.0 release. The name fits the job: find the marks that can hide in plain sight, distinguish recognized carriers from ordinary typography, and give the person holding the file control over what happens next.

This is still the direct, practical cleaner from the Wolf Edition—but 2.0 is much more careful about what the evidence can prove. A curly quote is typography, column-80 wrapping is formatting, C2PA is provenance, and a statistical detector applies only to the exact scheme and configuration it knows. None of those facts, by itself, identifies the human who wrote a document.

No generic “AI detector” theater. No mystery probability presented as truth. No claim that every em dash came from a chatbot.

## Why now?

Text watermarking is no longer only an academic proposal. [Anthropic says supported Claude models launched in the European Union on or after August 2, 2026 include model-level machine-readable text marking](https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content), that the marks may survive copy-and-paste and some edits, and that compatible detection tooling is still forthcoming. That makes visibility and user control an immediate concern, but it does **not** establish that Anthropic is embedding a personal tracking identifier or that its unpublished detector can currently be reproduced locally.

The privacy question is legitimate even when the most alarming claim is unproven. A durable hidden carrier, unique identifier, external manifest reference, or vendor-controlled detector could potentially be correlated with other records. UnicodeFix therefore treats privacy as a threat model to inspect—not a conclusion to manufacture.

The engineering rule is simple: report what is observable, attach the scheme and confidence when known, preserve exact locations, and say `unsupported` when the required public algorithm, key, tokenizer, model, or calibration is unavailable.

## What UnicodeFix can find

| Category | What it means | Cleanup policy |
| --- | --- | --- |
| `provenance` | A recognized local C2PA text carrier or structured manifest element. C2PA records provenance; it does not prove AI authorship. | Preserved unless `--strip-provenance` is explicit. |
| `unicode_security` | Bidi controls, default-ignorables, variation selectors, tag characters, private-use characters, noncharacters, replacement characters, normalization differences, mixed scripts, or confusable signals. | Exact safe transforms only; UTS #39 confusable skeletons are detection-only. |
| `known_watermark` | The result of a named local statistical-watermark profile using its required configuration and artifacts. | Reported by profile. No generic unknown-watermark rewrite. |
| `authorship_signal` | A paragraph crossed a named, locally calibrated model-distribution threshold. | Report-only probabilistic evidence, never an automatic cleanup trigger. |
| `typography` | Smart quotes, dashes, unusual whitespace, and other observable text-normalization candidates. | Selected characters can be normalized, with preservation switches available. |
| `formatting` | Markdown soft breaks, wrapped list continuations, and probable fixed-column wrapping. | Reported as formatting; unwrapping is opt-in. |

Detailed reports retain the category, signal, count, confidence, removability, planned action, and exact line, column, code point, and source context when available. Compact aggregate counts remain available for humans and CI.

## Three practical modes

### Audit it

`--report` inventories the file without changing it. Add `--metrics` for deterministic document facts such as bytes, characters, lines, words, newline style, ASCII/non-ASCII counts, and a non-ASCII code-point inventory.

```bash
cleanup-text --report --metrics document.md
cleanup-text --report --metrics --json document.md
```

### Preview it

`--dry-run` executes the exact requested cleanup pipeline in memory without writing. Add `--diff` to see the proposed change.

```bash
cleanup-text --dry-run --diff --unwrap-markdown document.md
```

### Clean it

The default cleaner normalizes selected typographic characters and whitespace, removes supported risky invisible characters, and preserves the input newline style when writing a file. Recognized provenance stripping and Markdown reformatting remain explicit choices.

```bash
cleanup-text document.txt
cleanup-text --unwrap-markdown README.md
cleanup-text --strip-provenance document.md
cleanup-text --source app.py
```

With no input file, UnicodeFix is a stdin-to-stdout filter. With input files, it writes `<name>.clean<extension>` unless `--output`, `--temp`, or stdout output is selected.

## Installation

Python 3.10 or newer is required.

```bash
git clone https://github.com/unixwzrd/UnicodeFix.git
cd UnicodeFix
./setup.sh
```

`setup.sh` uses [pyproject.toml](pyproject.toml) as the dependency source of truth. It reuses an active Conda or virtual environment, or creates a local `.venv` when needed. It also installs the repository's pre-push check by default; use `--no-hooks` when you do not want the hook.

```bash
./setup.sh --dev                    # Editable install and development tools
./setup.sh --watermark-lab          # Optional local KGW/SynthID and authorship tooling
./setup.sh --dev --watermark-lab    # Both optional groups
./setup.sh --no-hooks               # Install without the local pre-push hook
```

The optional lab does not fetch model artifacts at runtime. Profiles must point to matching artifacts already available locally. UnicodeFix is currently distributed through GitHub releases rather than PyPI.

For serious environment nerds, [VenvUtil](https://github.com/unixwzrd/venvutil) is my full-featured Python environment toolkit.

## Quick use

```bash
# Audit only; no file is written.
cleanup-text --report document.md

# Inventory deterministic metrics and exact findings as JSON.
cleanup-text --report --metrics --json document.md

# Preview the requested transformation and show a unified diff.
cleanup-text --dry-run --diff --unwrap-markdown document.md

# Create document.clean.md.
cleanup-text document.md

# Clean supported hidden payloads in source comments without rewriting strings or identifiers.
cleanup-text --source app.py

# Explicitly remove complete, recognized local C2PA carriers.
cleanup-text --strip-provenance document.md
```

Category-aware thresholds let CI fail on the findings that matter without treating informational typography or wrapping as a security failure.

```bash
cleanup-text --report --threshold 1 --threshold-category unicode_security source.py
cleanup-text --report --threshold 1 --threshold-category provenance --exit-zero README.md
```

`--threshold N` exits with status 1 when the selected finding count is at least `N`. Repeat `--threshold-category` to select more than one category. `--exit-zero` keeps the report informational.

## What a finding means

UnicodeFix deliberately separates inspection from attribution:

- **Detected Unicode is exact:** the named character or carrier exists at the reported location.
- **Detected C2PA is provenance:** it can identify a signed claim or reference, not automatically the author, model, or truth of the content.
- **A named watermark result is profile-specific:** `not_detected` means only that the named detector and configuration did not cross its threshold.
- **An authorship signal is probabilistic:** it reports how a paragraph behaves under a pinned reference model and calibration corpus, not who wrote it.
- **Typography is not authorship:** smart quotes, em dashes, ellipses, and unusual spacing have many ordinary sources.
- **Wrapping is formatting:** column 72, 78, 79, or 80 may reflect an editor, formatter, project convention, email client, or generator.

Configured statistical detectors return `detected`, `not_detected`, `insufficient_text`, `unsupported`, or `configuration_error`. “Not detected” always applies to the named detector profile, never to every possible watermark.

## Privacy, provenance, and proof

A watermark may be a harmless aggregate signal, a signed provenance record, a scheme-specific statistical pattern, or a hidden payload. Those designs have very different privacy properties. The mere presence of a mark does not prove that it contains a user identity, but users should be able to see what is embedded in material they possess and decide whether to retain a removable carrier.

[C2PA](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html) is designed for content provenance and authenticity, includes privacy and creator control among its design principles, and does not itself make a value judgment about whether content is “good,” “bad,” human, or AI. UnicodeFix recognizes C2PA before generic invisible cleanup so a valid credential is not silently destroyed.

UnicodeFix never retrieves external manifest URLs during normal operation. Complete recognized local carriers are removed only with `--strip-provenance`; malformed carriers are retained and reported. The tool also refuses to reformat signed C2PA content unless stripping was explicitly requested, because even a harmless Markdown reserialization can invalidate a credential.

For Anthropic specifically, the public documentation establishes automatic model-level output marking for supported models. It does not currently provide enough compatible public mechanics to reproduce the detector locally, so UnicodeFix records that status as `not_publicly_detectable` rather than guessing KGW, SynthID, Unicode, or a user identifier.

## Markdown and source safety

`--unwrap-markdown` joins CommonMark soft line breaks within the same paragraph, including paragraphs inside ordered, unordered, task, nested, and blockquoted list items. It preserves the marker for every real list item and does not merge sibling items, nested items, a paragraph with a following list, or separate blockquotes.

It also preserves explicit hard breaks, blank lines in loose lists, multiple paragraphs within one item, headings, thematic breaks, tables, front matter, link definitions, HTML, fenced and indented code, inline code, URLs, and setext headings. The operation is opt-in and idempotent: a second pass makes no further change.

`--source` classifies suspicious material inside comments, strings, identifiers, and syntax. It can clean recognized provenance and supported hidden payloads from comments, but strings and identifiers remain byte-for-byte unchanged. Parsing is checked before and after cleanup. UnicodeFix does not rename identifiers, insert dead code, or attempt generic AST watermark disruption.

`--source` and `--unwrap-markdown` are separate profiles and cannot be combined.

## Shortcut for macOS

UnicodeFix ships with a macOS Shortcut for direct Finder integration. Right-click one or more files, choose **Quick Actions → Strip Unicode**, and the selected files are cleaned without ordinary Terminal interaction.

### To add the Shortcut

1. Install UnicodeFix and locate its executable:

   ```bash
   command -v cleanup-text
   ```

2. Open the macOS **Shortcuts** app and choose **File → Import**.

   ![Shortcuts app File menu with Import Shortcut selected](docs/Screenshot%202025-04-25%20at%2005.50.57.png)

3. Import [macOS/Strip Unicode.shortcut](macOS/Strip%20Unicode.shortcut).

   ![Importing the bundled Strip Unicode shortcut](docs/Screenshot%202025-04-25%20at%2005.51.54.png)

4. Edit the Shortcut's **Run Shell Script** action. Replace the example path with the full path returned by `command -v cleanup-text`. Keep the selected Finder files passed as arguments.

   ![Editing the cleanup-text executable path in the Shortcut](docs/Screenshot%202025-04-25%20at%2005.07.47.png)

5. If the Quick Action does not appear immediately, relaunch Finder with **Command–Option–Escape**, select **Finder**, and choose **Relaunch**.

6. In Finder, select the files to clean, right-click, and choose **Quick Actions → Strip Unicode**.

   ![Selecting Strip Unicode from Finder Quick Actions](docs/Screenshot%202025-04-25%20at%2005.47.51.png)

The bundled Shortcut contains an example machine-specific executable path, so step 4 is required. If UnicodeFix is installed in a virtual environment, keep that environment in a stable location so the Shortcut's executable path remains valid after upgrades.

## Local watermark and authorship profiles

`--watermark-profile PATH` runs a named offline detector profile and implies report mode. The optional local adapters support explicit KGW and SynthID Text configurations. They require the matching tokenizer, model or detector artifacts, scheme parameters, key or seed where required, and a calibrated threshold.

```bash
cleanup-text --report --watermark-profile research/watermarks/profiles/example-kgw.toml text.txt
```

`--authorship-profile PATH` scores each sufficiently long paragraph with pinned local causal-model artifacts. It can report negative log likelihood, perplexity, selected-token rank, and top-10 rate under that reference model. A profile must include calibration coefficients fitted on a matched held-out corpus before UnicodeFix displays an estimated probability.

```bash
cleanup-text --report --json --authorship-profile research/watermarks/profiles/example-authorship.toml text.txt
```

A small local GGUF or llama.cpp-compatible model is a plausible future backend for these model-distribution measurements, but model size does not turn the result into proof. The reference model, tokenizer, quantization, corpus, text length, domain, language, and calibration all affect the distribution. This release's research review did not locate a documented Apple Intelligence interface that exposes the general-purpose token log probabilities required by this detector, so Apple Intelligence is not a UnicodeFix backend in 2.0.0.

UnicodeFix uses local-only artifact loading and never contacts a vendor service or model hub. It cannot generically find or remove unknown, proprietary, lexical, semantic, or source-code watermarks. A statistical watermark intentionally introduced during token sampling can often be weakened by editing, but UnicodeFix will not damage prose blindly in an attempt to erase an unknown scheme.

See the [vendor watermark matrix](docs/research/vendor-watermark-matrix.md), [feasibility ledger](docs/research/feasibility-ledger.md), and [local research harness](research/watermarks/README.md) for the dated evidence, deployment distinctions, public detector status, and experiment design. The ledger covers token probability partitioning, KGW green-list bias, SynthID Text tournament sampling, downstream trajectory effects, and the separate DetectGPT, Fast-DetectGPT, and Binoculars authorship-detection family.

## Brief examples

### Pipe or filter

```bash
cleanup-text < file.txt > cleaned.txt
```

### Batch clean

```bash
cleanup-text *.txt
```

### In-place clean

```bash
cleanup-text -t myfile.txt
```

### Preserve the temporary file as a backup

```bash
cleanup-text -t -p myfile.txt
```

In-place cleaning writes and syncs a unique same-directory temporary file, preserves the original permissions, and then atomically replaces the original with a new modification timestamp. `--preserve-tmp` copies the untouched original to `myfile.txt.tmp`, or the first unused numbered name such as `myfile.txt.tmp.1`; an existing backup is never overwritten.

### Audit without blocking a commit

```bash
cleanup-text --report --metrics --exit-zero foo.txt
```

### Audit stdin as JSON with a useful label

```bash
git show HEAD:README.md | cleanup-text --report --json --label README-at-HEAD -
```

### Use it in vi, Vim, or MacVim

```vim
:%!cleanup-text
```

Use it from Vim, an editor task, a pre-commit hook, Finder, a shell pipeline, or a CI job. For material where invisible characters or typographic punctuation are intentional, audit first and use the relevant preservation options. Run `cleanup-text --help` for the current switch list and see [the full CLI guide](docs/cleanup-text.md) for the deeper details.

## What's in this repository

- [src/unicodefix/cli.py](src/unicodefix/cli.py) — CLI entry point and cleanup orchestration.
- [src/unicodefix/scanner.py](src/unicodefix/scanner.py) — Unicode and findings inventory.
- [src/unicodefix/transforms.py](src/unicodefix/transforms.py) — safe text transformations.
- [src/unicodefix/c2pa.py](src/unicodefix/c2pa.py) — local C2PA carrier recognition and explicit stripping.
- [src/unicodefix/markdown.py](src/unicodefix/markdown.py) — Markdown wrapping audit and opt-in unwrapping.
- [src/unicodefix/source.py](src/unicodefix/source.py) — conservative source-context classification and comment cleanup.
- [src/unicodefix/watermarks.py](src/unicodefix/watermarks.py) — profile-driven local watermark adapters.
- [src/unicodefix/authorship.py](src/unicodefix/authorship.py) — optional locally calibrated model-distribution signals.
- [research/watermarks/](research/watermarks/) — reproducible offline research harness and example profiles.
- [data/](data/) — example and integration fixtures.
- [tests/](tests/) — automated feature and regression tests.
- [docs/](docs/) — CLI, API, research, test documentation, and macOS screenshots.
- [macOS/Strip Unicode.shortcut](macOS/Strip%20Unicode.shortcut) — Finder Quick Action integration.
- [scripts/run_checks.sh](scripts/run_checks.sh) — local release and pre-push checks.
- [setup.sh](setup.sh) — unified bootstrap and install script.

## Testing and CI/CD

Run the same local gate installed by the pre-push hook:

```bash
scripts/run_checks.sh
```

The local gate runs Black, Ruff, and pytest. CI also runs the shell integration suite across supported Python releases on macOS and Ubuntu without vendor APIs, accounts, downloads, or network access. Public watermark fixtures and profiles remain vendor-independent and deterministic.

For the integration harness alone:

```bash
tests/test_all.sh
tests/test_all.sh clean
```

See [docs/test-suite.md](docs/test-suite.md) for the complete test layout and acceptance checks.

## Contributing

Feedback, bug reports, detector research, fixtures, and patches are welcome. A useful watermark contribution needs more than a rumor: include the primary source, access date, exact algorithm or carrier, required configuration, a matched watermarked/unwatermarked corpus, and false-positive/false-negative evidence.

If a vendor's production deployment is not public, describe the implementation as research or compatible tooling rather than evidence that every output from that vendor carries the scheme. Pull requests with attitude, reproducible evidence, and clean diffs are especially appreciated.

## Support this and other projects

If UnicodeFix or one of my other projects saved your bacon, please consider fueling the caffeine habit and indie development work:

- [Patreon](https://patreon.com/unixwzrd)
- [Ko-Fi](https://ko-fi.com/unixwzrd)
- [Buy Me a Coffee](https://buymeacoffee.com/unixwzrd)

Quite a bit of effort goes into researching, implementing, testing, and preparing these releases. One coffee means one more tool gets released into the wild.

Thank you for keeping solo development alive.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the complete release history and the Ghostmark Edition changes.

## License

Copyright © 2025-2026 Distributed Thinking Systems LLC

[MIT License](LICENSE)
