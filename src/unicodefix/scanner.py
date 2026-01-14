import unicodedata
from dataclasses import asdict, dataclass


def _count_many(s: str, chars: str) -> int:
    return sum(s.count(c) for c in chars)


def _count_range(s: str, start: int, end: int) -> int:
    """Count chars with ord in [start, end] inclusive."""
    return sum(1 for ch in s if start <= ord(ch) <= end)


def _count_category(s: str, category: str) -> int:
    """Count chars where unicodedata.category(ch) == category."""
    n = 0
    for ch in s:
        try:
            if unicodedata.category(ch) == category:
                n += 1
        except Exception:
            continue
    return n


def _count_unassigned_cn(s: str) -> int:
    """Count unassigned Unicode chars (Cn) above ASCII."""
    n = 0
    for ch in s:
        code = ord(ch)
        if code <= 0x7F:
            continue
        try:
            if unicodedata.category(ch) == "Cn":
                n += 1
        except Exception:
            # If Unicode metadata fails, treat as suspicious
            n += 1
    return n


def _count_quote_like(s: str) -> int:
    """
    Count quote-like characters beyond the basic “ ” ‘ ’.
    Mirrors the quote-normalization intent in transforms.clean_text().
    """
    n = 0
    for ch in s:
        try:
            name = unicodedata.name(ch, "").upper()
            cat = unicodedata.category(ch)
        except Exception:
            continue

        if cat in ("Pi", "Pf"):
            n += 1
            continue

        if any(
            k in name
            for k in (
                "QUOTATION",
                "QUOTE",
                "APOSTROPHE",
                "PRIME",
                "GERSH",
                "DASIA",
                "PSILI",
            )
        ):
            n += 1
    return n


@dataclass
class ScanResult:
    unicode_ghosts: dict
    typographic: dict
    whitespace: dict
    final_newline: bool

    def total_counts(self) -> int:
        total = 0
        for d in (self.unicode_ghosts, self.typographic, self.whitespace):
            total += sum(int(v) for v in d.values())
        if not self.final_newline:
            total += 1
        return total


def scan_text_for_report(s: str) -> dict:
    # whitespace separators you normalize in transforms.py
    zs_separators = (
        "\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009"
        "\u200a\u202f\u205f\u3000"
    )

    ghosts = {
        # space oddities
        "NBSP_family": _count_many(s, "\u00a0\u202f\u2002\u2003\u2009\u3000"),
        "Zs_spaces": _count_many(s, zs_separators),
        # invisible / controls you strip
        "ZWSP": s.count("\u200b"),
        "ZWNJ": s.count("\u200c"),
        "ZWJ": s.count("\u200d"),
        "LRM": s.count("\u200e"),
        "RLM": s.count("\u200f"),
        "BOM": s.count("\ufeff"),
        # bidi controls: embeddings/overrides + isolates
        "bidi_overrides": _count_range(s, 0x202A, 0x202E),
        "bidi_isolates": _count_range(s, 0x2066, 0x2069),
        # encoding corruption
        "replacement_char": s.count("\ufffd"),
    }

    smart_basic = _count_many(s, "“”‘’")
    typographic = {
        # Keep schema stability: tests + downstream expect "smart_quotes"
        "smart_quotes": smart_basic,
        # Extra detail fields (fine to keep)
        "smart_quotes_basic": smart_basic,
        "quote_like_total": _count_quote_like(s),
        "emdash": s.count("\u2014"),
        "endash": s.count("\u2013"),
        "ellipsis": s.count("\u2026") + s.count("\u22ef") + s.count("\u2025"),
        # fullwidth punct you fold (【】)
        "fullwidth_brackets": _count_many(s, "\u3010\u3011"),
    }

    # Unicode validity / suspicious categories
    validity = {
        "private_use": (
            _count_range(s, 0xE000, 0xF8FF)
            + _count_range(s, 0xF0000, 0xFFFFD)
            + _count_range(s, 0x100000, 0x10FFFD)
        ),
        "surrogates": _count_range(s, 0xD800, 0xDFFF),
        "unassigned_cn": _count_unassigned_cn(s),
    }

    lines = s.splitlines(keepends=True)
    trailing = sum(1 for ln in lines if ln.rstrip("\r\n").endswith((" ", "\t")))
    blank_indent = sum(
        1 for ln in lines if (ln.strip("\r\n") != "" and ln.strip() == "")
    )
    whitespace = {"trailing_lines": trailing, "blank_with_indent": blank_indent}

    final_nl = bool(s) and s.endswith(("\n", "\r", "\r\n"))

    # merge validity signals into unicode_ghosts (keeps your existing structure)
    ghosts.update(validity)

    res = ScanResult(ghosts, typographic, whitespace, final_nl)
    d = asdict(res)
    d["total"] = res.total_counts()
    return d
