import argparse
import errno
import os
import shutil
import sys
from typing import Dict, List, Optional, Union

from unicodefix.report import print_csv, print_human, print_json, print_metrics_help
from unicodefix.scanner import scan_text_for_report
from unicodefix.transforms import clean_text, handle_newlines


# optional metrics
def _maybe_metrics(text: str, enabled: bool):
    if not enabled:
        return None
    try:
        from unicodefix.metrics import compute_metrics

        return compute_metrics(text)
    except Exception as e:
        return {"error": str(e)}


# ----- util
def log(*a, **kw):
    if getattr(log, "_quiet", False):
        return
    print(*a, file=sys.stderr, **kw)


def _read_text(path: str) -> str:
    """Read text without normalizing newlines so CRLF is preserved.

    Using newline="" prevents Python's universal newline translation, so we can
    preserve the file's original line ending style when writing back.
    """
    if path == "-":
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
        return f.read()


def _detect_eol(sample: str) -> str:
    """Detect dominant EOL style in a text blob: "\r\n", "\n", or "\r".

    Defaults to "\n" if mixed or none detected.
    """
    if "\r\n" in sample:
        return "\r\n"
    if "\r" in sample:
        return "\r"
    return "\n"


def _write_text(path: str, content: str, eol: str = "\n") -> None:
    """Write text with explicit EOLs preserved.

    We write with newline="" (no translation) and pre-convert "\n" to the
    desired EOL sequence when needed.
    """
    if eol != "\n":
        content = content.replace("\n", eol)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)


# ----- actions
def run_report(
    files: List[str],
    json_mode: bool,
    csv_mode: bool,
    threshold: Optional[int],
    metrics: bool,
    no_color: bool,
    display_label: Optional[str] = None,
    warn_only: bool = False,
) -> int:
    results: Dict[str, dict] = {}
    exit_hits = 0

    for path in files:
        raw = _read_text(path)  # still read the real path or "-"
        data = scan_text_for_report(raw)

        m = _maybe_metrics(raw, metrics)
        if m is not None:
            data["metrics"] = m

        # If a label was provided, always use it as the display key.
        # Otherwise, use the actual path (or "-" for stdin).
        key = display_label or path
        results[key] = data

        if threshold is not None and data["total"] >= threshold:
            exit_hits = 1

        if not json_mode and not csv_mode:
            print_human(key, data, no_color=no_color)

    if json_mode:
        print_json(results)
    elif csv_mode:
        print_csv(results)

    return 0 if warn_only else exit_hits


def run_filter_mode(args) -> None:
    raw = sys.stdin.read()
    cleaned = clean_text(
        raw,
        preserve_invisible=args.invisible,
        preserve_quotes=args.keep_smart_quotes,
        preserve_dashes=args.keep_dashes,
        preserve_fullwidth_brackets=args.keep_fullwidth_brackets,
    )
    cleaned = handle_newlines(cleaned, args.no_newline)
    # VSCode quirk: append only to stdout
    process_title = os.environ.get("VSCODE_PROCESS_TITLE", "")
    app_insights = os.environ.get("APPLICATION_INSIGHTS_NO_DIAGNOSTIC_CHANNEL", "")
    if (
        not args.no_newline
        and process_title.startswith("extension-host")
        and app_insights != "true"
    ):
        cleaned += "\n"
    sys.stdout.write(cleaned)


def process_file(infile: str, args) -> None:
    try:
        # Read once to preserve original EOL style
        raw = _read_text(infile)
        eol = _detect_eol(raw)

        if args.temp:
            tmpfile = infile + ".tmp"
            # Preflight perms: require write access to file and directory
            parent_dir = os.path.dirname(infile) or "."
            if not (os.access(infile, os.W_OK) and os.access(parent_dir, os.W_OK)):
                log(f"[✗] In-place edit requires write permission: {infile}")
                return
            # Move original to .tmp (preserve original). Fallback to copy on EXDEV.
            try:
                os.replace(infile, tmpfile)
            except OSError as e:
                if e.errno in (
                    errno.EXDEV,
                    getattr(errno, "ERROR_NOT_SAME_DEVICE", 18),
                ):
                    shutil.copy2(infile, tmpfile)
                    os.remove(infile)
                else:
                    raise
            try:
                # Process the previously read content and write back to original path
                cleaned = clean_text(
                    raw,
                    preserve_invisible=args.invisible,
                    preserve_quotes=args.keep_smart_quotes,
                    preserve_dashes=args.keep_dashes,
                    preserve_fullwidth_brackets=args.keep_fullwidth_brackets,
                )
                cleaned = handle_newlines(cleaned, args.no_newline)
                _write_text(infile, cleaned, eol)
                log(f"[✓] Cleaned (in-place): {infile}")
                if not args.preserve_tmp:
                    try:
                        os.remove(tmpfile)
                    except FileNotFoundError:
                        pass
                else:
                    log(f"[i] Preserved temp file: {tmpfile}")
                return
            except Exception:
                # Attempt to restore original from tmp
                try:
                    if os.path.exists(tmpfile):
                        os.replace(tmpfile, infile)
                finally:
                    raise

        cleaned = clean_text(
            raw,
            preserve_invisible=args.invisible,
            preserve_quotes=args.keep_smart_quotes,
            preserve_dashes=args.keep_dashes,
            preserve_fullwidth_brackets=args.keep_fullwidth_brackets,
        )
        cleaned = handle_newlines(cleaned, args.no_newline)

        if args.output:
            if args.output == "-":
                sys.stdout.write(cleaned)
                return
            else:
                outfile = args.output
        else:
            base, ext = os.path.splitext(infile)
            outfile = f"{base}.clean{ext}"

        _write_text(outfile, cleaned, eol)
        log(f"[✓] Cleaned: {infile} → {outfile}")
    except Exception as e:
        log(f"[✗] Failed to process {infile}: {e}")


