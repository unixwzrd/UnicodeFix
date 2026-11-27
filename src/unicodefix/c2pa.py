"""Offline recognition of C2PA text provenance carriers.

This module intentionally does not validate signatures or dereference URLs.
It recognizes explicit carriers so callers can inventory or explicitly remove
them without treating C2PA as evidence of AI authorship.
"""

from __future__ import annotations

import base64
import binascii
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from unicodefix.findings import Finding, Location

MAGIC = b"C2PATXT\0"
TEXT_WRAPPER_VERSION = 1
BEGIN_MARKER = "-----BEGIN C2PA MANIFEST-----"
END_MARKER = "-----END C2PA MANIFEST-----"
_SINGLE_LINE_RE = re.compile(
    rf"(?m)^[ \t]*(?:\#|//|--|;|%|/\*|<!--|!)[^\r\n]*?"
    rf"{re.escape(BEGIN_MARKER)}[ \t]+(?P<reference>.+?)[ \t]+"
    rf"{re.escape(END_MARKER)}[^\r\n]*(?:\r?\n|$)"
)
_MULTI_LINE_RE = re.compile(
    rf"(?m)^[ \t]*{re.escape(BEGIN_MARKER)}[ \t]*\r?\n"
    rf"(?P<reference>[^\r\n]+)\r?\n"
    rf"[ \t]*{re.escape(END_MARKER)}[ \t]*(?:\r?\n|$)"
)
_BEGIN_RE = re.compile(rf"(?m)^.*{re.escape(BEGIN_MARKER)}.*(?:\r?\n|$)")
_HTML_SPACE = " \t\n\r\f"
_HTML_START_RE = re.compile(
    r"<(?P<tag>script|link)(?=[ \t\n\r\f/>])", re.IGNORECASE | re.ASCII
)
_HTML_SCRIPT_END_RE = re.compile(r"</script[ \t\n\r\f]*>", re.IGNORECASE | re.ASCII)


@dataclass(frozen=True)
class Carrier:
    kind: str
    start: int
    end: int
    valid: bool
    payload: bytes | str | None = None
    message: str = ""


@dataclass(frozen=True)
class _HTMLTag:
    end: int
    attributes: dict[str, list[str]]
    complete: bool
    valid: bool
    self_closing: bool = False


def _location(text: str, start: int, end: int) -> Location:
    line = text.count("\n", 0, start) + 1
    line_start = text.rfind("\n", 0, start) + 1
    end_line = text.count("\n", 0, end) + 1
    end_line_start = text.rfind("\n", 0, end) + 1
    return Location(
        line, start - line_start + 1, end_line, end - end_line_start + 1, start, end
    )


def decode_variation_selectors(text: str, start: int = 0) -> tuple[bytes, int]:
    """Decode the standard 256-value variation-selector byte mapping.

    U+FE00..U+FE0F encode 0..15 and U+E0100..U+E01EF encode 16..255.
    The returned end position stops at the first non-selector character.
    """

    out = bytearray()
    pos = start
    while pos < len(text):
        point = ord(text[pos])
        if 0xFE00 <= point <= 0xFE0F:
            out.append(point - 0xFE00)
        elif 0xE0100 <= point <= 0xE01EF:
            out.append(point - 0xE0100 + 16)
        else:
            break
        pos += 1
    return bytes(out), pos


def encode_variation_selectors(payload: bytes) -> str:
    """Encode bytes for fixtures and local round-trip tests."""

    return "".join(
        chr(0xFE00 + byte) if byte < 16 else chr(0xE0100 + byte - 16)
        for byte in payload
    )


def build_text_wrapper(manifest: bytes, version: int = TEXT_WRAPPER_VERSION) -> bytes:
    """Build the byte wrapper defined by C2PA 2.4 for local fixtures."""

    if not 0 <= version <= 255:
        raise ValueError("C2PA text-wrapper version must fit in one byte")
    return MAGIC + bytes((version,)) + len(manifest).to_bytes(4, "big") + manifest


