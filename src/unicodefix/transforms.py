import re
import unicodedata

# Import ftfy lazily but give a clear error if missing
_ftfy_err = None
try:
    import ftfy
except Exception as e:
    ftfy = None
    _ftfy_err = e


def _require_ftfy():
    if ftfy is None:
        raise RuntimeError(
            "Missing dependency 'ftfy'. Install with `pip install ftfy` "
            "or install the package: `pip install unicodefix`."
        ) from _ftfy_err


def clean_text(
    text: str,
    preserve_invisible: bool = False,
    preserve_quotes: bool = False,
    preserve_dashes: bool = False,
    preserve_fullwidth_brackets: bool = False,
    preserve_replacement_chars: bool = False,
) -> str:
    """
    Normalize problematic/invisible Unicode to safe ASCII where appropriate.
    """
    _require_ftfy()
    text = ftfy.fix_text(text)

    # Remove Unicode replacement characters (U+FFFD) by default
    # These indicate invalid/undecodable bytes and should be removed
    # Do this early, right after ftfy fixes encoding issues
    if not preserve_replacement_chars:
        text = text.replace("\ufffd", "")  # U+FFFD REPLACEMENT CHARACTER
        text = text.replace("\uFFFD", "")  # Same, different case (case-insensitive check)

    # Quote normalization - aggressive by default
    if not preserve_quotes:
        # Pass 1: comprehensive explicit map for all known quote variants
        QUOTE_ELLIPSIS_MAP = {
            # Single quotes / apostrophes
            "\u2018": "'",  # LEFT SINGLE QUOTATION MARK
            "\u2019": "'",  # RIGHT SINGLE QUOTATION MARK
            "\u201B": "'",  # SINGLE HIGH-REVERSED-9 QUOTATION MARK
            "\u201A": "'",  # SINGLE LOW-9 QUOTATION MARK
            "\u2039": "'",  # SINGLE LEFT-POINTING ANGLE QUOTATION MARK
            "\u203A": "'",  # SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
            "\u02BC": "'",  # MODIFIER LETTER APOSTROPHE
            "\uFF07": "'",  # FULLWIDTH APOSTROPHE
            "\u02BB": "'",  # MODIFIER LETTER TURNED COMMA
            "\u02BD": "'",  # MODIFIER LETTER REVERSED COMMA
            "\u02BE": "'",  # MODIFIER LETTER RIGHT HALF RING
            "\u02BF": "'",  # MODIFIER LETTER LEFT HALF RING
            "\u02C8": "'",  # MODIFIER LETTER VERTICAL LINE
            "\u02EE": "'",  # MODIFIER LETTER DOUBLE APOSTROPHE
            "\u05F3": "'",  # HEBREW PUNCTUATION GERESH
            "\u1FBF": "'",  # GREEK PSILI
            "\u1FFE": "'",  # GREEK DASIA
            # Double quotes
            "\u201C": '"',  # LEFT DOUBLE QUOTATION MARK
            "\u201D": '"',  # RIGHT DOUBLE QUOTATION MARK
            "\u201E": '"',  # DOUBLE LOW-9 QUOTATION MARK
            "\u201F": '"',  # DOUBLE HIGH-REVERSED-9 QUOTATION MARK
            "\u00AB": '"',  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
            "\u00BB": '"',  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
            "\uFF02": '"',  # FULLWIDTH QUOTATION MARK
            "\u301D": '"',  # REVERSED DOUBLE PRIME QUOTATION MARK
            "\u301E": '"',  # DOUBLE PRIME QUOTATION MARK
            "\u301F": '"',  # LOW DOUBLE PRIME QUOTATION MARK
            "\u05F4": '"',  # HEBREW PUNCTUATION GERSHAYIM
            # Ellipses
            "\u2026": "...",  # HORIZONTAL ELLIPSIS
            "\u22EF": "...",  # MIDLINE HORIZONTAL ELLIPSIS
            "\u2025": "..",   # TWO DOT LEADER
        }
        text = text.translate(str.maketrans(QUOTE_ELLIPSIS_MAP))

        # Pass 2: aggressive fallback - catch ANY remaining quote-like characters
        # Normalize quotes even if they're in extended ASCII range (they're problematic)
        mapped = []
        for ch in text:
            code = ord(ch)

            # Get Unicode name for pattern matching (even for extended ASCII)
            try:
                name = unicodedata.name(ch, "").upper()
            except ValueError:
                name = ""

            # Check for quote/apostrophe patterns in name (including extended ASCII quotes)
            is_quote_like = any(pattern in name for pattern in [
                "QUOTATION", "QUOTE", "APOSTROPHE", "PRIME", "GERSH", "DASIA", "PSILI"
            ])

            # Also check category for Pi/Pf (initial/final punctuation) that might be quotes
            is_pi_pf = unicodedata.category(ch) in ("Pi", "Pf")

            if is_quote_like or is_pi_pf:
                # Determine if single or double based on name
                if "DOUBLE" in name or "GERSHAYIM" in name:
                    mapped.append('"')
                elif "SINGLE" in name or "APOSTROPHE" in name or "PRIME" in name or "GERSH" in name or "DASIA" in name or "PSILI" in name:
                    mapped.append("'")
                elif is_pi_pf:
                    # For Pi/Pf without clear name match, default to double quote
                    mapped.append('"')
                else:
                    # Default to double quote for ambiguous cases
                    mapped.append('"')
            elif code <= 255:
                # Preserve ASCII (0-127) and extended ASCII (128-255) that aren't quotes
                mapped.append(ch)
            else:
                # Preserve other Unicode characters (non-quote, non-problematic)
                mapped.append(ch)
        text = "".join(mapped)

    # Dash normalization
    if not preserve_dashes:
        text = re.sub(r"\s*\u2014\s*", " - ", text)  # EM → space-dash-space
        text = text.replace("\u2013", "-")           # EN → dash

    # Fold select fullwidth punctuation that affects monospace alignment
    if not preserve_fullwidth_brackets:
        FULLWIDTH_FOLD = {
            "\u3010": "[",  # 【
            "\u3011": "]",  # 】
        }
        if any(ch in text for ch in FULLWIDTH_FOLD):
            text = text.translate(str.maketrans(FULLWIDTH_FOLD))

    # Zs separators → ASCII space
    text = re.sub(r"[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]", " ", text)

    if not preserve_invisible:
        # Remove zero-width, bidi, and control invisibles
        text = re.sub(r"[\u200B-\u200D\uFEFF\u200E\u200F\u202A-\u202E\u2066-\u2069]", "", text)

    # Remove invalid/unassigned/private-use Unicode characters
    # These can appear when decoding is corrupted or bytes are invalid
    cleaned_chars = []
    for char in text:
        code = ord(char)

        # Always preserve common control characters (newlines, tabs, etc.)
        # These are essential for text structure even if they don't have Unicode names
        if code < 32 and char in '\n\r\t':
            cleaned_chars.append(char)
            continue

        # Check if character is valid and assigned
        try:
            name = unicodedata.name(char)
            category = unicodedata.category(char)
        except ValueError:
            # Character has no Unicode name (invalid/unassigned)
            # Skip it unless it's a basic printable ASCII character
            if code < 128 and char.isprintable():
                cleaned_chars.append(char)
            # Otherwise skip invalid characters
            continue

        # Skip private use area characters (often artifacts from encoding issues)
        # Private Use Areas: U+E000-U+F8FF, U+F0000-U+FFFFD, U+100000-U+10FFFD
        if (0xE000 <= code <= 0xF8FF) or (0xF0000 <= code <= 0xFFFFD) or (0x100000 <= code <= 0x10FFFD):
            continue

        # Skip unassigned characters (category "Cn" = "Other, not assigned")
        if category == "Cn" and code > 0x007F:  # Allow ASCII control chars to pass through if printable
            continue

        # Skip surrogates (shouldn't appear in valid UTF-8, but check anyway)
        if 0xD800 <= code <= 0xDFFF:
            continue

        # Keep the character
        cleaned_chars.append(char)

    text = "".join(cleaned_chars)

    # Strip trailing spaces/tabs on each line
    text = re.sub(r"[ \t]+(\r?\n)", r"\1", text)

    # Remove whitespace-only lines' spaces/tabs (keep the newline)
    text = re.sub(r"^[ \t]+(\r?\n)", r"\1", text, flags=re.MULTILINE)

    # If the file ends with spaces/tabs but no newline yet, drop them before
    # newline handling so the final line is truly blank (no trailing space)
    text = re.sub(r"[ \t]+$", "", text)

    return text


def handle_newlines(text: str, no_newline: bool = False) -> str:
    """
    Ensure a final newline unless suppressed, preserving CR/LF styles if already present.
    """
    if no_newline:
        return text
    return text if text.endswith(("\n", "\r", "\r\n")) else text + "\n"


def fold_for_terminal_display(text: str) -> str:
    """
    Fold a minimal set of width-breaking Unicode punctuation for better terminal alignment.
    - Fullwidth square brackets 【】 → ASCII [].
    - Intentionally does not touch † (dagger) and similar glyphs.
    """
    mapping = {
        "\u3010": "[",  # 【
        "\u3011": "]",  # 】
    }
    return text.translate(str.maketrans(mapping))
