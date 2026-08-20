"""Offline Unicode and provenance scanner.

``scan_text_for_report`` retains the v1 aggregate fields for existing renderers
and additionally returns the v2 finding envelope.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

import regex
import unicodedata2 as unicodedata
from confusable_homoglyphs import confusables

from unicodefix.c2pa import c2pa_findings
from unicodefix.findings import Finding, Findings, Location

_BIDI_RANGES = ((0x061C, 0x061C), (0x200E, 0x200F), (0x202A, 0x202E), (0x2066, 0x2069))
_VS_RANGES = ((0xFE00, 0xFE0F), (0xE0100, 0xE01EF))
_TOKEN_RE = regex.compile(r"[\p{L}_][\p{L}\p{N}_]*")
_DICP_CHAR_RE = regex.compile(r"\A\p{Default_Ignorable_Code_Point}\Z")


def _in_ranges(point: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= point <= end for start, end in ranges)


def _is_private_use(point: int) -> bool:
    return (
        0xE000 <= point <= 0xF8FF
        or 0xF0000 <= point <= 0xFFFFD
        or 0x100000 <= point <= 0x10FFFD
    )


def _is_noncharacter(point: int) -> bool:
    return 0xFDD0 <= point <= 0xFDEF or point & 0xFFFF in (0xFFFE, 0xFFFF)


def _location(text: str, offset: int) -> Location:
    line = text.count("\n", 0, offset) + 1
    line_start = text.rfind("\n", 0, offset) + 1
    return Location(
        line, offset - line_start + 1, line, offset - line_start + 2, offset, offset + 1
    )


def _span_location(text: str, start: int, end: int) -> Location:
    location = _location(text, start)
    return Location(
        location.line,
        location.column,
        text.count("\n", 0, end) + 1,
        end - text.rfind("\n", 0, end),
        start,
        end,
    )


def confusable_skeleton(token: str) -> str:
    """Return a conservative ASCII-biased UTS #39 detection skeleton."""

    skeleton: list[str] = []
    for character in token:
        if character.isascii() and (character.isalnum() or character == "_"):
            skeleton.append(character)
            continue
        replacements = confusables.confusables_data.get(character, ())
        replacement = next(
            (
                item["c"]
                for item in replacements
                if item["c"].isascii() and item["c"].isprintable()
            ),
            character,
        )
        skeleton.append(replacement)
    return "".join(skeleton)


def analyze_confusable_token(token: str) -> dict | None:
    """Describe a dangerous mixed-script token without changing it."""

    if not confusables.is_mixed_script(token) or not confusables.is_dangerous(token):
        return None
    matches = confusables.is_confusable(
        token, greedy=True, preferred_aliases=["latin", "common"]
    )
    if not matches:
        return None
    return {
        "token": token,
        "skeleton": confusable_skeleton(token),
        "characters": [
            {
                "character": item["character"],
                "code_point": f"U+{ord(item['character']):04X}",
                "script": item["alias"],
            }
            for item in matches
        ],
        "unicode_version": unicodedata.unidata_version,
    }


def _count_many(text: str, chars: str) -> int:
    return sum(text.count(char) for char in chars)


def _count_range(text: str, start: int, end: int) -> int:
    return sum(start <= ord(char) <= end for char in text)


def _is_quote_like(char: str) -> bool:
    name = unicodedata.name(char, "").upper()
    return unicodedata.category(char) in ("Pi", "Pf") or any(
        word in name
        for word in (
            "QUOTATION",
            "QUOTE",
            "APOSTROPHE",
            "PRIME",
            "GERSH",
            "DASIA",
            "PSILI",
        )
    )


def _script(char: str) -> str:
    """Best-effort script bucket without a third-party Unicode database."""

    if char.isascii():
        return "Latin" if char.isalpha() else "Common"
    name = unicodedata.name(char, "")
    for prefix in (
        "LATIN",
        "GREEK",
        "CYRILLIC",
        "HEBREW",
        "ARABIC",
        "HIRAGANA",
        "KATAKANA",
        "HANGUL",
        "CJK",
        "DEVANAGARI",
        "THAI",
    ):
        if name.startswith(prefix):
            return "Han" if prefix == "CJK" else prefix.title()
    return "Common" if unicodedata.category(char)[0] in "PZSN" else "Other"


