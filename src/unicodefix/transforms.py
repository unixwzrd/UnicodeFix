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
) -> str:
    """
    Normalize problematic/invisible Unicode to safe ASCII where appropriate.
    """
    _require_ftfy()
    text = ftfy.fix_text(text)

    # Quote normalization (deduped)
    if not preserve_quotes:
        # Pass 1: explicit fast translations
        QUOTE_ELLIPSIS_MAP = {
            "\u2018": "'", "\u2019": "'", "\u201B": "'", "\u201A": "'",
            "\u2039": "'", "\u203A": "'", "\u02BC": "'", "\uFF07": "'",
            "\u201C": '"', "\u201D": '"', "\u201E": '"', "\u201F": '"',
            "\u00AB": '"', "\u00BB": '"', "\uFF02": '"',
            "\u2026": "...", "\u22EF": "...", "\u2025": "..",
        }
        text = text.translate(str.maketrans(QUOTE_ELLIPSIS_MAP))

        # Pass 2: fallback only for remaining opening/closing punctuation
        mapped = []
        for ch in text:
            if unicodedata.category(ch) in ("Pi", "Pf"):
                name = unicodedata.name(ch, "")
                if "DOUBLE" in name:
                    mapped.append('"')
                elif "SINGLE" in name or "PRIME" in name:
                    mapped.append("'")
                else:
                    mapped.append('"')  # safe default
            else:
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
