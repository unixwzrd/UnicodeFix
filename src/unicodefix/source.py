"""Conservative, local source-code Unicode inspection.

This module deliberately does not rewrite identifiers, strings, or syntax.  It
only knows how to remove an exact hidden-Unicode or C2PA text carrier when the
carrier occurs in a comment.  The optional Tree-sitter integration is an
enhancement; Python source remains useful with the standard library alone.
"""

from __future__ import annotations

import ast
import io
import os
import re
import token
import tokenize
from dataclasses import dataclass
from typing import Iterable, Optional

import regex
import unicodedata2 as unicodedata

from unicodefix.c2pa import find_c2pa_carriers
from unicodefix.scanner import analyze_confusable_token

_PYTHON_SUFFIXES = {".py", ".pyi", ".pyw"}
_LANGUAGE_SUFFIXES = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
}
_LINE_COMMENT_PREFIXES = ("//", "#")
_HIDDEN_CHAR_RE = regex.compile(r"\A\p{Default_Ignorable_Code_Point}\Z")


@dataclass(frozen=True)
class _Span:
    start: int
    end: int
    context: str


def _language(language: Optional[str], path: Optional[str]) -> str:
    candidate = (language or "").lower().lstrip(".")
    if candidate:
        return {"py": "python", "c++": "cpp", "c#": "c_sharp"}.get(candidate, candidate)
    suffix = os.path.splitext(path or "")[1].lower()
    if suffix in _PYTHON_SUFFIXES:
        return "python"
    return _LANGUAGE_SUFFIXES.get(suffix, "unknown")


def _line_offsets(text: str) -> list[int]:
    starts = [0]
    starts.extend(match.end() for match in re.finditer("\\n", text))
    return starts


def _offset(starts: list[int], line: int, column: int) -> int:
    return starts[line - 1] + column


def _position(starts: list[int], index: int) -> tuple[int, int]:
    # A short linear scan avoids a dependency and is insignificant next to
    # parsing; source findings are normally sparse.
    line = 1
    for number, start in enumerate(starts, 1):
        if start > index:
            break
        line = number
    return line, index - starts[line - 1] + 1


def _is_hidden(character: str) -> bool:
    return bool(_HIDDEN_CHAR_RE.fullmatch(character))


def _c2pa_ranges(value: str, base: int) -> list[tuple[int, int]]:
    return [
        (base + carrier.start, base + carrier.end)
        for carrier in find_c2pa_carriers(value)
        if carrier.valid
    ]


def _python_spans(text: str) -> tuple[list[_Span], bool]:
    starts = _line_offsets(text)
    spans: list[_Span] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        for item in tokens:
            if item.type == tokenize.COMMENT:
                spans.append(
                    _Span(
                        _offset(starts, item.start[0], item.start[1]),
                        _offset(starts, item.end[0], item.end[1]),
                        "comments",
                    )
                )
            elif item.type == token.STRING:
                spans.append(
                    _Span(
                        _offset(starts, item.start[0], item.start[1]),
                        _offset(starts, item.end[0], item.end[1]),
                        "strings",
                    )
                )
            elif item.type == token.NAME:
                spans.append(
                    _Span(
                        _offset(starts, item.start[0], item.start[1]),
                        _offset(starts, item.end[0], item.end[1]),
                        "identifiers",
                    )
                )
    except (tokenize.TokenError, IndentationError):
        # ast.parse below remains the validity authority.  Partial spans still
        # make an invalid file auditable without attempting cleanup.
        pass
    try:
        ast.parse(text)
        valid = True
    except (SyntaxError, ValueError, TypeError):
        valid = False
    return spans, valid


def _generic_spans(text: str) -> list[_Span]:
    """Small lexer for comments and quoted strings in unsupported languages."""
    spans: list[_Span] = []
    index = 0
    size = len(text)
    while index < size:
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = size if end == -1 else end + 2
            spans.append(_Span(index, end, "comments"))
            index = end
        elif text.startswith(_LINE_COMMENT_PREFIXES, index):
            end = text.find("\n", index)
            end = size if end == -1 else end
            spans.append(_Span(index, end, "comments"))
            index = end
        elif text[index] in "'\"`":
            quote = text[index]
            end = index + 1
            while end < size:
                if text[end] == "\\":
                    end += 2
                elif end < size and text[end] == quote:
                    end += 1
                    break
                else:
                    end += 1
            spans.append(_Span(index, min(end, size), "strings"))
            index = end
        elif text[index].isidentifier() or text[index] == "_":
            end = index + 1
            while end < size and (text[end].isidentifier() or text[end].isdigit()):
                end += 1
            spans.append(_Span(index, end, "identifiers"))
            index = end
        else:
            index += 1
    return spans


