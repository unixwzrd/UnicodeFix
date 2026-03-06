from unicodefix.scanner import scan_text_for_report


def test_scanner_counts_core_signals():
    s = "a\u200bb “q”—r… re\u2011enter\nline \t\n  \n"
    d = scan_text_for_report(s)
    assert d["unicode_ghosts"]["ZWSP"] == 1
    assert d["typographic"]["smart_quotes"] >= 1
    assert d["typographic"]["emdash"] == 1
    assert d["typographic"]["nonbreaking_hyphen"] == 1
    assert d["typographic"]["ellipsis"] >= 1
    assert d["whitespace"]["trailing_lines"] >= 1
    assert d["whitespace"]["blank_with_indent"] >= 1
    assert d["total"] >= 1


def test_scanner_splits_ascii_quotes_without_counting_them_as_anomalies():
    s = 'plain "ascii" and apostrophe\'s only\n'
    d = scan_text_for_report(s)
    assert d["typographic"]["ascii_quote_like"] == 3
    assert d["typographic"]["smart_quotes"] == 0
    assert d["typographic"]["unicode_quote_like"] == 0
    assert d["total"] == 0


def test_scanner_reports_nbsp_family():
    s = "a\u00a0b\u202fc\n"
    d = scan_text_for_report(s)
    assert d["unicode_ghosts"]["NBSP_family"] == 2
    assert d["unicode_ghosts"]["Zs_spaces"] >= 2
    assert d["total"] >= 2