def scan_findings(text: str, *, location_limit: int = 100) -> Findings:
    """Return detailed locally observable Unicode and C2PA findings."""

    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    scripts: set[str] = set()
    for offset, char in enumerate(text):
        point = ord(char)
        category = unicodedata.category(char)
        if char.isalpha():
            script = _script(char)
            if script not in {"Common", "Other"}:
                scripts.add(script)
        signals: list[str] = []
        if _DICP_CHAR_RE.fullmatch(char):
            signals.append("default_ignorable")
        if point == 0x00AD:
            signals.append("soft_hyphen")
        if point in (0x2060, 0x034F):
            signals.append("word_or_grapheme_joiner")
        if _in_ranges(point, _BIDI_RANGES):
            signals.append("bidi_control")
        if _in_ranges(point, _VS_RANGES):
            signals.append("variation_selector")
        if 0xE0000 <= point <= 0xE007F:
            signals.append("tag_character")
        if _is_private_use(point):
            signals.append("private_use")
        if _is_noncharacter(point):
            signals.append("noncharacter")
        if category == "Cn":
            signals.append("unassigned")
        if category == "Cs":
            signals.append("surrogate")
        if char == "\ufffd":
            signals.append("replacement_character")
        if point == 0xFEFF and offset != 0:
            signals.append("noninitial_bom")
        for signal in signals:
            grouped[("unicode_security", signal)].append(offset)
        if char in "“”‘’":
            grouped[("typography", "smart_quote")].append(offset)
        elif char in "\u2010\u2011\u2012\u2013\u2014\u2015":
            grouped[("typography", "unicode_dash_or_hyphen")].append(offset)
        elif char in "\u2025\u2026\u22ef":
            grouped[("typography", "unicode_ellipsis")].append(offset)
        if unicodedata.category(char) == "Zs" and char != " ":
            grouped[("formatting", "unusual_space_separator")].append(offset)

    findings = Findings()
    for (category, signal), offsets in sorted(grouped.items()):
        locations = tuple(
            _location(text, offset) for offset in offsets[:location_limit]
        )
        removable = signal not in {"variation_selector", "mixed_scripts"}
        findings.add(
            Finding(
                category=category,
                signal=signal,
                count=len(offsets),
                locations=locations,
                confidence="high",
                removable=removable,
                planned_action="remove" if removable else "report",
                message=f"{len(offsets)} {signal.replace('_', ' ')} character(s) found locally.",
                details={"locations_truncated": len(offsets) > location_limit},
            )
        )
    if len(scripts) > 1:
        findings.add(
            Finding(
                category="unicode_security",
                signal="mixed_scripts",
                count=len(scripts),
                confidence="medium",
                removable=False,
                planned_action="report",
                message="Multiple alphabetic scripts occur in the document; inspect identifiers and look-alikes.",
                details={"scripts": sorted(scripts)},
            )
        )
    confusable_tokens = []
    confusable_locations = []
    for match in _TOKEN_RE.finditer(text):
        analysis = analyze_confusable_token(match.group(0))
        if analysis is None:
            continue
        confusable_tokens.append(analysis)
        confusable_locations.append(_span_location(text, match.start(), match.end()))
    if confusable_tokens:
        findings.add(
            Finding(
                category="unicode_security",
                signal="confusable_mixed_script_token",
                count=len(confusable_tokens),
                locations=tuple(confusable_locations[:location_limit]),
                confidence="medium",
                removable=False,
                planned_action="report",
                message="Mixed-script token(s) contain Unicode confusables; skeletons are detection-only.",
                details={
                    "tokens": confusable_tokens[:location_limit],
                    "locations_truncated": len(confusable_tokens) > location_limit,
                },
            )
        )
    nfc = unicodedata.normalize("NFC", text)
    nfkc = unicodedata.normalize("NFKC", text)
    if nfc != text or nfkc != text:
        findings.add(
            Finding(
                category="unicode_security",
                signal="normalization_difference",
                confidence="informational",
                removable=False,
                planned_action="report",
                message="Unicode normalization would change this document.",
                details={"nfc_changes": nfc != text, "nfkc_changes": nfkc != text},
            )
        )
    for finding in c2pa_findings(text):
        findings.add(finding)
    return findings


