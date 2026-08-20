"""Deterministic document metrics; no linguistic authorship scoring."""

from __future__ import annotations

import re
from collections import Counter

import unicodedata2 as unicodedata
from confusable_homoglyphs import confusables

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _newline_style(text: str) -> str:
    crlf = text.count("\r\n")
    remainder = text.replace("\r\n", "")
    lf = remainder.count("\n")
    cr = remainder.count("\r")
    styles = sum(bool(value) for value in (crlf, lf, cr))
    if styles == 0:
        return "none"
    if styles > 1:
        return "mixed"
    return "crlf" if crlf else "lf" if lf else "cr"


def compute_metrics(text: str) -> dict:
    """Return reproducible structural counts, never an AI-likeness score."""

    codepoints = Counter(f"U+{ord(char):04X}" for char in text if ord(char) > 127)
    inventory = {}
    for point, count in sorted(codepoints.items()):
        ordinal = int(point.replace("U+", "0x", 1), 0)
        inventory[point] = {
            "count": count,
            "name": unicodedata.name(chr(ordinal), "UNASSIGNED"),
            "category": unicodedata.category(chr(ordinal)),
            "script": confusables.alias(chr(ordinal)),
        }
    return {
        "bytes_utf8": len(text.encode("utf-8", "surrogatepass")),
        "characters": len(text),
        "lines": len(text.splitlines()),
        "words": len(_WORD_RE.findall(text)),
        "newline_style": _newline_style(text),
        "ascii_characters": sum(ord(char) < 128 for char in text),
        "non_ascii_characters": sum(ord(char) >= 128 for char in text),
        "non_ascii_codepoints": dict(sorted(codepoints.items())),
        "non_ascii_inventory": inventory,
        "unicode_version": unicodedata.unidata_version,
    }
