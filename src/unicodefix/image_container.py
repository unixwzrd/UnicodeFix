"""Bounded PNG/JPEG/WebP metadata edits without decoding or encoding pixels.

Container framing follows W3C PNG 3, the WebP RIFF specification and the
C2PA 2.4 embedding rules. Pillow is used only to parse/serialize EXIF.
"""

from __future__ import annotations

import hashlib
import struct
import warnings
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field

from PIL import ExifTags, Image

MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_METADATA_BYTES = 4 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
C2PA_UUID = bytes.fromhex("6332706100110010800000aa00389b71")
XMP_SIGNATURE = b"http://ns.adobe.com/xap/1.0/\0"
EXIF_RENDERING = {274, 282, 283, 296, 301, 318, 319, 529, 530, 531, 532, 34675}
EXIF_SUB_RENDERING = {40961, 42240}
XMP_RENDERING = {
    f"{{{namespace}}}{name}"
    for namespace, names in (
        (
            "http://ns.adobe.com/tiff/1.0/",
            (
                "Orientation",
                "XResolution",
                "YResolution",
                "ResolutionUnit",
                "WhitePoint",
                "PrimaryChromaticities",
                "YCbCrCoefficients",
                "YCbCrPositioning",
                "ReferenceBlackWhite",
            ),
        ),
        ("http://ns.adobe.com/exif/1.0/", ("ColorSpace", "Gamma")),
    )
    for name in names
}


class ContainerError(ValueError):
    """Malformed container or metadata that cannot safely be rewritten."""


@dataclass(frozen=True)
class Block:
    kind: bytes
    raw: bytes
    payload: bytes


def _png_block(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload))
    )


def _webp_block(kind: bytes, payload: bytes) -> bytes:
    return (
        kind
        + struct.pack("<I", len(payload))
        + payload
        + (b"\0" if len(payload) % 2 else b"")
    )


def _jpeg_block(kind: bytes, payload: bytes) -> bytes:
    if len(payload) > 65533:
        raise ContainerError("Rewritten JPEG metadata exceeds the segment limit")
    return kind + struct.pack(">H", len(payload) + 2) + payload


def _png(data: bytes) -> list[Block]:
    blocks = []
    offset = 8
    while offset < len(data):
        if offset + 12 > len(data):
            raise ContainerError("Truncated PNG chunk")
        length = int.from_bytes(data[offset : offset + 4], "big")
        end = offset + 12 + length
        if length > 0x7FFFFFFF or end > len(data):
            raise ContainerError("Invalid PNG chunk length")
        raw = data[offset:end]
        kind = raw[4:8]
        if not all(65 <= byte <= 90 or 97 <= byte <= 122 for byte in kind):
            raise ContainerError("Invalid PNG chunk type")
        if zlib.crc32(raw[4:-4]) != int.from_bytes(raw[-4:], "big"):
            raise ContainerError("PNG chunk CRC mismatch")
        blocks.append(Block(kind, raw, raw[8:-4]))
        offset = end
        if kind == b"IEND":
            if length or offset != len(data):
                raise ContainerError("PNG has invalid IEND or trailing bytes")
            break
    if (
        not blocks
        or blocks[0].kind != b"IHDR"
        or len(blocks[0].payload) != 13
        or blocks[-1].kind != b"IEND"
    ):
        raise ContainerError("PNG is missing its structural chunks")
    if sum(b.kind == b"IHDR" for b in blocks) != 1 or not any(
        b.kind == b"IDAT" for b in blocks
    ):
        raise ContainerError("PNG has invalid image structure")
    return blocks


def _webp(data: bytes) -> list[Block]:
    if len(data) < 12 or int.from_bytes(data[4:8], "little") + 8 != len(data):
        raise ContainerError("WebP RIFF size mismatch or trailing bytes")
    blocks = []
    offset = 12
    while offset < len(data):
        if offset + 8 > len(data):
            raise ContainerError("Truncated WebP chunk")
        length = int.from_bytes(data[offset + 4 : offset + 8], "little")
        end = offset + 8 + length + length % 2
        if end > len(data):
            raise ContainerError("Invalid WebP chunk length")
        if length % 2 and data[end - 1] != 0:
            raise ContainerError("Nonzero WebP chunk padding")
        kind = data[offset : offset + 4]
        payload = data[offset + 8 : offset + 8 + length]
        if kind == b"VP8X" and (len(payload) != 10 or blocks):
            raise ContainerError("Invalid WebP extended header")
        blocks.append(Block(kind, data[offset:end], payload))
        offset = end
    if not any(b.kind in {b"VP8 ", b"VP8L", b"ANMF"} for b in blocks):
        raise ContainerError("WebP has no image payload")
    return blocks


