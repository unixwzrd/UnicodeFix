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
_HTML_INLINE_RE = re.compile(
    r"<script\b(?=[^>]*\btype\s*=\s*(['\"])application/c2pa\1)[^>]*>"
    r"(?P<payload>.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_EXTERNAL_RE = re.compile(
    r"<link\b(?=[^>]*\brel\s*=\s*(['\"])[^'\"]*\bc2pa-manifest\b[^'\"]*\1)" r"[^>]*>",
    re.IGNORECASE,
)
_HREF_RE = re.compile(r"\bhref\s*=\s*(['\"])(?P<href>.*?)\1", re.IGNORECASE)


@dataclass(frozen=True)
class Carrier:
    kind: str
    start: int
    end: int
    valid: bool
    payload: bytes | str | None = None
    message: str = ""


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

    for match in _HTML_INLINE_RE.finditer(text):
        valid = _base64_payload(match.group("payload"))
        carriers.append(
            Carrier(
                "html_inline",
                match.start(),
                match.end(),
                valid,
                match.group(0),
                (
                    "complete inline HTML C2PA manifest carrier"
                    if valid
                    else "invalid or empty inline HTML C2PA Base64 payload"
                ),
            )
        )
    for match in _HTML_EXTERNAL_RE.finditer(text):
        href_match = _HREF_RE.search(match.group(0))
        href = href_match.group("href") if href_match else ""
        valid = bool(urlsplit(href).scheme) and not any(
            character.isspace() for character in href
        )
        carriers.append(
            Carrier(
                "html_external_reference",
                match.start(),
                match.end(),
                valid,
                match.group(0),
                (
                    "HTML C2PA external manifest reference; URL was not retrieved"
                    if valid
                    else "HTML C2PA manifest link has no valid href URI"
                ),
            )
        )
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