def validate_text_wrapper(payload: bytes) -> tuple[bool, str]:
    """Validate the public C2PA text-wrapper header and declared length.

    This validates carrier structure, not the embedded JUMBF manifest's
    signature or trust chain.
    """

    if not payload.startswith(MAGIC):
        return False, "not a C2PA text wrapper"
    if len(payload) < 13:
        return False, "truncated C2PA text-wrapper header"
    version = payload[8]
    if version != TEXT_WRAPPER_VERSION:
        return False, f"unsupported C2PA text-wrapper version {version}"
    declared_length = int.from_bytes(payload[9:13], "big")
    actual_length = len(payload) - 13
    if actual_length != declared_length:
        return (
            False,
            (
                "C2PA text-wrapper manifest length mismatch "
                f"(declared {declared_length}, found {actual_length})"
            ),
        )
    return True, "complete C2PA text wrapper"


def _structured_reference(reference: str) -> tuple[bool, str, str]:
    value = reference.strip()
    data_prefix = "data:application/c2pa;base64,"
    if value.startswith(data_prefix):
        encoded = value[len(data_prefix) :]
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            return False, "structured_block", "invalid C2PA data URI"
        if not decoded:
            return False, "structured_block", "empty C2PA data URI"
        return True, "structured_embedded", "complete embedded C2PA reference"
    parsed = urlsplit(value)
    if parsed.scheme and not any(character.isspace() for character in value):
        return (
            True,
            "structured_external_reference",
            "complete external C2PA reference; URL was not retrieved",
        )
    return False, "structured_block", "invalid or empty C2PA manifest reference"


def _base64_payload(payload: str) -> bool:
    encoded = "".join(payload.split())
    if not encoded:
        return False
    try:
        return bool(base64.b64decode(encoded, validate=True))
    except (binascii.Error, ValueError):
        return False


def _html_start_tag(text: str, index: int) -> _HTMLTag:
    """Read attributes once, returning the next unconsumed offset.

    Only attributes used by C2PA are retained. Quotes may contain angle brackets;
    an unquoted '<' instead ends this malformed candidate so scanning can resume
    there. An unterminated quote consumes the remaining input exactly once.
    """

    attributes: dict[str, list[str]] = {}
    valid = True
    size = len(text)
    while index < size:
        space_start = index
        while index < size and text[index] in _HTML_SPACE:
            index += 1
        if index == size:
            break
        if text[index] == ">":
            return _HTMLTag(index + 1, attributes, True, valid)
        if text.startswith("/>", index):
            return _HTMLTag(index + 2, attributes, True, valid, True)
        if text[index] == "<":
            return _HTMLTag(index, attributes, False, False)
        if index == space_start:
            valid = False  # Attributes must be separated by HTML whitespace.
        start = index
        while index < size and text[index] not in _HTML_SPACE + "=<>/\"'`":
            index += 1
        name = text[start:index].lower()
        if index == start:
            valid = False
            index += 1
            continue
        after_name = index
        while index < size and text[index] in _HTML_SPACE:
            index += 1
        value = ""
        if index < size and text[index] == "=":
            index += 1
            while index < size and text[index] in _HTML_SPACE:
                index += 1
            if index == size:
                break
            if text[index] in "\"'":
                quote = text[index]
                start = index + 1
                end = text.find(quote, start)
                if end < 0:
                    return _HTMLTag(size, attributes, False, False)
                index = end + 1
            else:
                start = index
                while index < size and text[index] not in _HTML_SPACE + "<>":
                    if text[index] in "\"'`=":
                        valid = False
                    index += 1
                end = index
                if end == start:
                    valid = False
            if name in {"type", "rel", "href"}:
                value = text[start:end]
        else:
            # Leave separators for the next attribute, including after booleans.
            index = after_name
        if name in {"type", "rel", "href"}:
            values = attributes.setdefault(name, [])
            if values:
                valid = False  # Duplicate relevant attributes are ambiguous.
            values.append(value)
    return _HTMLTag(size, attributes, False, False)