def _jpeg(data: bytes) -> list[Block]:
    blocks = []
    offset = 2
    while offset < len(data):
        start = offset
        if data[offset] != 255:
            raise ContainerError("JPEG marker expected")
        while offset < len(data) and data[offset] == 255:
            offset += 1
        if offset >= len(data):
            raise ContainerError("Truncated JPEG marker")
        marker = data[offset]
        kind = bytes((255, marker))
        offset += 1
        if marker == 217:
            if offset != len(data):
                raise ContainerError("JPEG has trailing bytes or multiple images")
            blocks.append(Block(kind, data[start:offset], b""))
            return blocks
        if marker == 1:
            blocks.append(Block(kind, data[start:offset], b""))
            continue
        if marker in {0, 216} or 208 <= marker <= 215 or offset + 2 > len(data):
            raise ContainerError("Invalid JPEG marker")
        length = int.from_bytes(data[offset : offset + 2], "big")
        end = offset + length
        if length < 2 or end > len(data):
            raise ContainerError("Invalid JPEG segment length")
        blocks.append(Block(kind, data[start:end], data[offset + 2 : end]))
        offset = end
        if marker == 218:
            scan_start = offset
            while offset < len(data):
                found = data.find(b"\xff", offset)
                if found < 0:
                    raise ContainerError("JPEG scan has no terminating marker")
                following = found + 1
                while following < len(data) and data[following] == 255:
                    following += 1
                if following >= len(data):
                    raise ContainerError("Truncated JPEG scan marker")
                if data[following] == 0 or 208 <= data[following] <= 215:
                    offset = following + 1
                    continue
                offset = found
                break
            blocks.append(
                Block(b"SCAN", data[scan_start:offset], data[scan_start:offset])
            )
    raise ContainerError("JPEG is missing its end marker")


def _boxes(data: bytes) -> list[tuple[bytes, bytes]]:
    result = []
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data) or len(result) > 100000:
            raise ContainerError("Malformed JUMBF box framing")
        length = int.from_bytes(data[offset : offset + 4], "big")
        header = 8
        if length == 1:
            if offset + 16 > len(data):
                raise ContainerError("Truncated JUMBF extended length")
            length = int.from_bytes(data[offset + 8 : offset + 16], "big")
            header = 16
        elif length == 0:
            length = len(data) - offset
        if length < header or offset + length > len(data):
            raise ContainerError("Invalid JUMBF box length")
        result.append(
            (data[offset + 4 : offset + 8], data[offset + header : offset + length])
        )
        offset += length
    return result


def _c2pa(data: bytes) -> bool:
    root = _boxes(data)
    if len(root) != 1 or root[0][0] != b"jumb":
        return False
    children = _boxes(root[0][1])
    if len(children) < 2 or children[0][0] != b"jumd":
        return False
    description = children[0][1]
    return (
        len(description) >= 22
        and description[:16] == C2PA_UUID
        and bool(description[16] & 2)
        and description[17:].split(b"\0", 1)[0] == b"c2pa"
    )


def _exif(payload: bytes) -> tuple[bytes | None, list[str]]:
    if len(payload) > MAX_METADATA_BYTES:
        raise ContainerError("Oversized EXIF metadata")
    prefix = payload.startswith(b"Exif\0\0")
    body = payload[6:] if prefix else payload
    if len(body) < 8 or body[:4] not in {b"II*\0", b"MM\0*"}:
        raise ContainerError("Unsupported or malformed EXIF TIFF header")
    with warnings.catch_warnings(record=True) as issues:
        warnings.simplefilter("always")
        original = Image.Exif()
        original.load(b"Exif\0\0" + body)
        values = dict(original)
        sub = original.get_ifd(34665) if 34665 in values else {}
        gps = original.get_ifd(34853) if 34853 in values else {}
        if 52545 in values or 52545 in sub:
            raise ContainerError("Nested EXIF JUMBF is audit-only in this writer")
        # Resolve nested directories now, so malformed pointers cannot be silently dropped.
        if 40965 in sub:
            original.get_ifd(40965)
        if issues:
            raise ContainerError("Malformed EXIF metadata cannot be safely rewritten")
    removed = [
        f"EXIF:{ExifTags.TAGS.get(tag, hex(tag))}"
        for tag in values
        if tag not in EXIF_RENDERING and tag not in {34665, 34853}
    ]
    removed.extend(
        f"EXIF:{ExifTags.TAGS.get(tag, hex(tag))}"
        for tag in sub
        if tag not in EXIF_SUB_RENDERING
    )
    removed.extend(f"EXIF:GPS{ExifTags.GPSTAGS.get(tag, hex(tag))}" for tag in gps)
    endian = "little" if body[:2] == b"II" else "big"
    ifd = int.from_bytes(body[4:8], endian)
    if ifd + 2 > len(body):
        raise ContainerError("Invalid EXIF directory offset")
    count = int.from_bytes(body[ifd : ifd + 2], endian)
    pointer = ifd + 2 + count * 12
    if pointer + 4 > len(body):
        raise ContainerError("Truncated EXIF directory")
    if int.from_bytes(body[pointer : pointer + 4], endian):
        removed.append("EXIF:ThumbnailDirectory")
    if 34853 in values and not gps:
        removed.append("EXIF:GPSInfo")
    if not removed:
        return payload, []
    kept = Image.Exif()
    for tag in EXIF_RENDERING & values.keys():
        if tag == 274 and values[tag] not in range(1, 9):
            raise ContainerError("Invalid EXIF orientation")
        kept[tag] = values[tag]
    kept_sub = {tag: sub[tag] for tag in EXIF_SUB_RENDERING & sub.keys()}
    if kept_sub:
        kept[34665] = kept_sub
    if not kept:
        return None, removed
    result = kept.tobytes()
    return (result if prefix else result[6:]), removed


