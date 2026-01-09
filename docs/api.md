# UnicodeFix Python API Documentation

*Last updated: 2026-01-08*

This document describes the Python API provided by UnicodeFix for programmatic text cleaning, scanning, and reporting.

## Table of Contents

- [UnicodeFix Python API Documentation](#unicodefix-python-api-documentation)
  - [Table of Contents](#table-of-contents)
  - [Core Text Cleaning](#core-text-cleaning)
    - [`clean_text()`](#clean_text)
    - [`handle_newlines()`](#handle_newlines)
    - [`fold_for_terminal_display()`](#fold_for_terminal_display)
  - [Text Scanning \& Analysis](#text-scanning--analysis)
    - [`scan_text_for_report()`](#scan_text_for_report)
  - [Report Generation](#report-generation)
    - [`print_human()`](#print_human)
    - [`print_json()`](#print_json)
    - [`print_csv()`](#print_csv)
    - [`print_metrics_help()`](#print_metrics_help)
  - [Semantic Metrics (Experimental)](#semantic-metrics-experimental)
    - [`compute_metrics()`](#compute_metrics)
  - [Complete Example: Programmatic Cleaning Pipeline](#complete-example-programmatic-cleaning-pipeline)
  - [Error Handling](#error-handling)
  - [Type Hints](#type-hints)
  - [See Also](#see-also)

---

## Core Text Cleaning

### `clean_text()`

The primary function for normalizing problematic Unicode characters to safe ASCII equivalents.

**Location:** `unicodefix.transforms.clean_text`

**Signature:**

```python
def clean_text(
    text: str,
    preserve_invisible: bool = False,
    preserve_quotes: bool = False,
    preserve_dashes: bool = False,
    preserve_fullwidth_brackets: bool = False,
    preserve_replacement_chars: bool = False,
) -> str
```

**Parameters:**

- `text` (str, required): Input text to clean
- `preserve_invisible` (bool, default: `False`): If `True`, preserves zero-width spaces, non-breaking spaces, bidirectional marks, and other invisible Unicode characters. If `False` (default), removes them.
- `preserve_quotes` (bool, default: `False`): If `True`, preserves smart quotes (curly quotes, apostrophes). If `False` (default), normalizes all quote-like characters to ASCII `'` and `"`.
- `preserve_dashes` (bool, default: `False`): If `True`, preserves em dashes (—) and en dashes (–). If `False` (default), converts em dashes to ` - ` and en dashes to `-`.
- `preserve_fullwidth_brackets` (bool, default: `False`): If `True`, preserves fullwidth square brackets 【】. If `False` (default), folds them to ASCII `[]`.
- `preserve_replacement_chars` (bool, default: `False`): If `True`, preserves Unicode replacement characters (U+FFFD). If `False` (default), removes them.

**Returns:** `str` - Cleaned text with normalized Unicode characters

**What it does:**

1. **Encoding Fix**: Uses `ftfy` to fix common encoding issues and mojibake
2. **Quote Normalization**: Aggressively normalizes all Unicode quote variants to ASCII `'` and `"` (unless `preserve_quotes=True`)
3. **Dash Normalization**: Converts em dashes (—) to ` - ` and en dashes (–) to `-` (unless `preserve_dashes=True`)
4. **Fullwidth Bracket Folding**: Folds fullwidth brackets 【】 to ASCII `[]` (unless `preserve_fullwidth_brackets=True`)
5. **Space Normalization**: Replaces various Unicode space separators (NBSP, narrow NBSP, etc.) with ASCII space
6. **Invisible Character Removal**: Removes zero-width spaces, bidirectional marks, and other invisible characters (unless `preserve_invisible=True`)
7. **Invalid Character Filtering**: Removes Unicode replacement characters, invalid/unassigned code points, private use area characters, and surrogates
8. **Whitespace Cleanup**: Strips trailing spaces/tabs on lines while preserving newlines and indentation

**Example:**

```python
from unicodefix.transforms import clean_text

# Default aggressive cleaning
text = "“Hello” — world…\u200b"
cleaned = clean_text(text)
# Result: '"Hello" - world...'

# Preserve smart quotes but clean everything else
cleaned = clean_text(text, preserve_quotes=True)
# Result: '"Hello" - world...'  (quotes preserved, dashes normalized)

# Preserve everything except invisible characters
cleaned = clean_text(
    text,
    preserve_quotes=True,
    preserve_dashes=True,
    preserve_fullwidth_brackets=True
)
# Result: '"Hello" — world…'  (invisible chars still removed)
```

**Note:** This function preserves 8-bit extended ASCII characters (128-255) by default, only normalizing problematic Unicode characters that cause issues in code, shell scripts, and plain text.

---

### `handle_newlines()`

Ensures text ends with a newline character unless explicitly suppressed.

**Location:** `unicodefix.transforms.handle_newlines`

**Signature:**

```python
def handle_newlines(text: str, no_newline: bool = False) -> str
```

**Parameters:**

- `text` (str, required): Input text
- `no_newline` (bool, default: `False`): If `True`, suppresses adding a final newline. If `False` (default), adds a newline if one is missing.

**Returns:** `str` - Text with final newline ensured (unless `no_newline=True`)

**What it does:**

- Checks if text ends with `\n`, `\r`, or `\r\n`
- If no newline is present and `no_newline=False`, appends `\n`
- Preserves existing line ending style (CRLF, LF, CR)
- If `no_newline=True`, returns text unchanged

**Example:**

```python
from unicodefix.transforms import handle_newlines

# Add newline if missing
text = "Line 1\nLine 2"
result = handle_newlines(text)
# Result: "Line 1\nLine 2\n"

# Suppress newline
result = handle_newlines(text, no_newline=True)
# Result: "Line 1\nLine 2"  (unchanged)

# Preserves CRLF
text = "Line 1\r\nLine 2\r\n"
result = handle_newlines(text)
# Result: "Line 1\r\nLine 2\r\n"  (unchanged, already has newline)
```

---

### `fold_for_terminal_display()`

Folds a minimal set of width-breaking Unicode punctuation for better terminal alignment.

**Location:** `unicodefix.transforms.fold_for_terminal_display`

**Signature:**

```python
def fold_for_terminal_display(text: str) -> str
```

**Parameters:**

- `text` (str, required): Input text

**Returns:** `str` - Text with fullwidth brackets folded to ASCII

**What it does:**

- Folds fullwidth square brackets 【】 to ASCII `[]`
- Intentionally does not touch other glyphs (e.g., † dagger)
- Useful for terminal/console output where fullwidth characters break alignment

**Example:**

```python
from unicodefix.transforms import fold_for_terminal_display

text = "【重要】Notice"
result = fold_for_terminal_display(text)
# Result: "[重要]Notice"
```

---

## Text Scanning & Analysis

### `scan_text_for_report()`

Scans text for Unicode anomalies and returns a structured report dictionary.

**Location:** `unicodefix.scanner.scan_text_for_report`

**Signature:**

```python
def scan_text_for_report(s: str) -> dict
```

**Parameters:**

- `s` (str, required): Input text to scan

**Returns:** `dict` - Dictionary containing anomaly counts and metadata:

```python
{
    "unicode_ghosts": {
        "NBSP_family": int,  # Non-breaking spaces and variants
        "ZWSP": int,          # Zero-width space (U+200B)
        "ZWNJ": int,          # Zero-width non-joiner (U+200C)
        "ZWJ": int,           # Zero-width joiner (U+200D)
        "LRM": int,           # Left-to-right mark (U+200E)
        "RLM": int,           # Right-to-left mark (U+200F)
        "BOM": int,           # Byte order mark (U+FEFF)
    },
    "typographic": {
        "smart_quotes": int,  # Curly quotes ""''
        "emdash": int,         # Em dash (—)
        "endash": int,         # En dash (–)
        "ellipsis": int,       # Ellipsis variants (…, ⋯, ‥)
    },
    "whitespace": {
        "trailing_lines": int,      # Lines with trailing spaces/tabs
        "blank_with_indent": int,   # Blank lines with only whitespace
    },
    "final_newline": bool,          # Whether text ends with newline
    "total": int,                   # Total anomaly count
}
```

**Example:**

```python
from unicodefix.scanner import scan_text_for_report

text = '"Hello" — world…\u200b'
result = scan_text_for_report(text)

print(result)
# {
#     'unicode_ghosts': {'NBSP_family': 0, 'ZWSP': 1, ...},
#     'typographic': {'smart_quotes': 2, 'emdash': 1, 'ellipsis': 1, ...},
#     'whitespace': {'trailing_lines': 0, 'blank_with_indent': 0},
#     'final_newline': False,
#     'total': 5
# }
```

---

## Report Generation

### `print_human()`

Prints a human-readable audit report to stdout using rich formatting.

**Location:** `unicodefix.report.print_human`

**Signature:**

```python
def print_human(path: str, data: dict, *, no_color: bool = False) -> None
```

**Parameters:**

- `path` (str, required): File path or label for the report
- `data` (dict, required): Scan result dictionary from `scan_text_for_report()`, optionally including `"metrics"` key for semantic metrics
- `no_color` (bool, default: `False`): If `True`, disables color output. If `False`, uses rich color formatting.

**Returns:** `None` (prints to stdout)

**Example:**

```python
from unicodefix.scanner import scan_text_for_report
from unicodefix.report import print_human

text = '"Hello" — world…\u200b'
anomalies = scan_text_for_report(text)
print_human("example.txt", anomalies)
# Prints formatted report with categories, counts, and color
```

---

### `print_json()`

Prints scan results as pretty-printed JSON to stdout.

**Location:** `unicodefix.report.print_json`

**Signature:**

```python
def print_json(all_results: dict) -> None
```

**Parameters:**

- `all_results` (dict, required): Dictionary mapping file paths to scan result dictionaries. Can be a single file result wrapped in a dict, or multiple files.

**Returns:** `None` (prints to stdout)

**Example:**

```python
from unicodefix.scanner import scan_text_for_report
from unicodefix.report import print_json

text1 = '"Hello" — world…'
text2 = "'Test'\u200b"

results = {
    "file1.txt": scan_text_for_report(text1),
    "file2.txt": scan_text_for_report(text2),
}
print_json(results)
# Prints JSON with all scan results
```

---

### `print_csv()`

Prints scan results as CSV to stdout.

**Location:** `unicodefix.report.print_csv`

**Signature:**

```python
def print_csv(all_results: dict) -> None
```

**Parameters:**

- `all_results` (dict, required): Dictionary mapping file paths to scan result dictionaries.

**Returns:** `None` (prints to stdout)

**Example:**

```python
from unicodefix.scanner import scan_text_for_report
from unicodefix.report import print_csv

results = {
    "file1.txt": scan_text_for_report('"Hello" — world…'),
    "file2.txt": scan_text_for_report("'Test'\u200b"),
}
print_csv(results)
# Prints CSV with headers and data rows
```

---

### `print_metrics_help()`

Prints a legend explaining semantic metrics and their ↑/↓ cues.

**Location:** `unicodefix.report.print_metrics_help`

**Signature:**

```python
def print_metrics_help(*, no_color: bool = False) -> None
```

**Parameters:**

- `no_color` (bool, default: `False`): If `True`, disables color output.

**Returns:** `None` (prints to stdout)

**Example:**

```python
from unicodefix.report import print_metrics_help

print_metrics_help()
# Prints explanation of entropy, AI score, type-token ratio, etc.
```

---

## Semantic Metrics (Experimental)

### `compute_metrics()`

Computes semantic metrics for text analysis, including entropy, AI score, and linguistic features.

**Location:** `unicodefix.metrics.compute_metrics`

**Signature:**

```python
def compute_metrics(text: str) -> dict
```

**Parameters:**

- `text` (str, required): Input text to analyze

**Returns:** `dict` - Dictionary containing computed metrics:

```python
{
    "entropy": float,                    # Shannon entropy (0.0-1.0)
    "ascii_ratio": float,                # Ratio of ASCII characters (0.0-1.0)
    "type_token_ratio": float,           # Unique tokens / total tokens (0.0-1.0)
    "avg_token_len": float,              # Average token length in characters
    "avg_sentence_len_tokens": float,    # Average sentence length in tokens
    "tokens": int,                       # Total token count
    "sentences": int,                    # Total sentence count
    "punctuation_ratio": float,          # Punctuation / total characters (0.0-1.0)
    "stopword_ratio": float,             # Stopwords / total tokens (0.0-1.0)
    "repetition_ratio": float,           # Repeated tokens / total tokens (0.0-1.0)
    "sentence_len_cv": float,            # Coefficient of variation for sentence lengths
    "digits_ratio": float,               # Digits / total characters (0.0-1.0)
    "ai_score": float,                   # Heuristic AI-generated text score (0.0-1.0)
}
```

**Dependencies:**

- Requires `nltk` package (installed automatically with `unicodefix[metrics]` or `pip install nltk`)
- Downloads NLTK data on first use (punkt tokenizer, stopwords)

**Example:**

```python
from unicodefix.metrics import compute_metrics

text = "This is a sample text for analysis. It contains multiple sentences."
metrics = compute_metrics(text)

print(metrics["ai_score"])      # 0.42 (example)
print(metrics["entropy"])       # 0.85 (example)
print(metrics["tokens"])        # 12
print(metrics["sentences"])     # 2
```

**Note:** This feature is experimental and may change in future releases. The AI score is a heuristic and should not be used as the sole indicator of AI-generated content.

---

## Complete Example: Programmatic Cleaning Pipeline

```python
from unicodefix.transforms import clean_text, handle_newlines
from unicodefix.scanner import scan_text_for_report
from unicodefix.report import print_human, print_json

# Read text from file
with open("input.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Scan for anomalies before cleaning
anomalies_before = scan_text_for_report(text)
print("Before cleaning:")
print_human("input.txt", anomalies_before)

# Clean the text
cleaned = clean_text(
    text,
    preserve_quotes=False,      # Normalize quotes
    preserve_dashes=False,      # Normalize dashes
    preserve_invisible=False    # Remove invisible chars
)

# Ensure final newline
cleaned = handle_newlines(cleaned)

# Scan after cleaning
anomalies_after = scan_text_for_report(cleaned)
print("\nAfter cleaning:")
print_human("input.txt", anomalies_after)

# Write cleaned text
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(cleaned)

# Generate JSON report for CI/CD
report = {
    "input.txt": anomalies_before,
    "output.txt": anomalies_after,
}
print_json(report)
```

---

## Error Handling

All functions raise standard Python exceptions:

- `RuntimeError`: If required dependencies (e.g., `ftfy`, `nltk`) are missing
- `ValueError`: If invalid parameters are provided
- `UnicodeDecodeError`: If text cannot be decoded (handled internally by `ftfy`)

Always wrap API calls in try/except blocks for production code:

```python
try:
    cleaned = clean_text(text)
except RuntimeError as e:
    print(f"Dependency error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Type Hints

All functions include Python 3.9+ compatible type hints. For Python 3.9, the package uses `typing.Union`, `typing.Optional`, `typing.List`, and `typing.Dict` instead of the `|` union syntax.

---

## See Also

- [Command-Line Interface Documentation](cleanup-text.md)
- [Test Suite Documentation](test-suite.md)
- [Main README](../README.md)
