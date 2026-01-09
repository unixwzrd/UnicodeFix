from unicodefix.scanner import scan_text_for_report


def test_scanner_counts_core_signals():
    s = "a\u200Bb “q”—r…\nline \t\n  \n"
    d = scan_text_for_report(s)
    assert d["unicode_ghosts"]["ZWSP"] == 1
    assert d["typographic"]["smart_quotes"] >= 1
    assert d["typographic"]["emdash"] == 1
    assert d["typographic"]["ellipsis"] >= 1
    assert d["whitespace"]["trailing_lines"] >= 1
    assert d["whitespace"]["blank_with_indent"] >= 1
    assert d["total"] >= 1