def _xmp_reference(key: str, value: str) -> bool:
    return bool(value.strip()) and (
        key == "{http://purl.org/dc/terms/}provenance"
        or "c2pa" in key.lower()
        or value.strip().lower().startswith("self#jumbf=")
    )


def _xmp(payload: bytes) -> tuple[bytes | None, list[str], bool]:
    if b"\0" in payload:
        raise ContainerError("Only UTF-8 XMP packets are supported")
    if (
        len(payload) > MAX_METADATA_BYTES
        or b"<!DOCTYPE" in payload.upper()
        or b"<!ENTITY" in payload.upper()
    ):
        raise ContainerError("Unsafe or oversized XMP metadata")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ContainerError("Malformed XMP metadata") from error
    rendered = []
    private = False
    reference = False
    for node in root.iter():
        if "gainmap" in node.tag.lower() or "hdr-gain-map" in node.tag.lower():
            raise ContainerError(
                "HDR gain-map XMP requires a format-specific preservation policy"
            )
        for key, value in node.attrib.items():
            if "gainmap" in key.lower() or "hdr-gain-map" in key.lower():
                raise ContainerError(
                    "HDR gain-map XMP requires a format-specific preservation policy"
                )
            if key in XMP_RENDERING:
                rendered.append((key, value))
            elif not key.endswith("}about"):
                private = True
            reference |= _xmp_reference(key, value)
        if node.tag in XMP_RENDERING:
            if list(node):
                raise ContainerError(
                    "Structured XMP rendering fields are not yet supported"
                )
            rendered.append((node.tag, node.text or ""))
        elif node.text and node.text.strip():
            private = True
        if node.text:
            reference |= _xmp_reference(node.tag, node.text)
    if not private and not reference:
        return payload, [], False
    if not rendered:
        return None, ["XMP:packet"], reference
    rdf = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    output = ET.Element("{adobe:ns:meta/}xmpmeta")
    description = ET.SubElement(
        ET.SubElement(output, f"{{{rdf}}}RDF"), f"{{{rdf}}}Description"
    )
    for key, value in rendered:
        if key in description.attrib and description.attrib[key] != value:
            raise ContainerError("Conflicting XMP rendering values")
        description.set(key, value)
    return ET.tostring(output, encoding="utf-8"), ["XMP:packet"], reference


def _inflate(payload: bytes) -> bytes:
    decoder = zlib.decompressobj()
    data = decoder.decompress(payload, MAX_METADATA_BYTES + 1)
    if len(data) > MAX_METADATA_BYTES or not decoder.eof or decoder.unused_data:
        raise ContainerError("Oversized or malformed compressed PNG metadata")
    return data