def _tree_sitter_spans(text: str, language: str) -> Optional[tuple[list[_Span], bool]]:
    """Use tree-sitter-language-pack when installed, without requiring it."""
    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(language)
        tree = parser.parse(text)
    except Exception:
        return None

    byte_offsets = [0]
    for character in text:
        byte_offsets.append(byte_offsets[-1] + len(character.encode("utf-8")))

    def char_offset(byte_offset: int) -> int:
        # byte_offsets is monotonic and source ASTs tend to have few nodes.
        for number, value in enumerate(byte_offsets):
            if value >= byte_offset:
                return number
        return len(text)

    root = tree.root_node() if callable(tree.root_node) else tree.root_node
    spans: list[_Span] = []
    stack = [root]
    while stack:
        node = stack.pop()
        node_type = getattr(node, "type", None)
        if node_type is None:
            node_type = node.kind()
        node_type = node_type.lower()
        context = None
        if "comment" in node_type:
            context = "comments"
        elif "string" in node_type:
            context = "strings"
        elif node_type in {"identifier", "field_identifier", "type_identifier"}:
            context = "identifiers"
        if context:
            start_byte = (
                node.start_byte() if callable(node.start_byte) else node.start_byte
            )
            end_byte = node.end_byte() if callable(node.end_byte) else node.end_byte
            spans.append(_Span(char_offset(start_byte), char_offset(end_byte), context))
        children = getattr(node, "children", None)
        if children is None:
            count = node.child_count()
            children = [node.child(index) for index in range(count)]
        stack.extend(children)
    has_error = root.has_error() if callable(root.has_error) else root.has_error
    return spans, not has_error


def _context_at(index: int, spans: Iterable[_Span]) -> str:
    for span in spans:
        if span.start <= index < span.end:
            return span.context
    return "syntax"


def scan_source(
    text: str, language: Optional[str] = None, path: Optional[str] = None
) -> dict:
    """Inspect source without modifying it.

    Results distinguish comments, strings, identifiers, and unclassified syntax.
    ``parse_valid`` is ``None`` for generic fallback lexing, rather than an
    unsafe guess about a language we cannot parse.
    """
    source_language = _language(language, path)
    parser = "generic"
    parse_valid: Optional[bool] = None
    if source_language == "python":
        spans, parse_valid = _python_spans(text)
        parser = "python-tokenize"
    else:
        parsed = _tree_sitter_spans(text, source_language)
        if parsed is not None:
            spans, parse_valid = parsed
            parser = "tree-sitter"
        else:
            spans = _generic_spans(text)

    counts = {name: 0 for name in ("comments", "strings", "identifiers", "syntax")}
    regions = {name: 0 for name in counts}
    for span in spans:
        regions[span.context] += 1
    starts = _line_offsets(text)
    findings = []
    c2pa = _c2pa_ranges(text, 0)
    c2pa_starts = {start for start, _ in c2pa}
    c2pa_covered = {index for start, end in c2pa for index in range(start, end)}
    for index, character in enumerate(text):
        if index in c2pa_covered and index not in c2pa_starts:
            continue
        if not _is_hidden(character) and index not in c2pa_starts:
            continue
        width = next((end - start for start, end in c2pa if start == index), 1)
        context_index = index
        while context_index < index + width and text[context_index] in " \t":
            context_index += 1
        context = _context_at(context_index, spans)
        line, column = _position(starts, index)
        signal = "c2pa_text_carrier" if index in c2pa_starts else "hidden_unicode"
        counts[context] += width
        findings.append(
            {
                "category": (
                    "provenance" if signal.startswith("c2pa") else "unicode_security"
                ),
                "signal": signal,
                "context": context,
                "line": line,
                "column": column,
                "offset": index,
                "count": width,
                "code_point": (
                    None if signal.startswith("c2pa") else f"U+{ord(character):04X}"
                ),
                "name": (
                    "C2PA Text carrier"
                    if signal.startswith("c2pa")
                    else unicodedata.name(character, "UNNAMED")
                ),
                "removable": context == "comments",
                "planned_action": (
                    "remove_from_comment" if context == "comments" else "report_only"
                ),
            }
        )
    for span in spans:
        if span.context != "identifiers":
            continue
        value = text[span.start : span.end]
        analysis = analyze_confusable_token(value)
        if analysis is None:
            continue
        line, column = _position(starts, span.start)
        counts["identifiers"] += 1
        findings.append(
            {
                "category": "unicode_security",
                "signal": "confusable_mixed_script_identifier",
                "context": "identifiers",
                "line": line,
                "column": column,
                "offset": span.start,
                "count": 1,
                "code_point": None,
                "name": "Mixed-script confusable identifier",
                "removable": False,
                "planned_action": "report_only",
                "details": analysis,
            }
        )
    return {
        "language": source_language,
        "parser": parser,
        "parse_valid": parse_valid,
        "counts": counts,
        "regions": regions,
        "findings": findings,
    }


def clean_source_comments(
    text: str,
    language: Optional[str] = None,
    path: Optional[str] = None,
    *,
    strip_provenance: bool = False,
) -> str:
    """Remove recognized hidden Unicode/C2PA carriers from comments only.

    A Python file that does not parse before cleanup is returned unchanged: the
    module cannot make a safety claim about a transformation of invalid source.
    """
    report = scan_source(text, language, path)
    if report["parse_valid"] is False:
        return text
    ranges: list[tuple[int, int]] = []
    for finding in report["findings"]:
        if finding["context"] != "comments":
            continue
        if finding["signal"] == "c2pa_text_carrier":
            if not strip_provenance:
                continue
            ranges.append((finding["offset"], finding["offset"] + finding["count"]))
        else:
            ranges.append((finding["offset"], finding["offset"] + 1))
    result = text
    for start, end in sorted(set(ranges), reverse=True):
        result = result[:start] + result[end:]
    if report["language"] == "python":
        try:
            ast.parse(result)
        except (SyntaxError, ValueError, TypeError):
            return text
    elif report["parser"] == "tree-sitter":
        # Tree-sitter was available for the original source, so require it to
        # accept the transformed source as well.  Generic fallback deliberately
        # makes no syntactic-validity claim.
        after = scan_source(result, language, path)
        if after["parse_valid"] is not True:
            return text
    return result
