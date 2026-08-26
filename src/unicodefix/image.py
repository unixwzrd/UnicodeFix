"""Local image metadata and provenance auditing with conservative cleanup."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, UnidentifiedImageError

SCHEMA_VERSION = "2.0.1"
MINIMUM_WRITE_EXIFTOOL = (12, 70)
WRITABLE_SUFFIXES = {
    ".avif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}

_TECHNICAL_GROUPS = {"composite", "exiftool", "file", "system"}
_RENDERING_TERMS = (
    "colorspace",
    "colorprofile",
    "icc_profile",
    "orientation",
    "photometricinterpretation",
    "transferfunction",
    "whitepoint",
    "ycbcrpositioning",
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


def _version_tuple(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    try:
        return tuple(int(part) for part in value.strip().split("."))
    except ValueError:
        return ()


def _run_exiftool(
    executable: str, arguments: Sequence[str], *, check: bool = True
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [executable, *arguments],
            check=check,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise ImageAuditError(f"ExifTool executable not found: {executable}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ImageAuditError("ExifTool timed out") from exc
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        raise ImageAuditError(f"ExifTool failed: {message}") from exc


def exiftool_status(executable: str = "exiftool") -> dict[str, Any]:
    path = (
        shutil.which(executable)
        if os.path.basename(executable) == executable
        else executable
    )
    if not path or not os.path.isfile(path):
        return {
            "available": False,
            "path": None,
            "version": None,
            "write_supported": False,
            "message": "Install ExifTool 12.70 or newer for lossless metadata and C2PA cleanup.",
        }
    try:
        result = _run_exiftool(path, ["-ver"])
    except (ImageAuditError, OSError) as exc:
        return {
            "available": False,
            "path": path,
            "version": None,
            "write_supported": False,
            "message": str(exc),
        }
    version = result.stdout.strip()
    supported = _version_tuple(version) >= MINIMUM_WRITE_EXIFTOOL
    return {
        "available": True,
        "path": path,
        "version": version,
        "write_supported": supported,
        "message": (
            None
            if supported
            else "ExifTool 12.70 or newer is required for verified image cleanup."
        ),
    }


def _pillow_metadata(image: Image.Image) -> list[str]:
    tags: set[str] = set()
    try:
        for tag_id in image.getexif():
            tags.add(f"EXIF:{ExifTags.TAGS.get(tag_id, tag_id)}")
    except (AttributeError, TypeError, ValueError):
        pass
    for key in image.info:
        tags.add(f"ImageInfo:{key}")
    return sorted(tags)


def _exiftool_metadata(path: Path, status: dict[str, Any]) -> dict[str, Any] | None:
    if not status["available"]:
        return None
    result = _run_exiftool(
        str(status["path"]),
        ["-json", "-G1", "-a", "-u", "-struct", str(path.resolve())],
    )
    try:
        records = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ImageAuditError("ExifTool returned invalid JSON") from exc
    if (
        not isinstance(records, list)
        or len(records) != 1
        or not isinstance(records[0], dict)
    ):
        raise ImageAuditError("ExifTool returned an unexpected metadata result")
    return {str(key): value for key, value in records[0].items() if key != "SourceFile"}


def _group_and_name(tag: str) -> tuple[str, str]:
    if ":" not in tag:
        return "", tag
    group, name = tag.split(":", 1)
    return group.strip("[]"), name


def _is_provenance_tag(tag: str) -> bool:
    lowered = tag.lower()
    return "jumbf" in lowered or "c2pa" in lowered


def _contains_c2pa_reference(value: Any) -> bool:
    try:
        lowered = json.dumps(value, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        lowered = str(value).lower()
    return "c2pa" in lowered or "self#jumbf" in lowered


def _is_c2pa_reference_tag(tag: str, value: Any) -> bool:
    group, _ = _group_and_name(tag)
    return group.lower().startswith("xmp") and _contains_c2pa_reference(value)


def _metadata_classes(tags: Sequence[str]) -> dict[str, list[str]]:
    classes: dict[str, list[str]] = {
        "location_metadata": [],
        "identity_or_device_metadata": [],
        "editing_metadata": [],
        "other_metadata": [],
    }
    for tag in tags:
        group, name = _group_and_name(tag)
        lowered = f"{group}:{name}".lower().replace(" ", "")
        if group.lower() in _TECHNICAL_GROUPS:
            continue
        if group.lower().startswith("icc"):
            continue
        if _is_provenance_tag(tag):
            continue
        if any(term in lowered for term in _RENDERING_TERMS):
            continue
        if any(term in lowered for term in _STRUCTURAL_TERMS):
            continue
        if any(term in lowered for term in _LOCATION_TERMS):
            classes["location_metadata"].append(tag)
        elif any(term in lowered for term in _IDENTITY_TERMS):
            classes["identity_or_device_metadata"].append(tag)
        elif any(term in lowered for term in _EDITING_TERMS):
            classes["editing_metadata"].append(tag)
        else:
            classes["other_metadata"].append(tag)
    return classes


def _finding(
    category: str,
    signal: str,
    tags: Sequence[str],
    *,
    confidence: str = "high",
    removable: bool = True,
    action: str = "report",
) -> dict[str, Any]:
    return {
        "category": category,
        "signal": signal,
        "count": len(tags),
        "locations": [],
        "confidence": confidence,
        "removable": removable,
        "planned_action": action,
        "details": {"tags": list(tags)},
    }


def _contains_binary_c2pa_markers(path: Path) -> bool:
    found_c2pa = False
    found_jumb = False
    overlap = b""
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            lowered = (overlap + chunk).lower()
            found_c2pa = found_c2pa or b"c2pa" in lowered
            found_jumb = found_jumb or b"jumb" in lowered
            if found_c2pa and found_jumb:
                return True
            overlap = chunk[-3:]
    return False


def audit_image(
    path: str | os.PathLike[str], *, exiftool: str = "exiftool"
) -> dict[str, Any]:
    """Audit an image locally without modifying or uploading it."""
    source = Path(path)
    if not source.is_file():
        raise ImageAuditError(f"Image file not found: {source}")
    try:
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            description = {
                "format": image.format,
                "mime_type": Image.MIME.get(image.format or ""),
                "width": image.width,
                "height": image.height,
                "mode": image.mode,
                "frames": getattr(image, "n_frames", 1),
                "animated": bool(getattr(image, "is_animated", False)),
            }
            pillow_tags = _pillow_metadata(image)
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise ImageAuditError(f"Not a supported or valid image: {source}") from exc

    backend = exiftool_status(exiftool)
    exiftool_metadata = _exiftool_metadata(source, backend)
    metadata_source = "exiftool" if exiftool_metadata is not None else "pillow"
    metadata = (
        exiftool_metadata
        if exiftool_metadata is not None
        else {tag: None for tag in pillow_tags}
    )
    tags = sorted(metadata)
    provenance_tags = [tag for tag in tags if _is_provenance_tag(tag)]
    reference_tags = [
        tag
        for tag, value in metadata.items()
        if tag not in provenance_tags and _is_c2pa_reference_tag(tag, value)
    ]
    findings: list[dict[str, Any]] = []
    if provenance_tags:
        finding = _finding("provenance", "c2pa_or_jumbf_metadata", provenance_tags)
        finding.update({"scheme": "c2pa", "vendor": None})
        findings.append(finding)
    if reference_tags:
        finding = _finding(
            "provenance", "c2pa_reference_metadata", sorted(reference_tags)
        )
        finding.update({"scheme": "c2pa", "vendor": None})
        findings.append(finding)
    non_provenance_tags = [
        tag for tag in tags if tag not in provenance_tags and tag not in reference_tags
    ]
    for signal, matching in _metadata_classes(non_provenance_tags).items():
        if matching:
            findings.append(_finding("metadata", signal, matching))

    possible_c2pa = False
    if not backend["write_supported"] and not provenance_tags:
        try:
            possible_c2pa = _contains_binary_c2pa_markers(source)
        except OSError:
            pass
        if possible_c2pa:
            findings.append(
                _finding(
                    "provenance",
                    "possible_c2pa_container_bytes",
                    ["binary:c2pa+jumb"],
                    confidence="low",
                    removable=False,
                )
            )

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "image",
        "image": description,
        "backend": {"exiftool": backend, "metadata_source": metadata_source},
        "findings": findings,
        "total": sum(int(item["count"]) for item in findings),
        "pixel_watermarks": [
            {
                "scheme": "synthid",
                "status": "unsupported",
                "removable": False,
                "message": "No public profile-compatible offline pixel detector or safe generic removal method is configured.",
            },
            {
                "scheme": "unknown_visible_or_pixel_watermark",
                "status": "unsupported",
                "removable": False,
                "message": "Pixel alteration, recompression, cropping, or inpainting cannot prove watermark removal.",
            },
        ],
        "limitations": [
            "Metadata and C2PA provenance are not proof of AI generation.",
            "Absence of a finding does not establish that an image is watermark-free.",
        ],
    }


def _removable_metadata_count(report: dict[str, Any]) -> int:
    return sum(
        int(finding["count"])
        for finding in report["findings"]
        if finding["category"] == "metadata" and finding["removable"]
    )


def _confirmed_provenance_count(report: dict[str, Any]) -> int:
    return sum(
        int(finding["count"])
        for finding in report["findings"]
        if finding["category"] == "provenance"
        and finding["signal"] in {"c2pa_or_jumbf_metadata", "c2pa_reference_metadata"}
    )


def _provenance_reference_count(report: dict[str, Any]) -> int:
    return sum(
        int(finding["count"])
        for finding in report["findings"]
        if finding["category"] == "provenance"
        and finding["signal"] == "c2pa_reference_metadata"
    )


def plan_image_cleanup(
    report: dict[str, Any], *, strip_metadata: bool, strip_provenance: bool
) -> dict[str, Any]:
    actions: list[str] = []
    if strip_metadata:
        actions.append("remove_non_rendering_metadata")
    if strip_provenance:
        actions.append("remove_c2pa_jumbf_provenance")
    status = report["backend"]["exiftool"]
    provenance_blocked = bool(
        strip_metadata and not strip_provenance and _confirmed_provenance_count(report)
    )
    reference_blocked = bool(
        strip_provenance and not strip_metadata and _provenance_reference_count(report)
    )
    return {
        "changed_expected": bool(
            (strip_metadata and _removable_metadata_count(report))
            or (strip_provenance and _confirmed_provenance_count(report))
        ),
        "actions": actions,
        "preserved": ["pixel data", "ICC profile", "orientation", "color-space tags"],
        "backend_ready": bool(
            status["write_supported"]
            and not provenance_blocked
            and not reference_blocked
        ),
        "backend_message": (
            "Metadata cleanup could invalidate C2PA provenance; add --strip-provenance explicitly."
            if provenance_blocked
            else (
                "C2PA reference metadata requires --strip-metadata with --strip-provenance."
                if reference_blocked
                else status["message"]
            )
        ),
    }


def clean_image(
    source: str | os.PathLike[str],
    output: str | os.PathLike[str],
    *,
    strip_metadata: bool,
    strip_provenance: bool,
    exiftool: str = "exiftool",
    force: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Losslessly remove selected image metadata through a verified local ExifTool."""
    if not strip_metadata and not strip_provenance:
        raise ImageAuditError("Select --strip-metadata and/or --strip-provenance")
    source_path = Path(source)
    output_path = Path(output)
    if source_path.resolve() == output_path.resolve():
        raise ImageAuditError(
            "Input and output must differ; in-place image cleanup is not supported"
        )
    if source_path.suffix.lower() not in WRITABLE_SUFFIXES:
        raise ImageAuditError(
            f"Cleanup is not supported for {source_path.suffix or 'extensionless'} images"
        )
    if output_path.suffix.lower() != source_path.suffix.lower():
        raise ImageAuditError("Output must keep the input image extension")
    if output_path.exists() and not force:
        raise ImageAuditError(f"Output already exists (use --force): {output_path}")
    if not output_path.parent.is_dir():
        raise ImageAuditError(f"Output directory does not exist: {output_path.parent}")

    before = audit_image(source_path, exiftool=exiftool)
    status = before["backend"]["exiftool"]
    if not status["write_supported"]:
        raise ImageAuditError(str(status["message"]))
    if strip_metadata and not strip_provenance and _confirmed_provenance_count(before):
        raise ImageAuditError(
            "Metadata cleanup could invalidate C2PA provenance; add --strip-provenance explicitly"
        )
    if strip_provenance and not strip_metadata and _provenance_reference_count(before):
        raise ImageAuditError(
            "C2PA reference metadata requires --strip-metadata with --strip-provenance"
        )

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.stem}.",
        suffix=output_path.suffix,
        dir=output_path.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copy2(source_path, temporary)
        arguments = ["-overwrite_original"]
        if strip_metadata:
            arguments.extend(["-all=", "--ICC_Profile:all"])
            arguments.extend(
                [
                    "-tagsfromfile",
                    "@",
                    "-Orientation",
                    "-ColorSpaceTags",
                ]
            )
        if strip_provenance:
            arguments.append("-JUMBF:all=")
        arguments.append(str(temporary))
        _run_exiftool(str(status["path"]), arguments)
        after = audit_image(temporary, exiftool=exiftool)
        if strip_provenance and _confirmed_provenance_count(after):
            raise ImageAuditError("C2PA/JUMBF provenance remained after cleanup")
        if strip_metadata and _removable_metadata_count(after):
            raise ImageAuditError("Removable metadata remained after cleanup")
        os.replace(temporary, output_path)
        return before, after
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
