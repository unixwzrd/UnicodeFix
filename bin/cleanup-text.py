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

from unidecode import unidecode


def clean_text(text: str) -> str:
    """
    Normalize problematic or invisible Unicode characters to safe ASCII equivalents.

    This function performs two main operations:
    1. Converts typographic characters (quotes, dashes) to their ASCII equivalents
    2. Removes zero-width and invisible Unicode characters

    Args:
        text (str): The input text containing Unicode characters

    Returns:
        str: The cleaned text with normalized ASCII characters

    Example:
        >>> clean_text('"Hello" — World')
        '"Hello" - World'
    """
    replacements = {
        '\u2018': "'", '\u2019': "'",  # Smart single quotes
        '\u201C': '"', '\u201D': '"',  # Smart double quotes
        '\u2013': '-', '\u2014': '-',  # En and em dashes
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)

    # Remove zero-width characters
    text = re.sub(r'[\u200B\u200C\u200D\uFEFF]', '', text)

    # Remove trailing whitespace on every line
    text = re.sub(r'[ \t]+(\r?\n)', r'\1', text)

    return text


def main():
    """
    Main function that handles command-line interface and file processing.

    Parses command line arguments, processes input files, and creates cleaned
    output files. Handles duplicate files and errors gracefully with informative
    messages.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Clean Unicode quirks from text.")
    parser.add_argument("infile", nargs="*", help="Input file(s)")
    args = parser.parse_args()

    if not args.infile:
        # No files provided: filter mode (STDIN to STDOUT)
        import sys
        raw = sys.stdin.read()
        cleaned = clean_text(raw)
        sys.stdout.write(cleaned)
        return

    seen = set()
    for infile in args.infile:
        if infile in seen:
            print(f"[!] Skipping duplicate: {infile}")
            continue
        seen.add(infile)

        try:
            with open(infile, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            cleaned = clean_text(raw)

            base, _ = os.path.splitext(infile)
            outfile = base + ".clean.txt"
            with open(outfile, "w", encoding="utf-8") as f:
                f.write(cleaned)
            print(f"[✓] Cleaned: {infile} → {outfile}")
        except Exception as e:
            print(f"[✗] Failed to process {infile}: {e}")


if __name__ == '__main__':
    main()
