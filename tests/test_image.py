import json
import struct
import subprocess
import zlib

import pytest
from PIL import Image, ImageCms, PngImagePlugin, TiffImagePlugin, features

from unicodefix.image import (
    ImageAuditError,
    audit_image,
    clean_image,
    plan_image_cleanup,
)
from unicodefix.image_container import C2PA_UUID, inspect_container


def _chunk(kind, data):
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data))
    )


def _box(kind, data):
    return struct.pack(">I", len(data) + 8) + kind + data


def _manifest():
    # Structural carrier fixture, not a signed/cryptographically valid credential.
    description = _box(b"jumd", C2PA_UUID + b"\x03c2pa\0")
    return _box(b"jumb", description + _box(b"cbor", b"\xa0"))


def _riff_chunk(kind, data):
    return (
        kind + struct.pack("<I", len(data)) + data + (b"\0" if len(data) % 2 else b"")
    )


def _inject(data, fmt, manifest, *, fragmented=False):
    if fmt == "PNG":
        return data[:33] + _chunk(b"caBX", manifest) + data[33:]
    if fmt == "WEBP":
        body = data[8:] + _riff_chunk(b"C2PA", manifest)
        return b"RIFF" + struct.pack("<I", len(body)) + body
    pieces = (
        [manifest[i : i + 32] for i in range(0, len(manifest), 32)]
        if fragmented
        else [manifest]
    )
    segments = []
    for sequence, piece in enumerate(pieces, 1):
        payload = (
            b"JP\0\x01"
            + sequence.to_bytes(4, "big")
            + (manifest[:8] if sequence > 1 else b"")
            + piece
        )
        segments.append(b"\xff\xeb" + struct.pack(">H", len(payload) + 2) + payload)
    return data[:2] + b"".join(segments) + data[2:]


def _fixture(path, *, fmt=None, animated=False, progressive=False):
    fmt = (
        fmt
        or {".png": "PNG", ".jpg": "JPEG", ".webp": "WEBP", ".tiff": "TIFF"}[
            path.suffix
        ]
    )
    frames = [Image.new("RGB", (8, 6), color) for color in ("red", "blue")]
    exif = Image.Exif()
    exif[315] = "Private Fixture Artist"
    exif[274] = 6
    exif[34665] = {40961: 1, 37510: b"Private comment"}
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    options = {"exif": exif, "icc_profile": profile}
    if fmt == "PNG":
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Comment", "Private fixture comment")
        metadata.add_itxt("Description", "Private multilingual text", zip=True)
        metadata.add_text("Software", "Fixture writer", zip=True)
        options["pnginfo"] = metadata
    if fmt == "JPEG":
        options["progressive"] = progressive
    if animated:
        options.update(
            save_all=True, append_images=frames[1:], duration=[70, 130], loop=2
        )
    frames[0].save(path, format=fmt, **options)
    return profile


@pytest.mark.parametrize(
    "suffix,animated,progressive",
    [
        (".png", False, False),
        (".png", True, False),
        (".jpg", False, False),
        (".jpg", False, True),
        (".webp", False, False),
        (".webp", True, False),
    ],
)
def test_cleanup_without_external_program_preserves_payload_and_rendering(
    tmp_path, monkeypatch, suffix, animated, progressive
):
    source = tmp_path / ("source" + suffix)
    output = tmp_path / ("clean" + suffix)
    profile = _fixture(source, animated=animated, progressive=progressive)
    original = source.read_bytes()

    def external_program_forbidden(*args, **kwargs):
        raise AssertionError("No external executable may be called")

    monkeypatch.setattr(subprocess, "run", external_program_forbidden)
    before, after = clean_image(
        source, output, strip_metadata=True, strip_provenance=False
    )
    assert before["backend"]["name"] == "builtin"
    assert after["total"] == 0
    assert (
        inspect_container(original).protected_digest()
        == inspect_container(output.read_bytes()).protected_digest()
    )
    assert source.read_bytes() == original
    with Image.open(source) as left, Image.open(output) as right:
        assert right.info["icc_profile"] == profile
        assert right.getexif()[274] == 6
        assert right.getexif().get_ifd(34665)[40961] == 1
        assert 315 not in right.getexif()
        assert 37510 not in right.getexif().get_ifd(34665)
        assert getattr(left, "n_frames", 1) == getattr(right, "n_frames", 1)
        for index in range(getattr(left, "n_frames", 1)):
            left.seek(index)
            right.seek(index)
            assert left.tobytes() == right.tobytes()
            assert left.info.get("duration") == right.info.get("duration")
        assert left.info.get("loop") == right.info.get("loop")
    second = tmp_path / ("second" + suffix)
    clean_image(output, second, strip_metadata=True, strip_provenance=False)
    assert second.read_bytes() == output.read_bytes()
    assert not list(tmp_path.glob(".*.png"))


