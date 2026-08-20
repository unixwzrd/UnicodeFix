"""UnicodeFix command-line interface."""

from __future__ import annotations

import argparse
import difflib
import os
import shutil
import sys
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10
    import tomli as tomllib

from unicodefix.c2pa import find_c2pa_carriers
from unicodefix.authorship import detect_authorship_profiles
from unicodefix.markdown import audit_markdown, unwrap_markdown
from unicodefix.metrics import compute_metrics
from unicodefix.report import print_csv, print_human, print_json, print_metrics_help
from unicodefix.scanner import scan_text_for_report
from unicodefix.source import clean_source_comments, scan_source
from unicodefix.transforms import clean_text, handle_newlines
from unicodefix.watermarks import detect_profiles


def _package_version() -> str:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if pyproject.exists():
        with pyproject.open("rb") as handle:
            return tomllib.load(handle)["project"]["version"]
    try:
        return version("unicodefix")
    except PackageNotFoundError:
        return "unknown"


def log(*args, **kwargs) -> None:
    if getattr(log, "_quiet", False):
        return
    print(*args, file=sys.stderr, **kwargs)


def _read_text(path: str) -> str:
    """Read UTF-8 strictly and preserve original newline bytes."""
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8", errors="strict", newline="") as handle:
        return handle.read()


def _detect_eol(sample: str) -> str:
    if "\r\n" in sample:
        return "\r\n"
    if "\r" in sample:
        return "\r"
    return "\n"


def _write_text(path: str, content: str, eol: str = "\n") -> None:
    if eol != "\n":
        content = content.replace("\n", eol)
    with open(path, "w", encoding="utf-8", errors="strict", newline="") as handle:
        handle.write(content)


