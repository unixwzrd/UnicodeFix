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

# Check for unidecode dependency early, with a clear message if missing
try:
    from unidecode import unidecode  # noqa: F401
except ImportError:
    print(
        "[✗] Missing dependency: 'Unidecode'. Please install it with:\n"
        "    pip install Unidecode\n"
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


def clean_text(text: str, preserve_invisible: bool = False) -> str:
    """
    Normalize problematic or invisible Unicode characters to safe ASCII equivalents.

    Args:
        text (str): The input text containing Unicode characters
        preserve_invisible (bool): If True, do not remove invisible characters

    Returns:
        str: The cleaned text with normalized ASCII characters
    """
    replacements = {
        '\u2018': "'", '\u2019': "'",  # Smart single quotes
        '\u201C': '"', '\u201D': '"',  # Smart double quotes
        '\u2011': '-',                   # Non-breaking hyphen to regular hyphen
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)

    # Replace EM dashes (U+2014) with space-dash-space, unless already surrounded by spaces
    def em_dash_replacer(match):
        before = match.group(1)
        after = match.group(2)
        if before and after:
            return before + '-' + after
        return ' - '
    text = re.sub(r'(\s*)\u2014(\s*)', em_dash_replacer, text)

    # Replace EN dashes (U+2013) with plain dash, preserving spacing
    text = re.sub(r'\u2013', '-', text)

    if not preserve_invisible:
        # Remove zero-width and other invisible characters
        text = re.sub(r'[\u200B\u200C\u200D\uFEFF\u00A0]', '', text)

    # Remove trailing whitespace on every line
    text = re.sub(r'[ \t]+(\r?\n)', r'\1', text)

    return text


def ensure_single_newline(text: str) -> str:
    """
    Ensure the text ends with exactly one newline character. Used for all text files.
    """
    return text.rstrip('\r\n') + '\n'


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
        help="Preserve invisible Unicode characters (zero-width, non-breaking, etc.)"
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
    parser.add_argument(
        "-n", "--no-newline",
        action="store_true",
        help="Do not add a newline at the end of the output file (suppress final newline)."
    )
    args = parser.parse_args()

    if not args.infile:
        # No files provided: filter mode (STDIN to STDOUT)
        raw = sys.stdin.read()
        cleaned = clean_text(raw, preserve_invisible=args.invisible)
        # Add or suppress newline at EOF based on -n/--no-newline
        if not args.no_newline:
            cleaned = ensure_single_newline(cleaned)
        else:
            cleaned = cleaned.rstrip('\r\n')
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
                cleaned = clean_text(raw, preserve_invisible=args.invisible)
                cleaned = ensure_single_newline(cleaned)
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
            cleaned = clean_text(raw, preserve_invisible=args.invisible)
            # Add or suppress newline at EOF based on -n/--no-newline
            if not args.no_newline:
                cleaned = ensure_single_newline(cleaned)
            else:
                cleaned = cleaned.rstrip('\r\n')

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