@dataclass
class ScanResult:
    unicode_ghosts: dict
    typographic: dict
    whitespace: dict
    final_newline: bool

    def total_counts(self) -> int:
        total = sum(
            int(value)
            for key, value in self.unicode_ghosts.items()
            if key != "NBSP_family"
        )
        total += sum(
            int(value)
            for key, value in self.typographic.items()
            if key not in {"smart_quotes_basic", "ascii_quote_like"}
        )
        total += sum(int(value) for value in self.whitespace.values())
        return total + (0 if self.final_newline else 1)


def scan_text_for_report(text: str) -> dict:
    """Legacy aggregate report plus the v2 ``findings`` envelope."""

    zs = "\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000"
    smart_basic = _count_many(text, "“”‘’")
    ascii_quotes = sum(_is_quote_like(char) and ord(char) <= 0x7F for char in text)
    unicode_quotes = sum(
        _is_quote_like(char) and ord(char) > 0x7F and char not in "“”‘’"
        for char in text
    )
    ghosts = {
        "NBSP_family": _count_many(text, "\u00a0\u202f\u2002\u2003\u2009\u3000"),
        "Zs_spaces": _count_many(text, zs),
        "ZWSP": text.count("\u200b"),
        "ZWNJ": text.count("\u200c"),
        "ZWJ": text.count("\u200d"),
        "LRM": text.count("\u200e"),
        "RLM": text.count("\u200f"),
        "BOM": text.count("\ufeff"),
        "bidi_overrides": _count_range(text, 0x202A, 0x202E),
        "bidi_isolates": _count_range(text, 0x2066, 0x2069),
        "replacement_char": text.count("\ufffd"),
        "default_ignorables": sum(bool(_DICP_CHAR_RE.fullmatch(char)) for char in text),
        "variation_selectors": sum(_in_ranges(ord(char), _VS_RANGES) for char in text),
        "tag_characters": _count_range(text, 0xE0000, 0xE007F),
        "noncharacters": sum(_is_noncharacter(ord(char)) for char in text),
        "private_use": sum(_is_private_use(ord(char)) for char in text),
        "surrogates": _count_range(text, 0xD800, 0xDFFF),
        "unassigned_cn": sum(
            unicodedata.category(char) == "Cn" and ord(char) > 0x7F for char in text
        ),
    }
    typographic = {
        "smart_quotes": smart_basic,
        "smart_quotes_basic": smart_basic,
        "unicode_quote_like": unicode_quotes,
        "ascii_quote_like": ascii_quotes,
        "unicode_hyphen": text.count("\u2010"),
        "nonbreaking_hyphen": text.count("\u2011"),
        "figure_dash": text.count("\u2012"),
        "emdash": text.count("\u2014"),
        "endash": text.count("\u2013"),
        "horizontal_bar": text.count("\u2015"),
        "ellipsis": _count_many(text, "\u2026\u22ef\u2025"),
        "fullwidth_brackets": _count_many(text, "\u3010\u3011"),
    }
    lines = text.splitlines(keepends=True)
    whitespace = {
        "trailing_lines": sum(
            line.rstrip("\r\n").endswith((" ", "\t")) for line in lines
        ),
        "blank_with_indent": sum(
            line.strip("\r\n") != "" and line.strip() == "" for line in lines
        ),
    }
    result = ScanResult(
        ghosts, typographic, whitespace, bool(text) and text.endswith(("\n", "\r"))
    )
    data = asdict(result)
    data["total"] = result.total_counts()
    data.update(scan_findings(text).to_dict())
    return data
