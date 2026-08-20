# UnicodeFix test suite

Run validation from the repository root.

```bash
pytest -q
black --check src tests research
ruff check src tests research
scripts/run_checks.sh
```

`tests/test_all.sh` remains the shell integration harness for representative data fixtures. It produces test output and diffs for manual inspection; use `tests/test_all.sh clean` to remove its generated output.

## 2.0 coverage

The unit suite covers the versioned finding model, deterministic metrics, Unicode/default-ignorable and bidi signals, C2PA variation-selector and structured carriers, explicit provenance stripping, Markdown soft-break unwrapping, source context safety, watermark-profile outcomes, paragraph-level authorship-profile outcomes, CLI report formats, dry-run behavior, and category-aware threshold exit codes.

Markdown cases must prove that soft breaks join within ordinary paragraphs, ordered/unordered/task/nested list items, and blockquotes without merging separate elements. They must preserve hard breaks, loose-list blank lines, tables, front matter, raw HTML, link definitions, and fenced/indented code. A second Markdown pass must not change output.

Source cases must show that comment cleanup can remove supported carriers while strings and identifiers remain unchanged. For supported languages, cleanup must not turn a parse-valid input into invalid source.

Dry-run cases must confirm no file write occurs and that the predicted cleanup equals a subsequent actual cleanup. Human, JSON, and CSV reports must use the same findings source, although CSV intentionally contains aggregate values.

## Local watermark experiments

CI must never need a vendor API, account, network service, or model download. Profile fixtures use deterministic local content and assert all five outcomes: `detected`, `not_detected`, `insufficient_text`, `unsupported`, and `configuration_error`.

Optional KGW, SynthID Text, or TextSeal research belongs in a local lab environment with cached artifacts and matched watermarked/control corpora. Before accepting an adapter, measure false positives and false negatives by length, verify incorrect configuration failure, and test edits, Unicode cleanup, Markdown reformatting, mixed documents, URLs, numbers, citations, and source parsing. A passing detector test does not establish vendor-product compatibility.

Authorship-signal evaluation additionally requires held-out human and generated samples matched by source, language, domain, paragraph length, and preprocessing. Record the exact reference model and tokenizer, generator and decoding settings, calibration split, threshold, false-positive and false-negative rates, and post-edit behavior. Tests must verify that no probability is emitted without explicit calibration coefficients.

## CI gates

Use category thresholds to make policy explicit. For example, gate `unicode_security` or `provenance` findings while retaining typography and formatting observations as informational data.

```bash
cleanup-text --report --threshold 1 --threshold-category unicode_security path/to/file
cleanup-text --report --threshold 1 --threshold-category provenance path/to/file
```

`--exit-zero` makes a report informational when a pipeline should record, rather than block on, findings.