def _html_carriers(text: str) -> list[Carrier]:
    """Find HTML carriers without retrying scans over overlapping suffixes.

    This recognizes carrier fragments, not a full HTML document. The start/end
    searches contain only fixed prefixes and disjoint whitespace runs; all tag
    parsing advances monotonically, including on malformed or incomplete input.
    """

    carriers: list[Carrier] = []
    index = 0
    while match := _HTML_START_RE.search(text, index):
        tag = _html_start_tag(text, match.end())
        end, attributes = tag.end, tag.attributes
        index = end
        if match.group("tag").lower() == "script":
            is_c2pa = any(
                value.lower() == "application/c2pa"
                for value in attributes.get("type", [])
            )
            complete = tag.valid and tag.complete and not tag.self_closing
            payload_end = end
            if tag.complete:
                closing = _HTML_SCRIPT_END_RE.search(text, end)
                if closing is None:
                    index = len(text)
                    complete = False
                else:
                    payload_end = closing.start()
                    index = closing.end()
            if is_c2pa:
                valid = complete and _base64_payload(text[end:payload_end])
                carriers.append(
                    Carrier(
                        "html_inline",
                        match.start(),
                        index,
                        valid,
                        text[match.start() : index],
                        (
                            "complete inline HTML C2PA manifest carrier"
                            if valid
                            else "incomplete, ambiguous, or invalid inline HTML C2PA carrier"
                        ),
                    )
                )
        elif any(
            "c2pa-manifest" in value.lower().split()
            for value in attributes.get("rel", [])
        ):
            href = attributes.get("href", [""])[0]
            try:
                valid = (
                    tag.complete
                    and tag.valid
                    and bool(urlsplit(href).scheme)
                    and not any(character.isspace() for character in href)
                )
            except ValueError:
                valid = False
            carriers.append(
                Carrier(
                    "html_external_reference",
                    match.start(),
                    end,
                    valid,
                    text[match.start() : end],
                    (
                        "HTML C2PA external manifest reference; URL was not retrieved"
                        if valid
                        else "incomplete, ambiguous, or invalid HTML C2PA manifest link"
                    ),
                )
            )
    return carriers


def find_c2pa_carriers(text: str) -> list[Carrier]:
    carriers: list[Carrier] = []
    index = 0
    while True:
        start = text.find("\ufeff", index)
        if start < 0:
            break
        payload, end = decode_variation_selectors(text, start + 1)
        if payload.startswith(MAGIC):
            valid, message = validate_text_wrapper(payload)
            carriers.append(
                Carrier(
                    "variation_selector",
                    start,
                    end,
                    valid,
                    payload,
                    message,
                )
            )
        index = start + 1

    for pattern in (_SINGLE_LINE_RE, _MULTI_LINE_RE):
        for match in pattern.finditer(text):
            valid, kind, message = _structured_reference(match.group("reference"))
            carriers.append(
                Carrier(
                    kind,
                    match.start(),
                    match.end(),
                    valid,
                    match.group(0),
                    message,
                )
            )
    for match in _BEGIN_RE.finditer(text):
        if not any(
            start <= match.start() < end
            for start, end in (
                (c.start, c.end) for c in carriers if c.kind.startswith("structured")
            )
        ):
            carriers.append(
                Carrier(
                    "structured_block",
                    match.start(),
                    match.end(),
                    False,
                    match.group(0),
                    "C2PA begin marker without complete end marker",
                )
            )

    carriers.extend(_html_carriers(text))
    return sorted(carriers, key=lambda carrier: carrier.start)


def c2pa_findings(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for carrier in find_c2pa_carriers(text):
        findings.append(
            Finding(
                category="provenance",
                signal=f"c2pa_{carrier.kind}_{'valid' if carrier.valid else 'malformed'}",
                locations=(_location(text, carrier.start, carrier.end),),
                confidence="high" if carrier.valid else "medium",
                removable=carrier.valid,
                planned_action="strip_provenance" if carrier.valid else "report",
                message=carrier.message + "; provenance is not proof of AI generation.",
                scheme="C2PA",
            )
        )
    return findings


def strip_c2pa_carriers(text: str) -> str:
    """Remove only complete, recognized C2PA carriers; leave malformed data intact."""

    carriers = [carrier for carrier in find_c2pa_carriers(text) if carrier.valid]
    for carrier in reversed(carriers):
        text = text[: carrier.start] + text[carrier.end :]
    return text
