#!/usr/bin/env python

"""
Unicode Text Cleaner

This script normalizes problematic Unicode characters to their ASCII equivalents.
It handles common issues like fancy quotes, em/en dashes, and zero-width spaces
that can cause problems in text processing.

The script takes one or more input files and creates cleaned versions with
".clean.txt" appended to the original filename. It skips duplicate files
and handles errors gracefully.

Example:
    $ python cleanup-text.py file1.txt file2.txt
    [✓] Cleaned: file1.txt → file1.clean.txt
    [✓] Cleaned: file2.txt → file2.clean.txt
"""

import argparse
import os
import re
import sys
import unicodedata

# Check for ftfy dependency early, with a clear message if missing
try:
    import ftfy
except ImportError:
    print(
        "[✗] Missing dependency: 'ftfy'. Please install it with:\n"
        "    pip install ftfy\n"
        "Or install all requirements with:\n"
        "    pip install -r requirements.txt",
        file=sys.stderr
    )
    sys.exit(1)


class CustomArgumentParser(argparse.ArgumentParser):
    def print_help(self, file=None):
        if file is None:
            file = sys.stderr
        print('', file=file)  # Blank line before help
        super().print_help(file)
        print('', file=file)  # Blank line after help

    def exit(self, status=0, message=None):
        if message:
            print('', file=sys.stderr)  # Blank line before error/usage
            self._print_message(message, sys.stderr)
            print('', file=sys.stderr)  # Blank line after error/usage
        sys.exit(status)


def clean_text(
    text: str,
    preserve_invisible: bool = False,
    preserve_quotes: bool = False,
    preserve_dashes: bool = False,
) -> str:
    """
    Normalize problematic or invisible Unicode characters to safe ASCII equivalents.

    Args:
        text (str): The input text containing Unicode characters
        preserve_invisible (bool): If True, do not remove invisible characters

    Returns:
        str: The cleaned text with normalized ASCII characters
    """
    # Use ftfy for intelligent text fixing and normalization
    text = ftfy.fix_text(text)

    # Handle specific cases for shell-friendliness
    # Quote normalization
    if not preserve_quotes:
        replacements = {
            # Smart/apostrophe variants → '
            '\u2018': "'", '\u2019': "'", '\u201B': "'", '\u201A': "'",
            '\u2039': "'", '\u203A': "'", '\u02BC': "'", '\uFF07': "'",
            # Double-quote variants → "
            '\u201C': '"', '\u201D': '"', '\u201E': '"', '\u201F': '"',
            '\u00AB': '"', '\u00BB': '"', '\uFF02': '"',
            # Ellipsis variants → '...'
            '\u2026': '...',  # Horizontal Ellipsis
            '\u22EF': '...',  # MiDline Horizontal Ellipsis
            '\u2025': '..',   # Two Dot Leader
        }
        for orig, repl in replacements.items():
            text = text.replace(orig, repl)

        # Fallback: map any remaining Unicode quote punctuation to ASCII
        single_like = {
            '\u2018', '\u2019', '\u201B', '\u201A', '\u2039', '\u203A', '\u02BC', '\uFF07', '\u2032', '\u2035'
        }
        double_like = {
            '\u201C', '\u201D', '\u201E', '\u201F', '\u00AB', '\u00BB', '\uFF02', '\u2033', '\u2036'
        }
        mapped_chars = []
        for ch in text:
            cat = unicodedata.category(ch)
            if cat in ("Pi", "Pf"):
                cp = f"\\u{ord(ch):04X}"
                if cp in single_like:
                    mapped_chars.append("'")
                elif cp in double_like:
                    mapped_chars.append('"')
                else:
                    mapped_chars.append('"')
            else:
                mapped_chars.append(ch)
        text = ''.join(mapped_chars)

    # Dash normalization
    if not preserve_dashes:
        # Replace EM dash with space-dash-space unless already spaced
        def em_dash_replacer(match):
            before = match.group(1)
            after = match.group(2)
            if before and after:
                return before + '-' + after
            return ' - '
        text = re.sub(r'(\s*)\u2014(\s*)', em_dash_replacer, text)
        # EN dash → '-'
        text = re.sub(r'\u2013', '-', text)

    # Normalize Unicode spaces: map all Zs separators to ASCII space
    text = re.sub(r"[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]", " ", text)

    if not preserve_invisible:
        # Remove zero-width and bidi/invisible controls
        text = re.sub(r"[\u200B\u200C\u200D\uFEFF\u200E\u200F\u202A-\u202E\u2066-\u2069]", "", text)

    # Remove trailing whitespace on every line
    text = re.sub(r'[ \t]+(\r?\n)', r'\1', text)

    return text


def handle_newlines(text: str, no_newline: bool = False) -> str:
    """
    Handle newline at EOF based on flags and environment.

    Args:
        text (str): The text to process
        no_newline (bool): If True, don't add any newlines

    Returns:
        str: Text with appropriate newline handling
    """
    if no_newline:
        return text  # Leave exactly as is

    # Only add newline if there isn't one already
    if not text.endswith('\n'):
        text += '\n'
    return text


