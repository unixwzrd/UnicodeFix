"""Local image auditing and built-in, lossless container metadata cleanup."""

from __future__ import annotations

import hashlib
import io
import os
import stat
import struct
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, UnidentifiedImageError

from unicodefix.image_container import (
    EXIF_RENDERING,
    EXIF_SUB_RENDERING,
    MAX_FILE_BYTES,
    Container,
    inspect_container,
)

SCHEMA_VERSION = "2.1"
WRITABLE_FORMATS = {"JPEG", "PNG", "WEBP"}
_RENDERING_TERMS = (
    "colorspace",
    "colorprofile",
    "icc_profile",
    "orientation",
    "photometricinterpretation",
    "transferfunction",
    "whitepoint",
    "ycbcrpositioning",
    "resolution",
    "chromaticities",
    "gamma",
    "transparency",
    "srgb",
)
_STRUCTURAL_TERMS = (
    "bitdepth",
    "bitspersample",
    "colorcomponents",
    "colortype",
    "compression",
    "duration",
    "encodingprocess",
    "filter",
    "framecount",
    "imagecount",
    "imageheight",
    "imagewidth",
    "interlace",
    "ycbcrsubsampling",
    "planarconfiguration",
    "rowsperstrip",
    "samplesperpixel",
    "stripbytecounts",
    "stripoffsets",
)
_LOCATION_TERMS = ("gps", "geotag", "location", "latitude", "longitude")
_IDENTITY_TERMS = (
    "artist",
    "author",
    "cameraowner",
    "copyright",
    "creator",
    "device",
    "email",
    "owner",
    "serialnumber",
)
_EDITING_TERMS = (
    "comment",
    "description",
    "history",
    "parameters",
    "prompt",
    "software",
    "workflow",
)


class ImageAuditError(RuntimeError):
    """Raised when an image cannot be audited or safely transformed."""


def _metadata_classes(tags: Sequence[str]) -> dict[str, list[str]]:
    classes: dict[str, list[str]] = {
        "location_metadata": [],
        "identity_or_device_metadata": [],
        "editing_metadata": [],
        "other_metadata": [],
    }
    for tag in tags:
        lowered = tag.lower().replace(" ", "")
        if any(term in lowered for term in (*_RENDERING_TERMS, *_STRUCTURAL_TERMS)):
            continue
        signal = "other_metadata"
        if any(term in lowered for term in _LOCATION_TERMS):
            signal = "location_metadata"
        elif any(term in lowered for term in _IDENTITY_TERMS):
            signal = "identity_or_device_metadata"
        elif any(term in lowered for term in _EDITING_TERMS):
            signal = "editing_metadata"
        classes[signal].append(tag)
    return classes


def _finding(
    category: str,
    signal: str,
    tags: Sequence[str],
    *,
    removable: bool,
    confidence: str = "high",
) -> dict[str, Any]:
    return {
        "category": category,
        "signal": signal,
        "count": len(tags),
        "locations": [],
        "confidence": confidence,
        "removable": removable,
        "planned_action": "report",
        "details": {"tags": list(tags)},
    }


def _read_image(path: Path) -> bytes:
    if not path.is_file():
        raise ImageAuditError(f"Image file not found: {path}")
    with path.open("rb") as handle:
        data = handle.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ImageAuditError("Image audit/cleanup is limited to 256 MiB per file")
    return data


def _format(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data.startswith(b"\xff\xd8"):
        return "JPEG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    if data.startswith((b"II*\0", b"MM\0*", b"II+\0", b"MM\0+")):
        return "TIFF"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    if data.startswith(b"BM"):
        return "BMP"
    if data[4:8] == b"ftyp":
        brands = [
            data[8:12],
            *(data[index : index + 4] for index in range(16, min(len(data), 64), 4)),
        ]
        if any(brand in {b"avif", b"avis"} for brand in brands):
            return "AVIF"
        if any(
            brand in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}
            for brand in brands
        ):
            return "HEIF"
    return None


def _pillow_tags(image: Image.Image) -> list[str]:
    tags = [f"EXIF:{ExifTags.TAGS.get(tag, hex(tag))}" for tag in image.getexif()]
    tags.extend(
        f"ImageInfo:{key}" for key in image.info if key not in {"exif", "icc_profile"}
    )
    return tags


