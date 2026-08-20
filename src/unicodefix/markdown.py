"""Markdown-specific inventory and safe prose unwrapping.

This module deliberately treats a physical line break as formatting, not
provenance.  ``unwrap_markdown`` only removes CommonMark soft breaks; it does
not turn separate Markdown blocks or list items into one another.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

try:  # Keep the core importable for report-only installations.
    import mdformat
except Exception as exc:  # pragma: no cover - depends on optional install
    mdformat = None
    _MDFORMAT_ERROR = exc
else:  # pragma: no cover - trivial branch
    _MDFORMAT_ERROR = None


_FENCE_RE = re.compile(r"^\s{0,3}(?:`{3,}|~{3,})")
_ATX_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}(?:\s|$)")
_SETEXT_RE = re.compile(r"^\s{0,3}(?:={3,}|-{3,})\s*$")
_THEMATIC_RE = re.compile(r"^\s{0,3}(?:[-*_]\s*){3,}$")
_LIST_RE = re.compile(r"^(?P<indent>\s*)(?:[-+*]|\d+[.)])\s+(?:\[[ xX]\]\s+)?")
_BLOCKQUOTE_RE = re.compile(r"^\s{0,3}> ?")
_REFERENCE_RE = re.compile(r"^\s{0,3}\[[^]]+\]:\s*\S+")
_HTML_RE = re.compile(r"^\s*</?[A-Za-z][^>]*>\s*$|^\s*<!--")
_TABLE_RE = re.compile(
    r"^\s*\|.*\|\s*$|^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)


def _is_protected(line: str, in_fence: bool) -> bool:
    """Whether *line* belongs to syntax where joining would be unsafe."""
    if in_fence or not line.strip():
        return True
    if line.startswith("    ") or line.startswith("\t"):
        return True
    return bool(
        _ATX_HEADING_RE.match(line)
        or _SETEXT_RE.match(line)
        or _THEMATIC_RE.match(line)
        or _REFERENCE_RE.match(line)
        or _HTML_RE.match(line)
        or _TABLE_RE.match(line)
    )


def _line_prefix(line: str) -> tuple[str, str]:
    """Return Markdown container prefix and paragraph content for a line."""
    prefix = ""
    rest = line
    # A blockquote may contain a list, and lists can be nested.  Preserve each
    # marker but compare only the stable container prefix during joining.
    while True:
        quote = _BLOCKQUOTE_RE.match(rest)
        if quote:
            prefix += quote.group(0)
            rest = rest[quote.end() :]
            continue
        item = _LIST_RE.match(rest)
        if item:
            marker = item.group(0)
            prefix += marker
            rest = rest[item.end() :]
        break
    return prefix, rest


def _continuation_prefix(prefix: str) -> str:
    """Indent continuation text enough to stay in the current list item."""
    # For quoted list items retain quote markers. mdformat will canonicalize
    # cosmetic indentation after this conservative transformation.
    if not prefix:
        return ""
    quote_parts = re.findall(r"(?:^|\s)> ?", prefix)
    quotes = "> " * len(quote_parts)
    non_quote = re.sub(r"(?:^|\s)> ?", "", prefix)
    return quotes + " " * len(non_quote)


def _has_hard_break(line: str) -> bool:
    return line.endswith("\\") or line.endswith("  ")


def _fallback_unwrap(text: str) -> str:
    """Conservatively join soft breaks before handing Markdown to mdformat."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_fence = False
    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.rstrip("\r\n")
        newline = raw[len(line) :]
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(raw)
            index += 1
            continue
        if _is_protected(line, in_fence):
            out.append(raw)
            index += 1
            continue

        prefix, content = _line_prefix(line)
        if not content.strip() or _has_hard_break(line):
            out.append(raw)
            index += 1
            continue

        assembled = line
        current_prefix = prefix
        while index + 1 < len(lines):
            candidate_raw = lines[index + 1]
            candidate = candidate_raw.rstrip("\r\n")
            candidate_indent = len(candidate) - len(candidate.lstrip(" "))
            list_continuation = bool(
                current_prefix
                and candidate_indent
                and candidate_indent <= len(current_prefix)
                and not _LIST_RE.match(candidate)
            )
            if _FENCE_RE.match(candidate) or (
                _is_protected(candidate, in_fence) and not list_continuation
            ):
                break
            if not candidate.strip() or _has_hard_break(assembled):
                break
            candidate_prefix, candidate_content = _line_prefix(candidate)
            # A marker begins a new element. A matching container is a new
            # item too, never a continuation. Otherwise an indented or plain
            # line is a continuation of this paragraph/list item.
            if candidate_prefix and candidate_content.strip():
                # Repeated blockquote markers are continuation lines, unlike
                # repeated list markers which necessarily start a sibling.
                if not (
                    current_prefix
                    and (
                        (
                            candidate_prefix == current_prefix
                            and "-" not in candidate_prefix
                            and "+" not in candidate_prefix
                            and "*" not in candidate_prefix
                            and not re.search(r"\d+[.)]\s", candidate_prefix)
                        )
                        # CommonMark quotes repeat the quote marker on every
                        # physical line of a list item's continuation.
                        or (
                            current_prefix.startswith(candidate_prefix)
                            and candidate_prefix.rstrip().endswith(">")
                            and candidate_content.startswith(" ")
                        )
                    )
                ):
                    break
            if candidate.startswith(("    ", "\t")) and not list_continuation:
                break
            quoted_list_continuation = bool(
                candidate_prefix
                and current_prefix.startswith(candidate_prefix)
                and candidate_prefix.rstrip().endswith(">")
                and candidate_content.startswith(" ")
            )
            if (
                candidate_prefix != current_prefix
                and candidate_prefix
                and not quoted_list_continuation
            ):
                break
            joined = (
                candidate_content.strip() if candidate_prefix else candidate.strip()
            )
            if not joined:
                break
            assembled = assembled.rstrip() + " " + joined
            index += 1
        out.append(assembled + newline)
        index += 1
    return "".join(out)