@pytest.mark.parametrize(
    "fmt,suffix", [("PNG", ".png"), ("JPEG", ".jpg"), ("WEBP", ".webp")]
)
@pytest.mark.parametrize("fragmented", [False, True])
def test_recognized_c2pa_is_protected_then_removed(tmp_path, fmt, suffix, fragmented):
    source = tmp_path / ("signed" + suffix)
    _fixture(source)
    source.write_bytes(
        _inject(source.read_bytes(), fmt, _manifest(), fragmented=fragmented)
    )
    original = source.read_bytes()
    output = tmp_path / ("clean" + suffix)
    report = audit_image(source)
    assert any(f["signal"] == "c2pa_or_jumbf_metadata" for f in report["findings"])
    assert not plan_image_cleanup(report, strip_metadata=True, strip_provenance=False)[
        "backend_ready"
    ]
    with pytest.raises(ImageAuditError, match="strip-provenance"):
        clean_image(source, output, strip_metadata=True, strip_provenance=False)
    assert not output.exists()
    before, after = clean_image(
        source, output, strip_metadata=True, strip_provenance=True
    )
    assert not any(f["category"] == "provenance" for f in after["findings"])
    assert source.read_bytes() == original
    assert before["preservation"] == after["preservation"]


@pytest.mark.parametrize(
    "fmt,suffix", [("PNG", ".png"), ("JPEG", ".jpg"), ("WEBP", ".webp")]
)
def test_provenance_only_keeps_other_metadata(tmp_path, fmt, suffix):
    source = tmp_path / ("signed" + suffix)
    _fixture(source)
    source.write_bytes(_inject(source.read_bytes(), fmt, _manifest()))
    output = tmp_path / ("clean" + suffix)
    _, after = clean_image(source, output, strip_metadata=False, strip_provenance=True)
    assert any(f["category"] == "metadata" for f in after["findings"])
    assert not any(f["category"] == "provenance" for f in after["findings"])
    with Image.open(output) as image:
        assert image.getexif()[315] == "Private Fixture Artist"


@pytest.mark.parametrize(
    "fmt,suffix", [("PNG", ".png"), ("JPEG", ".jpg"), ("WEBP", ".webp")]
)
def test_malformed_carriers_are_reported_and_never_removed(tmp_path, fmt, suffix):
    source = tmp_path / ("signed" + suffix)
    _fixture(source)
    source.write_bytes(_inject(source.read_bytes(), fmt, _manifest()[:-1]))
    report = audit_image(source)
    assert any(
        f["signal"] == "malformed_or_unrecognized_c2pa_carrier"
        for f in report["findings"]
    )
    with pytest.raises(ImageAuditError, match="Malformed or unrecognized"):
        clean_image(
            source,
            tmp_path / ("out" + suffix),
            strip_metadata=True,
            strip_provenance=True,
        )


def test_xmp_reference_does_not_expose_value_and_needs_both_flags(tmp_path):
    source = tmp_path / "reference.png"
    _fixture(source)
    packet = b'<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dcterms="http://purl.org/dc/terms/"><rdf:RDF><rdf:Description dcterms:provenance="https://private.example/manifest/123"/></rdf:RDF></x:xmpmeta>'
    itxt = b"XML:com.adobe.xmp\0\0\0\0\0" + packet
    data = source.read_bytes()
    source.write_bytes(data[:33] + _chunk(b"iTXt", itxt) + data[33:])
    report = audit_image(source)
    assert "private.example" not in json.dumps(report)
    assert any(f["signal"] == "c2pa_reference_metadata" for f in report["findings"])
    assert not plan_image_cleanup(report, strip_metadata=False, strip_provenance=True)[
        "backend_ready"
    ]
    _, after = clean_image(
        source, tmp_path / "clean.png", strip_metadata=True, strip_provenance=True
    )
    assert after["total"] == 0