def _png_text(block: Block) -> tuple[bytes | None, list[str], bool]:
    key, separator, rest = block.payload.partition(b"\0")
    if not separator or not 1 <= len(key) <= 79:
        raise ContainerError("Malformed PNG text keyword")
    if block.kind == b"zTXt":
        if rest[:1] != b"\0":
            raise ContainerError("Invalid PNG text compression")
        text = _inflate(rest[1:])
    elif block.kind == b"iTXt":
        if len(rest) < 4 or rest[0] not in {0, 1} or rest[1] != 0:
            raise ContainerError("Malformed PNG international text")
        language, null, remaining = rest[2:].partition(b"\0")
        translated, null2, text = remaining.partition(b"\0")
        if not null or not null2:
            raise ContainerError("Malformed PNG international text fields")
        if rest[0]:
            text = _inflate(text)
    else:
        text = rest
    if len(text) > MAX_METADATA_BYTES:
        raise ContainerError("Oversized PNG text metadata")
    if key == b"XML:com.adobe.xmp":
        changed, tags, reference = _xmp(text)
        if not tags:
            return block.payload, [], reference
        if changed is None:
            return None, tags, reference
        if block.kind != b"iTXt":
            raise ContainerError(
                "XMP rendering metadata in a non-iTXt PNG chunk is not supported"
            )
        return (
            key + b"\0\0\0" + language + b"\0" + translated + b"\0" + changed,
            tags,
            reference,
        )
    return None, ["PNG:" + key.decode("latin-1")], False


def _photoshop(payload: bytes) -> tuple[bytes | None, list[str]]:
    offset = 14
    keep = []
    removed = []
    # Known descriptive resources; unrecognized resources are kept verbatim.
    private = {1008, 1028, 1033, 1034, 1035, 1036, 1058, 1059, 1060, 1061}
    while offset < len(payload):
        start = offset
        if payload[offset : offset + 4] != b"8BIM" or offset + 7 > len(payload):
            raise ContainerError("Unsupported Photoshop resource framing")
        resource = int.from_bytes(payload[offset + 4 : offset + 6], "big")
        name_length = payload[offset + 6] + 1
        offset += 6 + name_length + name_length % 2
        if offset + 4 > len(payload):
            raise ContainerError("Truncated Photoshop resource")
        length = int.from_bytes(payload[offset : offset + 4], "big")
        offset += 4 + length + length % 2
        if offset > len(payload):
            raise ContainerError("Invalid Photoshop resource length")
        if resource in {1058, 1059, 1060}:
            raise ContainerError("Nested EXIF/XMP in Photoshop resources is audit-only")
        if resource in private:
            removed.append(f"IPTC:PhotoshopResource{resource}")
        else:
            keep.append(payload[start:offset])
    return (payload[:14] + b"".join(keep) if keep else None), removed


@dataclass
class Container:
    format: str
    blocks: list[Block]
    edits: dict[int, bytes | None] = field(default_factory=dict)
    metadata: list[str] = field(default_factory=list)
    provenance: list[int] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    metadata_blocks: set[int] = field(default_factory=set)

    def rewrite(self, *, strip_metadata: bool, strip_provenance: bool) -> bytes:
        output = []
        remaining = []
        for index, block in enumerate(self.blocks):
            raw = block.raw
            if strip_provenance and index in self.provenance:
                continue
            if strip_metadata and index in self.edits:
                raw = self.edits[index]
            if raw is not None:
                output.append(raw)
                remaining.append(block.kind)
        if self.format == "WEBP":
            for index, kind in enumerate(remaining):
                if kind == b"VP8X":
                    raw = bytearray(output[index])
                    raw[8] = (
                        (raw[8] & ~12)
                        | (8 if b"EXIF" in remaining else 0)
                        | (4 if b"XMP " in remaining else 0)
                    )
                    output[index] = bytes(raw)
            body = b"WEBP" + b"".join(output)
            return b"RIFF" + struct.pack("<I", len(body)) + body
        prefix = PNG_SIGNATURE if self.format == "PNG" else b"\xff\xd8"
        return prefix + b"".join(output)

    def protected_digest(self) -> str:
        digest = hashlib.sha256()
        for index, block in enumerate(self.blocks):
            if index in self.metadata_blocks or index in self.provenance:
                continue
            raw = block.raw
            if block.kind == b"VP8X":
                adjusted = bytearray(raw)
                adjusted[8] &= ~12
                raw = bytes(adjusted)
            digest.update(len(raw).to_bytes(8, "big"))
            digest.update(raw)
        return digest.hexdigest()

    def retained_metadata_digest(self) -> str:
        """Fingerprint the metadata projection that the cleanup must preserve."""
        digest = hashlib.sha256()
        for index, block in enumerate(self.blocks):
            if index not in self.metadata_blocks:
                continue
            raw = self.edits.get(index, block.raw)
            if raw is not None:
                digest.update(len(raw).to_bytes(8, "big"))
                digest.update(raw)
        return digest.hexdigest()