def audit_markdown(text: str) -> dict[str, Any]:
    """Return deterministic Markdown formatting metrics without mutation."""
    lines = text.splitlines()
    widths: Counter[int] = Counter()
    soft_breaks = 0
    list_continuations = 0
    protected_hard_breaks = 0
    in_fence = False
    for index, line in enumerate(lines[:-1]):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if _has_hard_break(line):
            protected_hard_breaks += 1
            continue
        following = lines[index + 1]
        if (
            line.strip()
            and following.strip()
            and not _is_protected(line, False)
            and not _is_protected(following, False)
            and not _LIST_RE.match(following)
            and not _BLOCKQUOTE_RE.match(following)
        ):
            soft_breaks += 1
            prefix, _ = _line_prefix(line)
            if prefix:
                list_continuations += 1
        if len(line.rstrip()) in {72, 78, 79, 80}:
            widths[len(line.rstrip())] += 1
    # Last line can itself be one of the conventional widths.
    if lines and len(lines[-1].rstrip()) in {72, 78, 79, 80}:
        widths[len(lines[-1].rstrip())] += 1
    return {
        "lines": len(lines),
        "soft_break_candidates": soft_breaks,
        "wrapped_list_item_continuations": list_continuations,
        "protected_hard_breaks": protected_hard_breaks,
        "probable_fixed_column_wrapping": dict(sorted(widths.items())),
    }


def unwrap_markdown(text: str) -> str:
    """Unwrap soft prose breaks with mdformat available as a local dependency.

    ``mdformat`` performs final Markdown-aware serialization.  The local
    pre-pass makes the intended no-wrap policy explicit and handles content
    from older mdformat releases consistently.
    """
    if mdformat is None:
        raise RuntimeError(
            "Markdown unwrapping requires the optional 'mdformat' dependency. "
            "Install UnicodeFix with Markdown support."
        ) from _MDFORMAT_ERROR
    prepared = _fallback_unwrap(text)
    return mdformat.text(prepared)