def test_xmp_orientation_is_retained_while_private_fields_are_removed(tmp_path):
    source = tmp_path / "xmp.png"
    _fixture(source)
    packet = b'<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:tiff="http://ns.adobe.com/tiff/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/"><rdf:RDF><rdf:Description tiff:Orientation="6" dc:creator="Private Artist"/></rdf:RDF></x:xmpmeta>'
    data = source.read_bytes()
    source.write_bytes(
        data[:33] + _chunk(b"iTXt", b"XML:com.adobe.xmp\0\0\0\0\0" + packet) + data[33:]
    )
    output = tmp_path / "clean.png"
    clean_image(source, output, strip_metadata=True, strip_provenance=False)
    assert b"Private Artist" not in output.read_bytes()
    assert b"Orientation" in output.read_bytes()
    assert audit_image(output)["total"] == 0


@pytest.mark.parametrize("compression", ["raw", "tiff_adobe_deflate", "tiff_lzw"])
def test_tiff_is_readable_but_explicitly_audit_only(tmp_path, compression):
    if compression != "raw" and not features.check("libtiff"):
        pytest.skip("Compressed TIFF support requires libtiff")
    source = tmp_path / "tagged.tiff"
    tags = TiffImagePlugin.ImageFileDirectory_v2()
    tags[315] = "Example Artist"
    Image.new("RGB", (4, 3), (12, 34, 56)).save(
        source, compression=compression, tiffinfo=tags
    )
    original = source.read_bytes()
    report = audit_image(source)
    assert report["image"]["format"] == "TIFF"
    assert not report["backend"]["write_supported"]
    assert "audit-only" in report["backend"]["message"]
    assert all(not f["removable"] for f in report["findings"])
    with pytest.raises(ImageAuditError, match="audit-only"):
        clean_image(
            source, tmp_path / "clean.tiff", strip_metadata=True, strip_provenance=False
        )
    assert source.read_bytes() == original
    assert not (tmp_path / "clean.tiff").exists()


@pytest.mark.parametrize("suffix,fmt", [(".gif", "GIF"), (".bmp", "BMP")])
def test_other_raster_formats_are_audit_only(tmp_path, suffix, fmt):
    source = tmp_path / ("source" + suffix)
    Image.new("RGB", (4, 3)).save(source, format=fmt)
    assert not audit_image(source)["backend"]["write_supported"]


def test_unknown_chunks_and_jpeg_app0_are_preserved(tmp_path):
    source = tmp_path / "private.png"
    _fixture(source)
    data = source.read_bytes()
    unknown = _chunk(b"vpAg", b"Unknown private data")
    source.write_bytes(data[:33] + unknown + data[33:])
    output = tmp_path / "clean.png"
    clean_image(source, output, strip_metadata=True, strip_provenance=False)
    assert unknown in output.read_bytes()
    jpeg = tmp_path / "source.jpg"
    _fixture(jpeg)
    output = tmp_path / "clean.jpg"
    clean_image(jpeg, output, strip_metadata=True, strip_provenance=False)
    before = [
        b.raw
        for b in inspect_container(jpeg.read_bytes()).blocks
        if b.kind == b"\xff\xe0"
    ]
    after = [
        b.raw
        for b in inspect_container(output.read_bytes()).blocks
        if b.kind == b"\xff\xe0"
    ]
    assert before and before == after


@pytest.mark.parametrize(
    "variant", ["png_crc", "png_trailer", "png_length", "jpeg_trailer", "webp_size"]
)
def test_malformed_container_framing_refuses_output(tmp_path, variant):
    suffix = (
        ".jpg"
        if variant.startswith("jpeg")
        else ".webp" if variant.startswith("webp") else ".png"
    )
    source = tmp_path / ("source" + suffix)
    _fixture(source)
    data = bytearray(source.read_bytes())
    if variant.endswith("trailer"):
        data += b"hidden trailer"
    elif variant == "png_crc":
        data[32] ^= 1
    elif variant == "png_length":
        data[8:12] = b"\x7f\xff\xff\xff"
    else:
        data[4:8] = b"\0" * 4
    source.write_bytes(data)
    with pytest.raises(ImageAuditError):
        clean_image(
            source,
            tmp_path / ("out" + suffix),
            strip_metadata=True,
            strip_provenance=False,
        )
    assert not (tmp_path / ("out" + suffix)).exists()


