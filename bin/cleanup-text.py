#!/usr/bin/env python3
import sys
import argparse
import re
from unidecode import unidecode

def clean_text(text):
    replacements = {
        '\u2018': "'", '\u2019': "'",
        '\u201C': '"', '\u201D': '"',
        '\u2013': '-', '\u2014': '-',
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    text = re.sub(r'[\u200B\u200C\u200D\uFEFF]', '', text)
    return unidecode(text)

def main():
    parser = argparse.ArgumentParser(description="Clean Unicode quirks from text.")
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin,
                        help='Input file (or use STDIN)')
    parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout,
                        help='Output file (default: STDOUT)')
    args = parser.parse_args()

    input_text = args.infile.read()
    cleaned = clean_text(input_text)
    args.output.write(cleaned)

if __name__ == '__main__':
    main()