# ----- CLI
def main():
    parser = argparse.ArgumentParser(
        description=(
            "Clean Unicode quirks from text.\n"
            "STDIN→STDOUT if no files; otherwise writes .clean files or -o."
        ),
        epilog="\n",
    )
    parser.add_argument("infile", nargs="*", help="Input file(s)")
    parser.add_argument(
        "-i",
        "--invisible",
        action="store_true",
        help="Preserve invisible Unicode (ZW*, bidi controls)",
    )
    parser.add_argument(
        "-Q",
        "--keep-smart-quotes",
        action="store_true",
        help="Preserve Unicode smart quotes",
    )
    parser.add_argument(
        "-D", "--keep-dashes", action="store_true", help="Preserve Unicode EN/EM dashes"
    )
    parser.add_argument(
        "--keep-fullwidth-brackets",
        action="store_true",
        help="Preserve fullwidth square brackets (【】)",
    )
    parser.add_argument(
        "-n", "--no-newline", action="store_true", help="Do not add a final newline"
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename or '-' for STDOUT will aggregate all files into teh STDOUT stream.",
    )
    parser.add_argument(
        "-t",
        "--temp",
        action="store_true",
        help="In-place clean via .tmp swap, then write back",
    )
    parser.add_argument(
        "-p",
        "--preserve-tmp",
        action="store_true",
        help="With -t, keep the .tmp file after success",
    )

    # Audit
    parser.add_argument(
        "--report", action="store_true", help="Audit counts per category (no changes)"
    )

    fmt = parser.add_mutually_exclusive_group()
    fmt.add_argument(
        "--csv", action="store_true", help="With --report, emit CSV (one row per file)"
    )
    fmt.add_argument("--json", action="store_true", help="With --report, emit JSON")
    parser.add_argument(
        "--label",
        help="When reading from STDIN ('-'), use this display name in report/CSV",
    )

    parser.add_argument(
        "--threshold",
        type=int,
        default=None,
        help="With --report, exit 1 if total anomalies >= N",
    )
    parser.add_argument(
        "--metrics", action="store_true", help="Include semantic metrics in report"
    )
    parser.add_argument(
        "--metrics-help", action="store_true", help="Explain metrics and arrows (↑/↓)."
    )
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Always exit with code 0 (useful for pre-commit reporting)",
    )

    # Output control
    parser.add_argument(
        "--no-color", action="store_true", help="Disable ANSI colors (plain output)"
    )

    # Logging
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress status lines on stderr"
    )

    args = parser.parse_args()
    log._quiet = bool(args.quiet)

    # Metrics help: print and exit (stdout, honors --no-color)
    if args.metrics_help:
        print_metrics_help(no_color=args.no_color)
        sys.exit(0)

    if args.report:
        if args.csv and args.json:
            log("[✗] --csv and --json are mutually exclusive.")
            sys.exit(2)
        files = args.infile or ["-"]
        code = run_report(
            files,
            json_mode=args.json,
            csv_mode=args.csv,
            threshold=args.threshold,
            metrics=args.metrics,
            no_color=args.no_color,
            display_label=args.label,
            warn_only=args.exit_zero,
        )  # <-- use label for display
        sys.exit(0 if args.exit_zero else code)

    # STDIN → STDOUT filter mode when no files provided
    if not args.infile:
        run_filter_mode(args)
        sys.exit(0)

    if args.output and args.output != "-" and len(args.infile) > 1:
        log("[✗] -o/--output with a filename is only allowed for a single input file.")
        sys.exit(1)

    seen = set()
    for infile in args.infile:
        if infile in seen:
            log(f"[!] Skipping duplicate: {infile}")
            continue
        seen.add(infile)
        process_file(infile, args)


if __name__ == "__main__":
    main()