def test_output_contract_and_force(tmp_path):
    source = tmp_path / "source.png"
    _fixture(source)
    output = tmp_path / "out.png"
    clean_image(source, output, strip_metadata=True, strip_provenance=False)
    with pytest.raises(ImageAuditError, match="already exists"):
        clean_image(source, output, strip_metadata=True, strip_provenance=False)
    clean_image(source, output, strip_metadata=True, strip_provenance=False, force=True)
    with pytest.raises(ImageAuditError, match="Input and output must differ"):
        clean_image(source, source, strip_metadata=True, strip_provenance=False)
    with pytest.raises(ImageAuditError, match="extension"):
        clean_image(
            source, tmp_path / "out.jpg", strip_metadata=True, strip_provenance=False
        )


def test_image_cli_dry_run_and_real_cleanup_without_exiftool(
    tmp_path, monkeypatch, capsys
):
    from unicodefix import image_cli

    source = tmp_path / "source.png"
    _fixture(source)
    original = source.read_bytes()
    monkeypatch.setattr(
        "sys.argv",
        ["cleanup-image", "--dry-run", "--strip-metadata", "--json", str(source)],
    )
    with pytest.raises(SystemExit) as result:
        image_cli.main()
    assert result.value.code == 0
    report = json.loads(capsys.readouterr().out)[str(source)]
    assert report["planned"]["backend_ready"]
    assert not (tmp_path / "source.clean.png").exists()
    monkeypatch.setattr(
        "sys.argv", ["cleanup-image", "--strip-metadata", "--json", str(source)]
    )
    with pytest.raises(SystemExit) as result:
        image_cli.main()
    assert result.value.code == 0
    report = json.loads(capsys.readouterr().out)[str(source)]
    assert report["cleanup"]["after_finding_count"] == 0
    assert source.read_bytes() == original


def test_audit_rejects_non_image(tmp_path):
    source = tmp_path / "invalid.png"
    source.write_text("Not an image")
    with pytest.raises(ImageAuditError, match="supported or valid"):
        audit_image(source)


@pytest.mark.parametrize("kind", ["hdr_xmp", "doctype_xmp", "nested_jumbf", "bad_exif"])
def test_unsupported_metadata_variants_fail_closed(tmp_path, kind):
    source = tmp_path / "source.png"
    if kind == "nested_jumbf":
        exif = Image.Exif()
        exif[52545] = _manifest()
        Image.new("RGB", (8, 6)).save(source, exif=exif)
    else:
        _fixture(source)
        if kind == "bad_exif":
            extra = _chunk(b"eXIf", b"not TIFF")
        else:
            packet = (
                b'<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:hdrgm="http://ns.adobe.com/hdr-gain-map/1.0/" hdrgm:Version="1.0"/>'
                if kind == "hdr_xmp"
                else b'<!DOCTYPE x [<!ENTITY e "private">]><x>&e;</x>'
            )
            extra = _chunk(b"iTXt", b"XML:com.adobe.xmp\0\0\0\0\0" + packet)
        data = source.read_bytes()
        source.write_bytes(data[:33] + extra + data[33:])
    report = audit_image(source)
    assert not report["backend"]["write_supported"]
    assert any(
        f["signal"] == "unsupported_metadata_variant" for f in report["findings"]
    )
    with pytest.raises(ImageAuditError):
        clean_image(
            source, tmp_path / "out.png", strip_metadata=True, strip_provenance=True
        )
    assert not (tmp_path / "out.png").exists()


def test_unknown_jumbf_and_app11_are_not_deleted(tmp_path):
    source = tmp_path / "source.jpg"
    _fixture(source)
    other = _manifest().replace(
        C2PA_UUID, bytes.fromhex("00112233445566778899aabbccddeeff")
    )
    data = _inject(source.read_bytes(), "JPEG", other)
    source.write_bytes(data)
    output = tmp_path / "out.jpg"
    clean_image(source, output, strip_metadata=True, strip_provenance=True)
    assert other in output.read_bytes()


def test_corrupted_rewrite_is_never_published(tmp_path, monkeypatch):
    from unicodefix.image_container import Container

    source = tmp_path / "source.png"
    _fixture(source)
    replacement = tmp_path / "different.png"
    Image.new("RGB", (8, 6), "yellow").save(replacement)
    changed_idat = next(
        b
        for b in inspect_container(replacement.read_bytes()).blocks
        if b.kind == b"IDAT"
    )
    original_rewrite = Container.rewrite

    def corrupt(container, **options):
        data = original_rewrite(container, **options)
        blocks = inspect_container(data).blocks
        return data[:8] + b"".join(
            changed_idat.raw if block.kind == b"IDAT" else block.raw for block in blocks
        )

    monkeypatch.setattr(Container, "rewrite", corrupt)
    with pytest.raises(ImageAuditError, match="payload or rendering metadata changed"):
        clean_image(
            source, tmp_path / "out.png", strip_metadata=True, strip_provenance=False
        )
    assert not (tmp_path / "out.png").exists()