def _audit(data: bytes) -> tuple[dict[str, Any], Container | None]:
    detected = _format(data)
    if detected is None:
        raise ImageAuditError("Not a supported or valid image")
    container = None
    try:
        if detected in WRITABLE_FORMATS:
            container = inspect_container(data)
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            description = {
                "format": image.format,
                "mime_type": Image.MIME.get(image.format or ""),
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "frames": getattr(image, "n_frames", 1),
                "animated": bool(getattr(image, "is_animated", False)),
            }
            fallback_tags = _pillow_tags(image) if container is None else []
    except UnidentifiedImageError as error:
        if detected not in {"HEIF", "AVIF"}:
            raise ImageAuditError("Not a supported or valid image") from error
        description = {
            "format": detected,
            "mime_type": "image/heif" if detected == "HEIF" else "image/avif",
            "width": None,
            "height": None,
            "mode": None,
            "frames": None,
            "animated": None,
        }
        fallback_tags = []
    except (
        OSError,
        ValueError,
        TypeError,
        SyntaxError,
        EOFError,
        OverflowError,
        struct.error,
        Image.DecompressionBombError,
    ) as error:
        raise ImageAuditError(f"Not a supported or valid image: {error}") from error
    blockers = container.blockers if container is not None else []
    supported = (
        container is not None
        and not blockers
        and description["format"] in WRITABLE_FORMATS
    )
    message = (
        None
        if supported
        else (
            "; ".join(blockers)
            if blockers
            else f"{detected} is audit-only; built-in cleanup supports PNG, JPEG and WebP"
        )
    )
    if description["width"] is None:
        message += "; decoder unavailable, header-only inventory is incomplete"
    findings = []
    for signal, tags in _metadata_classes(
        container.metadata if container is not None else fallback_tags
    ).items():
        if tags:
            findings.append(_finding("metadata", signal, tags, removable=supported))
    if container is not None:
        if container.provenance:
            findings.append(
                _finding(
                    "provenance",
                    "c2pa_or_jumbf_metadata",
                    [f"{detected}:carrier[{index}]" for index in container.provenance],
                    removable=supported,
                )
            )
        if container.references:
            findings.append(
                _finding(
                    "provenance",
                    "c2pa_reference_metadata",
                    container.references,
                    removable=supported,
                )
            )
        if container.malformed:
            findings.append(
                _finding(
                    "provenance",
                    "malformed_or_unrecognized_c2pa_carrier",
                    container.malformed,
                    removable=False,
                    confidence="low",
                )
            )
        if blockers:
            findings.append(
                _finding(
                    "metadata",
                    "unsupported_metadata_variant",
                    blockers,
                    removable=False,
                )
            )
    elif b"c2pa" in data.lower() and b"jumb" in data.lower():
        findings.append(
            _finding(
                "provenance",
                "possible_c2pa_container_bytes",
                [f"{detected}:unparsed_container"],
                removable=False,
                confidence="low",
            )
        )
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "image",
        "image": description,
        "backend": {
            "name": "builtin",
            "write_supported": supported,
            "metadata_source": (
                "container"
                if container is not None
                else "header" if description["width"] is None else "pillow"
            ),
            "message": message,
        },
        "findings": findings,
        "total": sum(item["count"] for item in findings),
        "pixel_watermarks": [
            {"scheme": "synthid", "status": "unsupported", "removable": False},
            {
                "scheme": "unknown_visible_or_pixel_watermark",
                "status": "unsupported",
                "removable": False,
            },
        ],
        "limitations": [
            "Metadata and C2PA provenance are not proof of AI generation.",
            "C2PA carriers are structurally recognized; signatures are not validated.",
            "Unknown container blocks are retained. No generic metadata-free or watermark-free claim is made.",
            "External manifests are never retrieved.",
        ],
    }
    if container is not None:
        report["preservation"] = {
            "protected_container_sha256": container.protected_digest(),
            "retained_metadata_sha256": container.retained_metadata_digest(),
            "encoded_payload_rewritten": False,
        }
    return report, container


