from unicodefix.metrics import compute_metrics


def test_metrics_are_deterministic_and_not_authorship_scores():
    metrics = compute_metrics("one two\r\nthree")
    assert metrics["bytes_utf8"] == len(b"one two\r\nthree")
    assert metrics["words"] == 3
    assert metrics["newline_style"] == "crlf"
    assert "ai_score" not in metrics
    assert "entropy" not in metrics


def test_metrics_include_unicode_17_codepoint_inventory():
    metrics = compute_metrics("x\u00a0x")
    assert metrics["unicode_version"].startswith("17.")
    assert metrics["non_ascii_inventory"]["U+00A0"] == {
        "count": 1,
        "name": "NO-BREAK SPACE",
        "category": "Zs",
        "script": "COMMON",
    }