def inspect_container(data: bytes) -> Container:
    if len(data) > MAX_FILE_BYTES:
        raise ContainerError("Native image cleanup is limited to 256 MiB per file")
    if data.startswith(PNG_SIGNATURE):
        container = Container("PNG", _png(data))
        pack = _png_block
    elif data.startswith(b"\xff\xd8"):
        container = Container("JPEG", _jpeg(data))
        pack = _jpeg_block
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        container = Container("WEBP", _webp(data))
        pack = _webp_block
    else:
        raise ContainerError("No built-in writer for this image format")
    jpeg_jumbf: dict[bytes, list[tuple[int, bytes]]] = {}
    for index, block in enumerate(container.blocks):
        kind, payload = block.kind, block.payload
        if (
            kind
            in {
                b"eXIf",
                b"EXIF",
                b"XMP ",
                b"tEXt",
                b"zTXt",
                b"iTXt",
                b"tIME",
                b"\xff\xfe",
            }
            or kind == b"\xff\xe1"
            and payload.startswith((b"Exif\0\0", XMP_SIGNATURE))
            or kind == b"\xff\xed"
            and payload.startswith(b"Photoshop 3.0\0")
        ):
            container.metadata_blocks.add(index)
        if kind == b"\xff\xe2" and payload.startswith(b"MPF\0"):
            container.blockers.append("MPO/multi-picture JPEG is audit-only")
        if kind == b"\xff\xeb" and payload.startswith(b"JP"):
            jpeg_jumbf.setdefault(payload[2:4], []).append((index, payload))
            continue
        if kind in {b"caBX", b"C2PA"}:
            try:
                if not _c2pa(payload):
                    raise ContainerError("Unrecognized JUMBF content")
                container.provenance.append(index)
            except ContainerError:
                container.malformed.append(f"{container.format}:{kind.decode('ascii')}")
            continue
        try:
            changed = payload
            tags: list[str] = []
            reference = False
            if (
                kind in {b"eXIf", b"EXIF"}
                or kind == b"\xff\xe1"
                and payload.startswith(b"Exif\0\0")
            ):
                changed, tags = _exif(payload)
            elif (
                kind == b"XMP "
                or kind == b"\xff\xe1"
                and payload.startswith(XMP_SIGNATURE)
            ):
                prefix = XMP_SIGNATURE if kind == b"\xff\xe1" else b""
                changed, tags, reference = _xmp(payload[len(prefix) :])
                if changed is not None:
                    changed = prefix + changed
            elif container.format == "PNG" and kind in {b"tEXt", b"zTXt", b"iTXt"}:
                changed, tags, reference = _png_text(block)
            elif container.format == "PNG" and kind == b"tIME":
                changed, tags = None, ["PNG:ModificationTime"]
            elif kind == b"\xff\xfe":
                changed, tags = None, ["JPEG:Comment"]
            elif kind == b"\xff\xed" and payload.startswith(b"Photoshop 3.0\0"):
                changed, tags = _photoshop(payload)
            elif kind == b"\xff\xe1" and payload.startswith(
                b"http://ns.adobe.com/xmp/extension/\0"
            ):
                raise ContainerError("Extended XMP is audit-only in this writer")
            if tags:
                container.metadata.extend(tags)
                container.edits[index] = (
                    None if changed is None else pack(kind, changed)
                )
            if reference:
                container.references.append(
                    f"{container.format}:XMP:provenance_reference"
                )
        except (
            ContainerError,
            OSError,
            ValueError,
            TypeError,
            SyntaxError,
            struct.error,
            zlib.error,
            OverflowError,
            EOFError,
            KeyError,
            IndexError,
        ) as error:
            container.blockers.append(f"{container.format}:{kind.hex()}: {error}")
    for instance, fragments in jpeg_jumbf.items():
        try:
            first = fragments[0][1]
            header = first[8:16]
            if (
                len(first) < 16
                or header[4:] != b"jumb"
                or int.from_bytes(header[:4], "big") in {0, 1}
            ):
                raise ContainerError("Unsupported JPEG JUMBF header")
            pieces = []
            previous = fragments[0][0] - 1
            for sequence, (index, payload) in enumerate(fragments, 1):
                if (
                    len(payload) < 16
                    or index != previous + 1
                    or int.from_bytes(payload[4:8], "big") != sequence
                    or payload[8:16] != header
                ):
                    raise ContainerError("Incomplete or unordered JPEG JUMBF sequence")
                pieces.append(payload[8:] if sequence == 1 else payload[16:])
                previous = index
            store = b"".join(pieces)
            if _c2pa(store):
                container.provenance.extend(index for index, _ in fragments)
        except ContainerError:
            container.malformed.append(f"JPEG:APP11:{instance.hex()}")
    return container
