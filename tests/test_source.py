from unicodefix.c2pa import build_text_wrapper
from unicodefix.source import clean_source_comments, scan_source
import pytest


def _variation_wrapper(payload: bytes) -> str:
    return "\ufeff" + "".join(
        chr(0xFE00 + value) if value < 16 else chr(0xE0100 + value - 16)
        for value in payload
    )


def test_python_source_reports_contexts_and_cleans_comments_only():
    carrier = _variation_wrapper(build_text_wrapper(b"opaque"))
    source = (
        f"# note\u200b and {carrier}\n"
        "name = 'string\u200b'  # hidden\u2060 comment\n"
        "print(name)\n"
    )
    report = scan_source(source, language="python")
    assert report["parser"] == "python-tokenize"
    assert report["parse_valid"] is True
    assert report["counts"]["comments"] > 0
    assert report["counts"]["strings"] == 1
    assert any(item["signal"] == "c2pa_text_carrier" for item in report["findings"])

    cleaned = clean_source_comments(source, language="python", strip_provenance=True)
    assert "# note and " in cleaned
    assert carrier not in cleaned
    assert "'string\u200b'" in cleaned
    assert "name =" in cleaned


def test_generic_fallback_is_audit_only_but_can_clean_comments():
    source = "const label = 'keep\u200b'; // remove\u200b this\n"
    report = scan_source(source, path="example.js")
    assert report["parser"] in {"generic", "tree-sitter"}
    assert report["parse_valid"] in {None, True}
    assert report["counts"]["comments"] == 1
    assert report["counts"]["strings"] == 1

    cleaned = clean_source_comments(source, path="example.js")
    assert "'keep\u200b'" in cleaned
    assert "// remove this" in cleaned


def test_bare_c2pa_magic_is_not_treated_as_a_standardized_carrier():
    source = "// C2PATXT\0opaque\nconst preserved = 1;\n"
    assert clean_source_comments(source, path="example.js") == source
    assert (
        clean_source_comments(source, path="example.js", strip_provenance=True)
        == source
    )


def test_structured_c2pa_is_removed_only_from_source_comments():
    comment = (
        "# -----BEGIN C2PA MANIFEST----- https://example.invalid/a.c2pa "
        "-----END C2PA MANIFEST-----\n"
    )
    string_value = (
        'value = "# -----BEGIN C2PA MANIFEST----- https://example.invalid/a.c2pa '
        '-----END C2PA MANIFEST-----"\n'
    )
    source = comment + string_value

    report = scan_source(source, path="sample.py")
    assert report["findings"][0]["context"] == "comments"
    cleaned = clean_source_comments(source, path="sample.py", strip_provenance=True)

    assert cleaned == string_value


def test_invalid_python_is_not_modified():
    source = "def broken(:  # payload\u200b\n"
    assert scan_source(source, language="python")["parse_valid"] is False
    assert clean_source_comments(source, language="python") == source


def test_confusable_identifier_is_reported_and_never_rewritten():
    source = "pаypal = 1\n"  # Cyrillic small a.
    report = scan_source(source, language="python")
    finding = next(
        item
        for item in report["findings"]
        if item["signal"] == "confusable_mixed_script_identifier"
    )
    assert finding["details"]["skeleton"] == "paypal"
    assert finding["planned_action"] == "report_only"
    assert clean_source_comments(source, language="python") == source


@pytest.mark.parametrize(
    ("path", "source", "preserved"),
    [
        ("sample.c", '// remove\u200b\nchar *s = "keep\u200b";\n', '"keep\u200b"'),
        ("sample.cpp", '// remove\u200b\nauto s = "keep\u200b";\n', '"keep\u200b"'),
        ("sample.js", '// remove\u200b\nconst s = "keep\u200b";\n', '"keep\u200b"'),
        ("sample.yaml", '# remove\u200b\nvalue: "keep\u200b"\n', '"keep\u200b"'),
        ("sample.toml", '# remove\u200b\nvalue = "keep\u200b"\n', '"keep\u200b"'),
    ],
)
def test_tree_sitter_languages_clean_comments_and_preserve_strings(
    path, source, preserved
):
    report = scan_source(source, path=path)
    assert report["parser"] == "tree-sitter"
    assert report["parse_valid"] is True
    cleaned = clean_source_comments(source, path=path)
    assert "remove\u200b" not in cleaned
    assert preserved in cleaned
