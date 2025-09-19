from dataclasses import asdict, dataclass


def _count_many(s: str, chars: str) -> int:
    return sum(s.count(c) for c in chars)


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
    ghosts = {
        "NBSP_family": _count_many(s, "\u00A0\u202F\u2002\u2003\u2009\u3000"),
        "ZWSP": s.count("\u200B"),
        "ZWNJ": s.count("\u200C"),
        "ZWJ":  s.count("\u200D"),
        "LRM":  s.count("\u200E"),
        "RLM":  s.count("\u200F"),
        "BOM":  s.count("\ufeff"),
    }
    typographic = {
        "smart_quotes": _count_many(s, "“”‘’"),
        "emdash": s.count("\u2014"),
        "endash": s.count("\u2013"),
        "ellipsis": s.count("\u2026") + s.count("\u22EF") + s.count("\u2025"),
    }
    lines = s.splitlines(keepends=True)
    trailing = sum(1 for ln in lines if ln.rstrip("\r\n").endswith((" ", "\t")))
    blank_indent = sum(1 for ln in lines if (ln.strip("\r\n") != "" and ln.strip() == ""))
    whitespace = {"trailing_lines": trailing, "blank_with_indent": blank_indent}
    final_nl = bool(s) and s.endswith(("\n", "\r", "\r\n"))
    res = ScanResult(ghosts, typographic, whitespace, final_nl)
    d = asdict(res)
    d["total"] = res.total_counts()
    return d