def test_concurrent_output_is_not_overwritten(tmp_path, monkeypatch):
    from unicodefix import image as backend

    source = tmp_path / "source.png"
    output = tmp_path / "out.png"
    _fixture(source)
    original_link = backend.os.link

    def race(temporary, destination):
        output.write_bytes(b"Concurrent writer data")
        return original_link(temporary, destination)

    monkeypatch.setattr(backend.os, "link", race)
    with pytest.raises(ImageAuditError, match="already exists"):
        clean_image(source, output, strip_metadata=True, strip_provenance=False)
    assert output.read_bytes() == b"Concurrent writer data"
    assert not list(tmp_path.glob(".out.*"))


def test_heif_without_decoder_is_explicitly_incomplete_and_audit_only(
    tmp_path, monkeypatch
):
    from PIL import UnidentifiedImageError

    source = tmp_path / "source.heic"
    source.write_bytes(struct.pack(">I", 24) + b"ftypheic\0\0\0\0heicmif1")

    def unavailable(*args, **kwargs):
        raise UnidentifiedImageError("No HEIF decoder")

    monkeypatch.setattr(Image, "open", unavailable)
    report = audit_image(source)
    assert report["image"]["format"] == "HEIF"
    assert report["image"]["width"] is None
    assert not report["backend"]["write_supported"]
    assert "incomplete" in report["backend"]["message"]
    assert report["backend"]["metadata_source"] == "header"


def test_image_size_limit_is_enforced_without_writing(tmp_path, monkeypatch):
    from unicodefix import image as backend

    source = tmp_path / "source.png"
    _fixture(source)
    monkeypatch.setattr(backend, "MAX_FILE_BYTES", 32)
    with pytest.raises(ImageAuditError, match="limited"):
        clean_image(
            source, tmp_path / "out.png", strip_metadata=True, strip_provenance=False
        )
    assert not (tmp_path / "out.png").exists()


def test_mentioning_c2pa_is_not_itself_a_provenance_reference(tmp_path):
    source = tmp_path / "comment.png"
    _fixture(source)
    packet = b'<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:description>C2PA is provenance, not proof.</dc:description></x:xmpmeta>'
    data = source.read_bytes()
    source.write_bytes(
        data[:33] + _chunk(b"iTXt", b"XML:com.adobe.xmp\0\0\0\0\0" + packet) + data[33:]
    )
    assert not any(
        f["category"] == "provenance" for f in audit_image(source)["findings"]
    )
    clean_image(
        source, tmp_path / "clean.png", strip_metadata=True, strip_provenance=False
    )


def test_corrupted_xmp_rendering_value_is_never_published(tmp_path, monkeypatch):
    from unicodefix.image_container import Container

    source = tmp_path / "xmp.png"
    _fixture(source)
    packet = b'<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:tiff="http://ns.adobe.com/tiff/1.0/" tiff:Orientation="6"/>'
    data = source.read_bytes()
    source.write_bytes(
        data[:33] + _chunk(b"iTXt", b"XML:com.adobe.xmp\0\0\0\0\0" + packet) + data[33:]
    )
    original_rewrite = Container.rewrite

    def corrupt(container, **options):
        changed = original_rewrite(container, **options)
        blocks = inspect_container(changed).blocks
        return changed[:8] + b"".join(
            (
                _chunk(
                    block.kind,
                    block.payload.replace(b'Orientation="6"', b'Orientation="8"'),
                )
                if block.kind == b"iTXt"
                else block.raw
            )
            for block in blocks
        )

    monkeypatch.setattr(Container, "rewrite", corrupt)
    with pytest.raises(ImageAuditError, match="payload or rendering metadata changed"):
        clean_image(
            source, tmp_path / "out.png", strip_metadata=True, strip_provenance=False
        )
    assert not (tmp_path / "out.png").exists()


def test_decompression_bomb_dimensions_are_a_clean_error(tmp_path):
    source = tmp_path / "oversized.png"
    _fixture(source)
    data = source.read_bytes()
    huge_header = struct.pack(">II", 100000, 100000) + data[24:29]
    source.write_bytes(data[:8] + _chunk(b"IHDR", huge_header) + data[33:])
    with pytest.raises(ImageAuditError, match="supported or valid"):
        audit_image(source)
