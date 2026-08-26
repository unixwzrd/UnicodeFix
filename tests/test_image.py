import json
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from unicodefix import image as image_module
from unicodefix.image import (
    ImageAuditError,
    audit_image,
    clean_image,
    plan_image_cleanup,
)


def _png(path: Path) -> None:
    Image.new("RGB", (4, 3), (12, 34, 56)).save(path)


def test_audit_image_without_exiftool_is_local_and_explicit(tmp_path):
    source = tmp_path / "plain.png"
    _png(source)

    report = audit_image(source, exiftool="definitely-missing-exiftool")

    assert report["schema_version"] == "2.0.1"
    assert report["image"]["format"] == "PNG"
    assert report["image"]["width"] == 4
    assert report["backend"]["exiftool"]["available"] is False
    assert report["total"] == 0
    assert report["pixel_watermarks"][0]["scheme"] == "synthid"
    assert report["pixel_watermarks"][0]["status"] == "unsupported"


def test_audit_reports_exif_metadata_with_pillow_fallback(tmp_path):
    source = tmp_path / "tagged.jpg"
    exif = Image.Exif()
    exif[315] = "Example Artist"
    Image.new("RGB", (3, 2), "white").save(source, exif=exif)

    report = audit_image(source, exiftool="definitely-missing-exiftool")

    finding = next(
        item
        for item in report["findings"]
        if item["signal"] == "identity_or_device_metadata"
    )
    assert finding["details"]["tags"] == ["EXIF:Artist"]


def test_audit_rejects_non_image(tmp_path):
    source = tmp_path / "not-image.png"
    source.write_text("not an image", encoding="utf-8")

    with pytest.raises(ImageAuditError, match="Not a supported or valid image"):
        audit_image(source, exiftool="definitely-missing-exiftool")


def test_structural_container_tags_are_not_reported_as_metadata():
    classes = image_module._metadata_classes(
        [
            "PNG:ImageWidth",
            "PNG:ImageHeight",
            "PNG:BitDepth",
            "PNG:ColorType",
            "PNG:Compression",
            "PNG:Filter",
            "PNG:Interlace",
        ]
    )

    assert all(not tags for tags in classes.values())


def test_c2pa_reference_values_are_detected_without_exposing_value(
    tmp_path, monkeypatch
):
    source = tmp_path / "referenced.jpg"
    Image.new("RGB", (3, 2), "white").save(source)
    monkeypatch.setattr(
        image_module,
        "exiftool_status",
        lambda executable="exiftool": {
            "available": True,
            "path": "/fake/exiftool",
            "version": "13.55",
            "write_supported": True,
            "message": None,
        },
    )
    monkeypatch.setattr(
        image_module,
        "_exiftool_metadata",
        lambda path, status: {
            "XMP-dcterms:Provenance": "self#jumbf=/c2pa/example/c2pa.claim"
        },
    )

    report = audit_image(source)

    finding = report["findings"][0]
    assert finding["signal"] == "c2pa_reference_metadata"
    assert finding["details"]["tags"] == ["XMP-dcterms:Provenance"]
    assert "self#jumbf" not in json.dumps(report)
    plan = plan_image_cleanup(report, strip_metadata=False, strip_provenance=True)
    assert plan["backend_ready"] is False
    assert "--strip-metadata" in plan["backend_message"]


