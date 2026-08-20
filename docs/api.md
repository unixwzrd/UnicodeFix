# UnicodeFix Python API

UnicodeFix 2.0 exposes focused local primitives. Results describe observable data; they do not assign AI authorship. Python 3.10 or newer is required.

## Core cleaning

```python
from unicodefix.transforms import clean_text, handle_newlines

cleaned = clean_text(
    '“Example”\u200b',
    preserve_invisible=False,
    preserve_quotes=False,
    preserve_dashes=False,
    preserve_fullwidth_brackets=False,
    preserve_default_ignorables=False,
    strip_provenance=False,
)
cleaned = handle_newlines(cleaned)
```

`clean_text()` repairs common text encoding issues, normalizes selected quotes, dashes, spaces, and brackets, and removes replacement, unassigned, private-use, and default-ignorable characters unless a preservation option applies. Complete recognized C2PA carriers are protected from generic cleanup by default; set `strip_provenance=True` only to remove them intentionally. `handle_newlines(text, no_newline=False)` ensures a final newline.

`fold_for_terminal_display(text)` folds fullwidth square brackets to ASCII and is useful for terminal presentation without applying the full cleaner.

## Findings and deterministic metrics

```python
from unicodefix.metrics import compute_metrics
from unicodefix.scanner import scan_text_for_report

report = scan_text_for_report(text)
metrics = compute_metrics(text)
```

`scan_text_for_report()` returns the versioned findings envelope used by CLI output. Its `schema_version` is `2.0`; each finding has a category, signal, count, one-based locations, confidence, removability, planned action, and optional scheme/vendor details. Categories are `provenance`, `unicode_security`, `known_watermark`, `authorship_signal`, `typography`, and `formatting`.

Unicode security scanning uses a packaged Unicode 17 database and pinned confusable table. Mixed-script confusable tokens include a detection-only skeleton and exact locations; UnicodeFix never uses that skeleton as replacement text.

`compute_metrics()` returns deterministic `bytes_utf8`, `characters`, `lines`, `words`, `newline_style`, ASCII/non-ASCII totals, and a non-ASCII code-point inventory. It does not expose AI-likeness, entropy, repetition, burstiness, type-token ratio, stop-word analysis, or a probability score.

## C2PA provenance carriers

```python
from unicodefix.c2pa import find_c2pa_carriers, strip_c2pa_carriers

carriers = find_c2pa_carriers(text)
cleaned = strip_c2pa_carriers(text)
```

`find_c2pa_carriers()` recognizes local variation-selector and structured C2PA text wrappers plus inline and external-reference HTML carriers, returning their span, kind, structural validity, payload, and message. It does not verify signatures or dereference URLs. `strip_c2pa_carriers()` removes only complete recognized carriers and leaves malformed data untouched. Treat C2PA as provenance, not AI-generation proof.

`encode_variation_selectors(payload)` and `decode_variation_selectors(text, start=0)` are fixture and forensic helpers for the standard byte mapping.

## Markdown and source operations

```python
from unicodefix.markdown import audit_markdown, unwrap_markdown
from unicodefix.source import clean_source_comments, scan_source

markdown_inventory = audit_markdown(markdown_text)
unwrapped = unwrap_markdown(markdown_text)
source_inventory = scan_source(source_text, path='module.py')
cleaned_source = clean_source_comments(source_text, path='module.py', strip_provenance=False)
```

`audit_markdown()` reports soft-break candidates, list continuations, hard breaks, and probable wrap widths. `unwrap_markdown()` safely joins soft paragraph breaks without merging Markdown elements; callers that reformat C2PA-bearing content should first decide explicitly whether to retain or remove provenance.

`scan_source()` classifies findings by source context and returns language/parser/parse-valid information. `clean_source_comments()` only removes eligible payloads in comments and preserves identifiers and string content. It returns the original source if parse validation cannot establish a safe transformation.

## Local watermark profiles

```python
from unicodefix.watermarks import detect_profiles, detect_with_profile

result = detect_with_profile(text, 'profiles/local-kgw.toml').to_dict()
results = detect_profiles(text, ['profiles/local-kgw.toml'])
```

Profile results have `detected`, `not_detected`, `insufficient_text`, `unsupported`, or `configuration_error` status. A result names the profile path, scheme, score/threshold when available, and a configuration fingerprint. Never interpret `not_detected` as a generic absence claim.

The `literal_fixture` adapter supports deterministic tests. `kgw` and `synthid_text` require the optional lab dependency, exact matching local model/tokenizer or detector artifacts, configuration, and calibrated threshold. All artifact loads are local-only; no vendor service is contacted.

## Local authorship-signal profiles

```python
from unicodefix.authorship import detect_authorship_profiles, detect_authorship_with_profile

result = detect_authorship_with_profile(text, 'profiles/local-authorship.toml').to_dict()
results = detect_authorship_profiles(text, ['profiles/local-authorship.toml'])
```

These profiles score sufficiently long paragraphs against pinned, local causal-language-model artifacts. Available metrics are `mean_nll`, `perplexity`, `mean_rank`, and `top_10_fraction`. Results are `potentially_ai_generated`, `not_flagged`, `insufficient_text`, `unsupported`, or `configuration_error`; the first status means only that a paragraph crossed this profile's threshold. An `estimated_ai_probability` is absent unless the profile supplies logistic calibration coefficients derived from an appropriate held-out corpus. The API never rewrites a paragraph based on an authorship signal.

## Rendering reports

```python
from unicodefix.report import print_csv, print_human, print_json

print_human('example.txt', report)
print_json({'example.txt': report})
print_csv({'example.txt': report})
```

Use the shared renderers rather than reconstructing legacy scanner dictionaries. Human output presents exact findings, JSON retains the detailed schema, and CSV exports aggregate category and scalar metric fields.
