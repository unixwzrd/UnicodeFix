from unicodefix.transforms import clean_text, handle_newlines


def test_quotes_and_dashes_normalize():
    s = "\u201chi\u201d\u2014said\u2026 Bob\u2019s"  # "hi"—said… Bob's
    out = clean_text(s)
    assert '"' in out and "'" in out
    assert " - " in out  # em dash spaced
    assert "..." in out  # ellipsis normalized


def test_invisible_removed_by_default():
    s = "a\u200bb"
    out = clean_text(s)
    assert out == "ab\n" or out == "ab"  # newline may be added later by handle_newlines


def test_handle_newlines():
    assert handle_newlines("x") == "x\n"
    assert handle_newlines("x\n") == "x\n"
    assert handle_newlines("x", no_newline=True) == "x"


def test_newlines_preserved_single_line():
    """Test that newlines are preserved in single-line text."""
    text = "Line 1\n"
    result = clean_text(text)
    assert "\n" in result, "Newline should be preserved"
    assert result.count("\n") >= text.count("\n"), "Should preserve or add newlines"


def test_newlines_preserved_multi_line():
    """Test that newlines are preserved in multi-line text (critical for file structure)."""
    text = "Line 1\nLine 2\nLine 3\n"
    result = clean_text(text)
    assert result.count("\n") == text.count("\n"), "All newlines must be preserved"
    assert len(result.splitlines()) == len(
        text.splitlines()
    ), "Line structure must be preserved"


def test_newlines_preserved_with_unicode():
    """Test that newlines are preserved even when Unicode characters are normalized."""
    text = '"Line 1"\n"Line 2"—said…\nLine 3\n'
    result = clean_text(text)
    assert result.count("\n") == text.count(
        "\n"
    ), "Newlines preserved despite Unicode normalization"
    assert len(result.splitlines()) == len(
        text.splitlines()
    ), "Line structure preserved"


def test_newlines_preserved_with_tabs():
    """Test that tabs and newlines are both preserved."""
    text = "Line 1\n\tIndented line\nLine 2\n"
    result = clean_text(text)
    assert (
        "\n" in result and "\t" in result
    ), "Both newlines and tabs should be preserved"
    assert result.count("\n") == text.count("\n"), "Newline count preserved"
    assert result.count("\t") == text.count("\t"), "Tab count preserved"


def test_newlines_preserved_crlf():
    """Test that CRLF line endings are handled correctly."""
    text = "Line 1\r\nLine 2\r\n"
    result = clean_text(text)
    # CRLF may be normalized to LF, but newlines must be preserved
    assert "\n" in result or "\r\n" in result, "Line endings must be preserved"
    assert len(result.splitlines()) >= len(
        text.splitlines()
    ), "Line structure preserved"


def test_newlines_preserved_empty_lines():
    """Test that empty lines (consecutive newlines) are preserved."""
    text = "Line 1\n\nLine 2\n\n\nLine 3\n"
    result = clean_text(text)
    assert result.count("\n") >= text.count(
        "\n"
    ), "Empty lines (newlines) must be preserved"
    # Should have at least the same number of line breaks
    assert len(result.splitlines()) >= len(
        text.splitlines()
    ), "Empty line structure preserved"


def test_newlines_preserved_no_trailing():
    """Test that newlines are preserved even when file doesn't end with newline."""
    text = "Line 1\nLine 2\nLine 3"  # No trailing newline
    result = clean_text(text)
    assert result.count("\n") >= text.count("\n"), "Internal newlines must be preserved"
    assert len(result.splitlines()) >= len(
        text.splitlines()
    ), "Line structure preserved"