def test_clean_image_refuses_old_exiftool(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    _png(source)
    monkeypatch.setattr(
        image_module,
        "exiftool_status",
        lambda executable="exiftool": {
            "available": True,
            "path": "/usr/bin/exiftool",
            "version": "10.65",
            "write_supported": False,
            "message": "ExifTool 12.70 or newer is required for verified image cleanup.",
        },
    )
    monkeypatch.setattr(image_module, "_exiftool_metadata", lambda path, status: {})

    with pytest.raises(ImageAuditError, match="12.70"):
        clean_image(
            source,
            output,
            strip_metadata=True,
            strip_provenance=False,
        )
    assert not output.exists()


def test_clean_image_refuses_existing_output(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    _png(source)
    _png(output)

    with pytest.raises(ImageAuditError, match="Output already exists"):
        clean_image(
            source,
            output,
            strip_metadata=True,
            strip_provenance=False,
        )


def test_clean_image_uses_lossless_metadata_command_and_verifies(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    output = tmp_path / "output.jpg"
    Image.new("RGB", (3, 2), "white").save(source)
    calls = []
    audits = iter(
        [
            {
                "backend": {
                    "exiftool": {
                        "write_supported": True,
                        "path": "/fake/exiftool",
                        "message": None,
                    }
                },
                "findings": [
                    {
                        "category": "metadata",
                        "signal": "editing_metadata",
                        "count": 1,
                        "removable": True,
                    },
                    {
                        "category": "provenance",
                        "signal": "c2pa_or_jumbf_metadata",
                        "count": 1,
                        "removable": True,
                    },
                ],
                "total": 2,
            },
            {
                "backend": {"exiftool": {"write_supported": True}},
                "findings": [],
                "total": 0,
            },
        ]
    )
    monkeypatch.setattr(
        image_module, "audit_image", lambda *args, **kwargs: next(audits)
    )

    def fake_run(executable, arguments, check=True):
        calls.append((executable, list(arguments)))
        return subprocess.CompletedProcess([executable, *arguments], 0, "", "")

    monkeypatch.setattr(image_module, "_run_exiftool", fake_run)

    clean_image(
        source,
        output,
        strip_metadata=True,
        strip_provenance=True,
    )

    assert output.read_bytes() == source.read_bytes()
    command = calls[0][1]
    assert "-all=" in command
    assert "--ICC_Profile:all" in command
    assert "-Orientation" in command
    assert "-ColorSpaceTags" in command
    assert "-JUMBF:all=" in command


def test_metadata_cleanup_refuses_to_invalidate_provenance(tmp_path, monkeypatch):
    source = tmp_path / "source.jpg"
    output = tmp_path / "output.jpg"
    Image.new("RGB", (3, 2), "white").save(source)
    provenance = {
        "category": "provenance",
        "signal": "c2pa_or_jumbf_metadata",
        "count": 1,
        "removable": True,
    }
    audits = iter(
        [
            {
                "backend": {
                    "exiftool": {
                        "write_supported": True,
                        "path": "/fake/exiftool",
                        "message": None,
                    }
                },
                "findings": [
                    {
                        "category": "metadata",
                        "signal": "editing_metadata",
                        "count": 1,
                        "removable": True,
                    },
                    provenance,
                ],
                "total": 2,
            },
        ]
    )
    monkeypatch.setattr(
        image_module, "audit_image", lambda *args, **kwargs: next(audits)
    )
    with pytest.raises(ImageAuditError, match="invalidate C2PA provenance"):
        clean_image(
            source,
            output,
            strip_metadata=True,
            strip_provenance=False,
        )

    assert not output.exists()


def test_cleanup_image_cli_json_report(tmp_path, capsys, monkeypatch):
    from unicodefix import image_cli

    source = tmp_path / "plain.png"
    _png(source)
    monkeypatch.setattr(
        "sys.argv",
        [
            "cleanup-image",
            "--metrics",
            "--json",
            "--exiftool",
            "definitely-missing-exiftool",
            str(source),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        image_cli.main()
    assert exc.value.code == 0
    report = json.loads(capsys.readouterr().out)[str(source)]
    assert report["kind"] == "image"


def test_cleanup_image_cli_rejects_output_without_cleanup(tmp_path, monkeypatch):
    from unicodefix import image_cli

    source = tmp_path / "plain.png"
    _png(source)
    monkeypatch.setattr(
        "sys.argv",
        ["cleanup-image", "--output", str(tmp_path / "other.png"), str(source)],
    )

    with pytest.raises(SystemExit) as exc:
        image_cli.main()

    assert exc.value.code == 2


def test_cleanup_image_cli_dry_run_writes_no_output(tmp_path, monkeypatch, capsys):
    from unicodefix import image_cli

    source = tmp_path / "plain.png"
    _png(source)
    monkeypatch.setattr(
        "sys.argv",
        [
            "cleanup-image",
            "--dry-run",
            "--strip-metadata",
            "--json",
            "--exiftool",
            "definitely-missing-exiftool",
            str(source),
        ],
    )

    with pytest.raises(SystemExit) as exc:
        image_cli.main()

    assert exc.value.code == 1
    assert not (tmp_path / "plain.clean.png").exists()
    report = json.loads(capsys.readouterr().out)[str(source)]
    assert report["planned"]["backend_ready"] is False