def _atomic_replace_text(path: str, content: str, eol: str = "\n") -> None:
    """Write a same-directory temporary file and atomically replace path."""
    parent = os.path.dirname(path) or "."
    basename = os.path.basename(path)
    descriptor, temporary = tempfile.mkstemp(
        dir=parent, prefix=f".{basename}.", suffix=".tmp"
    )
    try:
        if eol != "\n":
            content = content.replace("\n", eol)
        with os.fdopen(
            descriptor, "w", encoding="utf-8", errors="strict", newline=""
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copymode(path, temporary)
        os.replace(temporary, path)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            os.remove(temporary)
        except FileNotFoundError:
            pass
        raise


def _preserve_backup(path: str) -> str:
    """Copy path to the first available .tmp backup name without overwriting."""
    index = 0
    while True:
        suffix = ".tmp" if index == 0 else f".tmp.{index}"
        backup = path + suffix
        try:
            descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            index += 1
            continue
        try:
            with open(path, "rb") as source, os.fdopen(descriptor, "wb") as target:
                shutil.copyfileobj(source, target)
                target.flush()
                os.fsync(target.fileno())
            shutil.copystat(path, backup)
            return backup
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                os.remove(backup)
            except FileNotFoundError:
                pass
            raise


def _clean_content(raw: str, args: argparse.Namespace, path: str = "-") -> str:
    if args.source:
        cleaned = clean_source_comments(
            raw,
            path=None if path == "-" else path,
            strip_provenance=args.strip_provenance,
        )
    else:
        cleaned = clean_text(
            raw,
            preserve_invisible=args.invisible,
            preserve_quotes=args.keep_smart_quotes,
            preserve_dashes=args.keep_dashes,
            preserve_fullwidth_brackets=args.keep_fullwidth_brackets,
            preserve_default_ignorables=args.preserve_default_ignorables,
            strip_provenance=args.strip_provenance,
        )

    if args.unwrap_markdown:
        valid_provenance = any(carrier.valid for carrier in find_c2pa_carriers(cleaned))
        if valid_provenance and not args.strip_provenance:
            raise ValueError(
                "Markdown contains C2PA provenance; use --strip-provenance "
                "explicitly before reformatting it"
            )
        cleaned = unwrap_markdown(cleaned)
    return handle_newlines(cleaned, args.no_newline)


def _category_total(data: dict[str, Any], categories: list[str] | None) -> int:
    wanted = set(categories or ())
    return sum(
        int(finding.get("count", 1))
        for finding in data.get("findings", [])
        if not wanted or finding.get("category") in wanted
    )


def _build_report_data(
    raw: str,
    args: argparse.Namespace,
    *,
    path: str = "-",
    cleaned: str | None = None,
) -> dict[str, Any]:
    data = scan_text_for_report(raw)
    if args.metrics:
        data["metrics"] = compute_metrics(raw)
    if args.unwrap_markdown or path.lower().endswith((".md", ".markdown", ".mdx")):
        data["markdown"] = audit_markdown(raw)
    if args.source:
        data["source"] = scan_source(raw, path=None if path == "-" else path)
    if args.watermark_profile:
        profile_results = detect_profiles(raw, args.watermark_profile)
        data["known_watermarks"] = profile_results
        for result in profile_results:
            if result["status"] != "detected":
                continue
            data["findings"].append(
                {
                    "category": "known_watermark",
                    "signal": f"{result['scheme']}_profile_detection",
                    "count": 1,
                    "locations": [],
                    "confidence": "medium",
                    "removable": False,
                    "planned_action": "report",
                    "message": "Detected only by the named local profile and configuration.",
                    "scheme": result["scheme"],
                    "vendor": None,
                    "details": {
                        "profile": result["profile"],
                        "configuration_fingerprint": result[
                            "configuration_fingerprint"
                        ],
                    },
                }
            )
    if args.authorship_profile:
        authorship_results = detect_authorship_profiles(raw, args.authorship_profile)
        data["authorship_signals"] = authorship_results
        for result in authorship_results:
            flagged = [
                segment for segment in result.get("segments", []) if segment["flagged"]
            ]
            if not flagged:
                continue
            data["findings"].append(
                {
                    "category": "authorship_signal",
                    "signal": f"{result['method']}_{result['metric']}",
                    "count": len(flagged),
                    "locations": [
                        {
                            "line": segment["line"],
                            "column": segment["column"],
                            "end_line": segment["end_line"],
                            "end_column": segment["end_column"],
                            "offset": segment["offset"],
                            "end_offset": segment["end_offset"],
                        }
                        for segment in flagged
                    ],
                    "confidence": "low",
                    "removable": False,
                    "planned_action": "report",
                    "message": "Paragraph crossed a calibrated local model-distribution threshold; this is not proof of AI authorship.",
                    "scheme": None,
                    "vendor": None,
                    "details": {
                        "profile": result["profile"],
                        "configuration_fingerprint": result[
                            "configuration_fingerprint"
                        ],
                        "metric": result["metric"],
                        "threshold": result["threshold"],
                        "comparison": result["comparison"],
                        "segments": flagged,
                    },
                }
            )
    if cleaned is not None:
        before_signals = {finding["signal"] for finding in data.get("findings", [])}
        after_data = scan_text_for_report(cleaned)
        after_signals = {
            finding["signal"] for finding in after_data.get("findings", [])
        }
        opcodes = difflib.SequenceMatcher(None, raw, cleaned).get_opcodes()
        data["planned"] = {
            "changed": cleaned != raw,
            "before": compute_metrics(raw),
            "after": compute_metrics(cleaned),
            "removed_characters": max(0, len(raw) - len(cleaned)),
            "added_characters": max(0, len(cleaned) - len(raw)),
            "replacement_spans": sum(tag == "replace" for tag, *_ in opcodes),
            "joined_lines": max(0, len(raw.splitlines()) - len(cleaned.splitlines())),
            "before_finding_count": sum(
                finding.get("count", 1) for finding in data.get("findings", [])
            ),
            "after_finding_count": sum(
                finding.get("count", 1) for finding in after_data.get("findings", [])
            ),
            "unchanged_findings": sorted(before_signals & after_signals),
            "resolved_findings": sorted(before_signals - after_signals),
        }
    return data


def _unified_diff(path: str, raw: str, cleaned: str) -> str:
    return "".join(
        difflib.unified_diff(
            raw.splitlines(keepends=True),
            cleaned.splitlines(keepends=True),
            fromfile=path,
            tofile=f"{path} (cleaned)",
        )
    )


def run_report(files: list[str], args: argparse.Namespace) -> int:
    results: dict[str, dict[str, Any]] = {}
    threshold_hit = False
    for path in files:
        try:
            raw = _read_text(path)
            cleaned = _clean_content(raw, args, path) if args.dry_run else None
            data = _build_report_data(raw, args, path=path, cleaned=cleaned)
        except Exception as exc:
            log(f"[x] Failed to inspect {path}: {exc}")
            return 1
        key = args.label or path
        results[key] = data
        if (
            args.threshold is not None
            and _category_total(data, args.threshold_category) >= args.threshold
        ):
            threshold_hit = True
        if not args.json and not args.csv:
            print_human(key, data, no_color=args.no_color)
            if args.diff and cleaned is not None:
                sys.stdout.write(_unified_diff(key, raw, cleaned))
    if args.json:
        print_json(results)
    elif args.csv:
        print_csv(results)
    if args.exit_zero:
        return 0
    return int(threshold_hit)


def run_filter_mode(args: argparse.Namespace) -> None:
    raw = sys.stdin.read()
    cleaned = _clean_content(raw, args)
    process_title = os.environ.get("VSCODE_PROCESS_TITLE", "")
    app_insights = os.environ.get("APPLICATION_INSIGHTS_NO_DIAGNOSTIC_CHANNEL", "")
    if (
        not args.no_newline
        and process_title.startswith("extension-host")
        and app_insights != "true"
    ):
        cleaned += "\n"
    sys.stdout.write(cleaned)


def _side_report(path: str, raw: str, args: argparse.Namespace) -> int:
    data = _build_report_data(raw, args, path=path)
    target = args.label or path
    if args.json:
        print_json({target: data}, file=sys.stderr)
    elif args.csv:
        print_csv({target: data}, file=sys.stderr)
    else:
        print_human(target, data, no_color=args.no_color, file=sys.stderr)
    if args.threshold is None:
        return 0
    return int(_category_total(data, args.threshold_category) >= args.threshold)


def process_file(infile: str, args: argparse.Namespace) -> int:
    try:
        raw = _read_text(infile)
        eol = _detect_eol(raw)
        cleaned = _clean_content(raw, args, infile)

        if args.temp:
            parent = os.path.dirname(infile) or "."
            if not (os.access(infile, os.W_OK) and os.access(parent, os.W_OK)):
                log(f"[x] In-place edit requires write permission: {infile}")
                return 1
            backup = _preserve_backup(infile) if args.preserve_tmp else None
            _atomic_replace_text(infile, cleaned, eol)
            log(f"[ok] Cleaned (in-place): {infile}")
            if backup is not None:
                log(f"[i] Preserved temp file: {backup}")
        else:
            if args.output == "-":
                sys.stdout.write(cleaned)
                return 0
            if args.output:
                outfile = args.output
            else:
                base, extension = os.path.splitext(infile)
                outfile = f"{base}.clean{extension}"
            _write_text(outfile, cleaned, eol)
            log(f"[ok] Cleaned: {infile} -> {outfile}")
        return _side_report(infile, raw, args) if args.metrics else 0
    except UnicodeDecodeError as exc:
        log(f"[x] {infile} is not strict UTF-8: {exc}")
        return 1
    except Exception as exc:
        log(f"[x] Failed to process {infile}: {exc}")
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit and safely clean Unicode, provenance, and formatting artifacts."
    )
    parser.add_argument("infile", nargs="*", help="Input file(s)")
    parser.add_argument(
        "-i", "--invisible", action="store_true", help="Preserve invisible Unicode"
    )
    parser.add_argument(
        "--preserve-default-ignorables",
        action="store_true",
        help="Preserve Unicode Default_Ignorable_Code_Point characters",
    )
    parser.add_argument("-Q", "--keep-smart-quotes", action="store_true")
    parser.add_argument("-D", "--keep-dashes", action="store_true")
    parser.add_argument("--keep-fullwidth-brackets", action="store_true")
    parser.add_argument("-n", "--no-newline", action="store_true")
    parser.add_argument("-o", "--output", help="Output filename or '-' for stdout")
    parser.add_argument(
        "-t", "--temp", action="store_true", help="Atomically clean files in place"
    )
    parser.add_argument(
        "-p",
        "--preserve-tmp",
        action="store_true",
        help="With --temp, preserve the original as an unused .tmp backup name",
    )
    parser.add_argument("--unwrap-markdown", action="store_true")
    parser.add_argument("--strip-provenance", action="store_true")
    parser.add_argument(
        "--source", action="store_true", help="Use conservative source-code handling"
    )

    parser.add_argument(
        "--report", action="store_true", help="Audit without changing input"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the requested cleanup in memory and report planned changes",
    )
    parser.add_argument(
        "--diff", action="store_true", help="With --dry-run, show a unified diff"
    )
    formats = parser.add_mutually_exclusive_group()
    formats.add_argument("--csv", action="store_true")
    formats.add_argument("--json", action="store_true")
    parser.add_argument("--label")
    parser.add_argument("--threshold", type=int)
    parser.add_argument(
        "--threshold-category",
        action="append",
        choices=(
            "provenance",
            "unicode_security",
            "known_watermark",
            "authorship_signal",
            "typography",
            "formatting",
        ),
        help="Count only this category for --threshold; repeatable",
    )
    parser.add_argument(
        "--watermark-profile",
        action="append",
        default=[],
        metavar="PATH",
        help="Run an explicit local statistical-watermark detector profile",
    )
    parser.add_argument(
        "--authorship-profile",
        action="append",
        default=[],
        metavar="PATH",
        help="Run a calibrated local model-distribution authorship profile",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Include deterministic document metrics; implies report without output options",
    )
    parser.add_argument("--metrics-help", action="store_true")
    parser.add_argument("--exit-zero", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {_package_version()}"
    )
    return parser


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    log._quiet = bool(args.quiet)

    if args.metrics_help:
        print_metrics_help(no_color=args.no_color)
        raise SystemExit(0)
    if args.diff and not args.dry_run:
        parser.error("--diff requires --dry-run")
    if args.diff and (args.json or args.csv):
        parser.error("--diff cannot be combined with --json or --csv")
    if args.source and args.unwrap_markdown:
        parser.error("--source and --unwrap-markdown are separate safety profiles")
    if args.output and args.output != "-" and len(args.infile) > 1:
        parser.error("--output with a filename accepts one input file")
    if args.dry_run and (args.output or args.temp):
        parser.error("--dry-run never accepts output or in-place write options")
    if args.metrics and not (args.output or args.temp):
        args.report = True
    if args.dry_run or args.watermark_profile or args.authorship_profile:
        args.report = True

    if args.report:
        files = args.infile or ["-"]
        raise SystemExit(run_report(files, args))
    if not args.infile:
        run_filter_mode(args)
        raise SystemExit(0)

    seen: set[str] = set()
    exit_code = 0
    for infile in args.infile:
        if infile in seen:
            log(f"[i] Skipping duplicate: {infile}")
            continue
        seen.add(infile)
        exit_code = max(exit_code, process_file(infile, args))
    raise SystemExit(0 if args.exit_zero else exit_code)


if __name__ == "__main__":
    main()
