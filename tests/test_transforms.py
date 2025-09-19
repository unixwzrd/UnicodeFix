from unicodefix.transforms import clean_text, handle_newlines


def test_quotes_and_dashes_normalize():
    s = '“hi”—said… Bob’s'
    out = clean_text(s)
    assert '"' in out and "'" in out
    assert " - " in out         # em dash spaced
    assert "..." in out         # ellipsis normalized


def test_invisible_removed_by_default():
    s = "a\u200Bb"
    out = clean_text(s)
    assert out == "ab\n" or out == "ab"  # newline may be added later by handle_newlines


def test_handle_newlines():
    assert handle_newlines("x") == "x\n"
    assert handle_newlines("x\n") == "x\n"
    assert handle_newlines("x", no_newline=True) == "x"
