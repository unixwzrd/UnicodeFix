# `cleanup-text` CLI

`cleanup-text` audits and safely cleans observable Unicode, provenance, formatting artifacts, and image metadata. It operates locally, recognizes common image signatures before decoding, reads text files as strict UTF-8, and never treats a formatting pattern or negative detector result as an AI-authorship determination.

## Invocation

```text
cleanup-text [options] [infile ...]
```

No input files selects stdin-to-stdout filter mode. Named files produce `<base>.clean<extension>` by default. Use `--output FILE` with one input, `--output -` for stdout, or `--temp` for an atomic in-place replacement; add `--preserve-tmp` to copy the untouched original to the first unused `.tmp` or numbered `.tmp.N` backup name.

## Automatic image cleanup

PNG, JPEG, GIF, TIFF, BMP, WebP, HEIF, and AVIF signatures route to the existing image backend instead of UTF-8 decoding. Plain `cleanup-text image.png` selects non-rendering metadata cleanup and writes `image.clean.png`; `--strip-provenance` also selects recognized C2PA/JUMBF removal. Lossless writing requires ExifTool 12.70+ and a supported writable format (JPEG, PNG, WebP, TIFF, HEIF, or AVIF). Pixels, ICC profiles, orientation, and color-space tags are preserved. Recognized C2PA content requires explicit `--strip-provenance` before metadata cleanup.

```bash
cleanup-text image.png
cleanup-text notes.txt image.png
cleanup-text --report --metrics --json notes.txt image.png
cleanup-text --dry-run image.png
cleanup-text --strip-provenance --force -o public.png image.png
```

`--report` never writes; `--dry-run` reports planned image cleanup and fails if the backend cannot perform it. `--metrics` follows the existing text convention: audit by default, or a side report on stderr with an explicit output. JSON and CSV reports can contain both text and images, including image dimensions and metadata counts. Use `--threshold-category metadata` to select image metadata findings.

Images require separate file output; `--temp`, `--preserve-tmp`, and `--output -` are rejected. Text-only transforms, preservation switches, `--diff`, and text detector profiles are also rejected for image inputs. `--force` permits replacing existing image output; it does not change text overwrite behavior. [The image guide](cleanup-image.md) describes the backend and provenance protections. `cleanup-image` remains available, with audit-only behavior when called without cleanup flags.

## Cleaning options

| Option | Effect |
| --- | --- |
| `-i`, `--invisible` | Preserve the legacy invisible-character set. |
| `--preserve-default-ignorables` | Preserve all Unicode Default_Ignorable_Code_Point characters. This includes variation selectors and tag characters; recognized C2PA is preserved by default regardless. |
| `-Q`, `--keep-smart-quotes` | Preserve typographic quotes. |
| `-D`, `--keep-dashes` | Preserve Unicode dash and hyphen variants. |
| `--keep-fullwidth-brackets` | Preserve `【】` rather than folding to `[]`. |
| `-n`, `--no-newline` | Do not ensure a final newline. |
| `--strip-provenance` | Remove complete, recognized local C2PA carriers. No URL is fetched; malformed carriers remain for review. |
| `--unwrap-markdown` | Safely join Markdown soft breaks and format supported Markdown blocks. |
| `--source` | Use conservative source-code cleanup. This cannot be combined with `--unwrap-markdown`. |
| `--force` | Permit replacing an existing image output file. |

`--strip-provenance` is intentional and explicit because C2PA credentials may be valuable provenance. UnicodeFix reports C2PA separately from AI generation and does not validate a signature or retrieve an external manifest.

## Reporting and preview

| Option | Effect |
| --- | --- |
| `--report` | Audit only; never write input or output files. |
| `--metrics` | Add deterministic document metrics and imply report mode when no output option is supplied. |
| `--metrics-help` | Explain deterministic metrics. |
| `--dry-run` | Run the requested cleanup in memory and report planned before/after changes. It cannot be combined with `--output` or `--temp`. |
| `--diff` | Show a unified diff for a dry run. It requires `--dry-run` and cannot be combined with JSON or CSV. |
| `--json`, `--csv` | Select structured report output. |
| `--label NAME` | Report stdin under `NAME`. |
| `--threshold N` | Exit 1 when the selected finding count is at least `N`. |
| `--threshold-category CATEGORY` | Restrict a threshold to a category; repeat for multiple categories. |
| `--watermark-profile PATH` | Run an explicit local statistical-watermark profile; repeat for multiple profiles. |
| `--authorship-profile PATH` | Score paragraphs with an explicit local causal-model likelihood profile; repeatable and never treated as proof. |
| `--exit-zero` | Force status 0 after reporting, including a threshold hit. |
| `--no-color` | Disable ANSI color in human reports. |
| `-q`, `--quiet` | Suppress status lines written to stderr. |

