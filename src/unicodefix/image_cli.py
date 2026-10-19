"""Command-line image audit and conservative metadata cleanup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from rich.console import Console
from rich.table import Table

from unicodefix import __version__
from unicodefix.image import (
    ImageAuditError,
    audit_image,
    clean_image,
    plan_image_cleanup,
)


def _default_output(path: str) -> str:
    source = Path(path)
    return str(source.with_name(f"{source.stem}.clean{source.suffix}"))


def print_image_report(
    path: str,
    report: dict[str, Any],
    *,
    no_color: bool,
    file: TextIO | None = None,
) -> None:
    console = Console(no_color=no_color, file=file)
    image = report["image"]
    backend = report["backend"]["exiftool"]
    console.print(f"\nImage: {path}", style="bold")
    console.print(
        f"{image['format']} {image['width']}x{image['height']} {image['mode']}  "
        f"frames={image['frames']}  findings={report['total']}"
    )
    table = Table(title="Observable findings", box=None, pad_edge=False)
    table.add_column("Category", style="bold")
    table.add_column("Signal")
    table.add_column("Count", justify="right")
    table.add_column("Removable")
    for finding in report["findings"]:
        table.add_row(
            finding["category"],
            finding["signal"],
            str(finding["count"]),
            "yes" if finding["removable"] else "no",
        )
    if report["findings"]:
        console.print(table)
    else:
        console.print("Findings: none", style="green")
    status = "ready" if backend["write_supported"] else "audit only"
    console.print(f"ExifTool: {backend['version'] or 'unavailable'} ({status})")
    if backend["message"]:
        console.print(backend["message"], style="yellow")
    console.print(
        "Pixel watermark detectors: SynthID and unknown schemes unsupported; no watermark-free claim is made.",
        style="dim",
    )
    if "planned" in report:
        console.print(
            f"Planned actions: {', '.join(report['planned']['actions']) or 'none'}"
        )
        if report["planned"]["backend_message"]:
            console.print(report["planned"]["backend_message"], style="yellow")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit image metadata and locally remove selected metadata or C2PA provenance."
    )
    parser.add_argument("infile", nargs="+", help="Input image file(s)")
    parser.add_argument("--report", action="store_true", help="Audit without writing")
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Include image structure metrics (already present in every report)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report the requested cleanup without writing",
    )
    parser.add_argument("--strip-metadata", action="store_true")
    parser.add_argument("--strip-provenance", action="store_true")
    parser.add_argument("-o", "--output", help="Output filename; accepts one input")
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing output file"
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--exiftool", default="exiftool", help=argparse.SUPPRESS)
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if args.metrics:
        args.report = True
    has_cleanup = args.strip_metadata or args.strip_provenance
    if args.output and len(args.infile) != 1:
        parser.error("--output accepts one input file")
    if args.output and (args.report or args.dry_run or not has_cleanup):
        parser.error("--output requires a write operation")
    if args.force and (args.report or args.dry_run or not has_cleanup):
        parser.error("--force applies only when writing output")
    if not has_cleanup:
        args.report = True

    results: dict[str, dict[str, Any]] = {}
    exit_code = 0
    for infile in dict.fromkeys(args.infile):
        try:
            if args.report or args.dry_run:
                report = audit_image(infile, exiftool=args.exiftool)
                if args.strip_metadata or args.strip_provenance:
                    report["planned"] = plan_image_cleanup(
                        report,
                        strip_metadata=args.strip_metadata,
                        strip_provenance=args.strip_provenance,
                    )
                    if args.dry_run and not report["planned"]["backend_ready"]:
                        exit_code = 1
                results[infile] = report
            else:
                outfile = args.output or _default_output(infile)
                before, after = clean_image(
                    infile,
                    outfile,
                    strip_metadata=args.strip_metadata,
                    strip_provenance=args.strip_provenance,
                    exiftool=args.exiftool,
                    force=args.force,
                )
                report = before
                report["cleanup"] = {
                    "output": outfile,
                    "before_finding_count": before["total"],
                    "after_finding_count": after["total"],
                    "removed_findings": max(0, before["total"] - after["total"]),
                }
                results[infile] = report
                if not args.json:
                    print(f"[ok] Cleaned: {infile} -> {outfile}", file=sys.stderr)
        except (ImageAuditError, OSError) as exc:
            print(f"[x] Failed to process {infile}: {exc}", file=sys.stderr)
            exit_code = 1

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for path, report in results.items():
            print_image_report(path, report, no_color=args.no_color)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