def main():
    """
    Main function that handles command-line interface and file processing.
    """
    parser = CustomArgumentParser(
        description=(
            "Clean Unicode quirks from text.\n"
            "If no input files are given, reads from STDIN and writes to STDOUT (filter mode).\n"
            "If input files are given, creates cleaned files with .clean before the extension "
            "(e.g., foo.txt -> foo.clean.txt).\n"
            "Use -o - to force output to STDOUT for all input files, or -o <file> to specify a single output file "
            "(only with one input file)."
        ),
        epilog="\n"
    )
    parser.add_argument("infile", nargs="*", help="Input file(s)")
    parser.add_argument(
        "-i", "--invisible",
        action="store_true",
        help="Preserve invisible Unicode characters (zero-width, bidi controls, etc.)"
    )
    parser.add_argument(
        "-Q", "--keep-smart-quotes",
        action="store_true",
        help="Preserve Unicode smart quotes (do not convert to ASCII)"
    )
    parser.add_argument(
        "-D", "--keep-dashes",
        action="store_true",
        help="Preserve Unicode EN/EM dashes (do not convert to ASCII)"
    )
    parser.add_argument(
        "-n", "--no-newline",
        action="store_true",
        help="Do not add a newline at the end of the output file (suppress final newline)."
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file name, or '-' for STDOUT. Only valid with one input file, or use '-' for STDOUT with multiple files."
    )
    parser.add_argument(
        "-t", "--temp",
        action="store_true",
        help=(
            "In-place cleaning:\n"
            "  Move each input file to .tmp, clean it, write cleaned output to original name,\n"
            "  and delete .tmp after success."
        )
    )
    parser.add_argument(
        "-p", "--preserve-tmp",
        action="store_true",
        help=(
            "With -t, preserve the .tmp file after cleaning (do not delete it).\n"
            "  Useful for backup or manual recovery."
        )
    )
    args = parser.parse_args()

    if not args.infile:
        # No files provided: filter mode (STDIN to STDOUT)
        raw = sys.stdin.read()
        cleaned = clean_text(
            raw,
            preserve_invisible=args.invisible,
            preserve_quotes=args.keep_smart_quotes,
            preserve_dashes=args.keep_dashes,
        )
        # VS Code compensation only in filter mode (skip in CI/CD)
        vscode_extension = False
        process_title = os.environ.get('VSCODE_PROCESS_TITLE', '')
        app_insights = os.environ.get('APPLICATION_INSIGHTS_NO_DIAGNOSTIC_CHANNEL', '')
        if process_title.startswith('extension-host') and app_insights != 'true':
            vscode_extension = True

        # Base newline handling
        cleaned = handle_newlines(cleaned, args.no_newline)
        # VS Code compensation only in filter mode
        if not args.no_newline and vscode_extension:
            cleaned += '\n'
        sys.stdout.write(cleaned)
        return

    if args.output and args.output != '-' and len(args.infile) > 1:
        print(
            "[✗] -o/--output with a filename is only allowed when processing a single input file.",
            file=sys.stderr
        )
        sys.exit(1)

    seen = set()
    for infile in args.infile:
        if infile in seen:
            print(f"[!] Skipping duplicate: {infile}")
            continue
        seen.add(infile)

        try:
            if args.temp:
                tmpfile = infile + ".tmp"
                os.rename(infile, tmpfile)
                with open(tmpfile, "r", encoding="utf-8", errors="replace") as f:
                    raw = f.read()
                cleaned = clean_text(
                    raw,
                    preserve_invisible=args.invisible,
                    preserve_quotes=args.keep_smart_quotes,
                    preserve_dashes=args.keep_dashes,
                )
                cleaned = handle_newlines(cleaned, args.no_newline)
                with open(infile, "w", encoding="utf-8") as f:
                    f.write(cleaned)
                print(f"[✓] Cleaned (in-place): {infile}")
                if not args.preserve_tmp:
                    os.remove(tmpfile)
                else:
                    print(f"[i] Preserved temp file: {tmpfile}")
                continue

            with open(infile, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            cleaned = clean_text(
                raw,
                preserve_invisible=args.invisible,
                preserve_quotes=args.keep_smart_quotes,
                preserve_dashes=args.keep_dashes,
            )
            cleaned = handle_newlines(cleaned, args.no_newline)

            if args.output:
                if args.output == '-':
                    sys.stdout.write(cleaned)
                    continue
                else:
                    outfile = args.output
            else:
                base, ext = os.path.splitext(infile)
                outfile = f"{base}.clean{ext}"

            with open(outfile, "w", encoding="utf-8") as f:
                f.write(cleaned)
            print(f"[✓] Cleaned: {infile} → {outfile}")
        except Exception as e:
            print(f"[✗] Failed to process {infile}: {e}")


if __name__ == '__main__':
    main()