Text categories are `provenance`, `unicode_security`, `known_watermark`, `authorship_signal`, `typography`, and `formatting`; images also use `metadata`. Human, JSON, and CSV reports use the same versioned findings model with signal, count, location, confidence, removability, and planned action. JSON keeps the detailed locations; CSV is intentionally aggregate-oriented.

```bash
# Preview every requested change without writing.
cleanup-text --dry-run --diff --strip-provenance --unwrap-markdown paper.md

# Gate CI only on security-relevant observable findings.
cleanup-text --report --threshold 1 --threshold-category unicode_security src/module.py

# Retain a machine-readable audit without failing an informational hook.
cleanup-text --report --metrics --json --exit-zero README.md
```

## Markdown behavior

Markdown unwrapping joins CommonMark soft line breaks inside a single paragraph. This includes ordinary prose and continuation lines within ordered lists, unordered lists, task lists, nested items, blockquotes, and combinations of these containers. The original list marker remains attached to its item.

It will not merge sibling list items, separate paragraphs, headings, thematic breaks, link definitions, tables, raw HTML, fenced or indented code, or distinct blockquotes. It preserves hard breaks created with two trailing spaces or a backslash, blank lines that make a list loose or introduce another paragraph, and inline code. Fixed-width wrapping at 72, 78, 79, 80, or another width is an informational formatting observation, not provenance or a watermark.

A valid C2PA carrier blocks Markdown reformatting unless `--strip-provenance` is supplied. This avoids silently invalidating signed content through reserialization.

## Source behavior

Source mode is deliberately narrower than document cleanup. It inventories suspicious text by comment, string, identifier, and syntax context; it removes recognized C2PA/hidden payloads only from comments; and it checks that a previously valid source file remains parseable. It reports potentially confusing identifiers and strings without renaming or rewriting them. Source semantics and language-specific code-watermark disruption are outside its scope.

## Statistical-watermark profiles

Profiles run locally and must name a scheme plus every detector prerequisite. The built-in profile adapters currently recognize `literal_fixture`, `kgw`, and `synthid_text`; KGW and SynthID need the optional `unicodefix[watermark-lab]` installation and matching cached local artifacts. Model/tokenizer loads use local-only mode.

`not_detected` applies only to the named profile, detector configuration, and input. It is not a statement that the document contains no watermark. Unknown and proprietary schemes are not generically detectable or removable. Keep profile keys out of source control; reports output a configuration fingerprint rather than secret material.

## Examples

```bash
# Default file cleanup.
cleanup-text notes.txt

# Filter mode.
printf 'hello\u200b\n' | cleanup-text

# In-place cleanup with recoverable temporary copy.
cleanup-text --temp --preserve-tmp notes.txt

# Audit a local fixture detector.
cleanup-text --report --watermark-profile profiles/fixture.toml sample.txt
```

In-place writes use a unique temporary file in the input file's directory, sync its contents, preserve the original permissions, and then use an atomic replacement with a new modification timestamp. Without `--preserve-tmp`, the internal temporary file is removed by the replacement. With it, an existing backup is never overwritten.

Run a locally calibrated paragraph-level authorship profile:

```bash
cleanup-text --report --json --authorship-profile profiles/local-authorship.toml sample.txt
```

An authorship profile pins an already-downloaded causal model and tokenizer, metric, comparison, minimum paragraph length, and threshold. Optional logistic calibration coefficients may be supplied only when fitted on a held-out corpus matched to the expected language and domain. Without those coefficients, UnicodeFix shows scores and threshold crossings but no estimated probability. These findings are never cleanup actions.