def audit_image(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Inventory known local carriers; never invoke an external program."""
    report, _ = _audit(_read_image(Path(path)))
    return report


def _count(report: dict[str, Any], category: str, signal: str | None = None) -> int:
    return sum(
        int(item["count"])
        for item in report["findings"]
        if item["category"] == category and (signal is None or item["signal"] == signal)
    )


def plan_image_cleanup(
    report: dict[str, Any], *, strip_metadata: bool, strip_provenance: bool
) -> dict[str, Any]:
    actions = []
    if strip_metadata:
        actions.append("remove_non_rendering_metadata")
    if strip_provenance:
        actions.append("remove_c2pa_jumbf_provenance")
    message = report["backend"]["message"]
    if _count(report, "provenance", "malformed_or_unrecognized_c2pa_carrier"):
        message = (
            "Malformed or unrecognized provenance carrier retained; cleanup is refused"
        )
    elif strip_metadata and not strip_provenance and _count(report, "provenance"):
        message = "Metadata cleanup could invalidate C2PA provenance; add --strip-provenance explicitly"
    elif (
        strip_provenance
        and not strip_metadata
        and _count(report, "provenance", "c2pa_reference_metadata")
    ):
        message = (
            "C2PA reference metadata requires --strip-metadata with --strip-provenance"
        )
    return {
        "changed_expected": bool(
            (strip_metadata and _count(report, "metadata"))
            or (strip_provenance and _count(report, "provenance"))
        ),
        "actions": actions,
        "preserved": [
            "encoded image payload",
            "ICC profile",
            "orientation",
            "color-space tags",
            "animation frames and timing",
        ],
        "backend_ready": bool(report["backend"]["write_supported"] and not message),
        "backend_message": message,
    }


def _rendering_snapshot(data: bytes) -> dict[str, Any]:
    with Image.open(io.BytesIO(data)) as image:
        exif = image.getexif()
        sub = exif.get_ifd(34665) if 34665 in exif else {}
        return {
            "icc": hashlib.sha256(image.info.get("icc_profile", b"")).hexdigest(),
            "exif": {tag: repr(exif[tag]) for tag in EXIF_RENDERING & exif.keys()},
            "exif_color": {
                tag: repr(sub[tag]) for tag in EXIF_SUB_RENDERING & sub.keys()
            },
        }


def clean_image(
    source: str | os.PathLike[str],
    output: str | os.PathLike[str],
    *,
    strip_metadata: bool,
    strip_provenance: bool,
    force: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Strip selected container metadata and atomically publish verified output."""
    if not strip_metadata and not strip_provenance:
        raise ImageAuditError("Select --strip-metadata and/or --strip-provenance")
    source_path, output_path = Path(source), Path(output)
    if source_path.resolve() == output_path.resolve():
        raise ImageAuditError(
            "Input and output must differ; in-place image cleanup is not supported"
        )
    if output_path.suffix.lower() != source_path.suffix.lower():
        raise ImageAuditError("Output must keep the input image extension")
    if output_path.exists() and not force:
        raise ImageAuditError(f"Output already exists (use --force): {output_path}")
    if not output_path.parent.is_dir():
        raise ImageAuditError(f"Output directory does not exist: {output_path.parent}")
    data = _read_image(source_path)
    before, container = _audit(data)
    plan = plan_image_cleanup(
        before, strip_metadata=strip_metadata, strip_provenance=strip_provenance
    )
    if not plan["backend_ready"] or container is None:
        raise ImageAuditError(str(plan["backend_message"]))
    cleaned = container.rewrite(
        strip_metadata=strip_metadata, strip_provenance=strip_provenance
    )
    after, checked = _audit(cleaned)
    if (
        checked is None
        or container.protected_digest() != checked.protected_digest()
        or container.retained_metadata_digest() != checked.retained_metadata_digest()
        or _rendering_snapshot(data) != _rendering_snapshot(cleaned)
    ):
        raise ImageAuditError(
            "Image payload or rendering metadata changed; output refused"
        )
    if strip_provenance and _count(after, "provenance"):
        raise ImageAuditError("Recognized provenance remained after cleanup")
    if strip_metadata and _count(after, "metadata"):
        raise ImageAuditError("Recognized removable metadata remained after cleanup")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}.",
        suffix=output_path.suffix,
        dir=output_path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(cleaned)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(stat.S_IMODE(source_path.stat().st_mode))
        if force:
            os.replace(temporary, output_path)
        else:
            try:
                os.link(temporary, output_path)
            except FileExistsError as error:
                raise ImageAuditError(
                    f"Output already exists (use --force): {output_path}"
                ) from error
        return before, after
    finally:
        temporary.unlink(missing_ok=True)
