"""
NLTK bootstrap, parallel to ftfy's require pattern.
Installed via optional extra: pip install unicodefix[nlp]
"""

_nltk_err = None
try:
    import nltk  # type: ignore
except Exception as e:
    nltk = None  # type: ignore
    _nltk_err = e


def init_nltk():
    """
    Ensure nltk is importable and required models are present.
    Downloads missing models quietly. Raises RuntimeError if nltk missing.
    """
    if nltk is None:
        raise RuntimeError(
            "Missing dependency 'nltk'. Install with: pip install unicodefix[nlp]"
        ) from _nltk_err

    required = ("punkt", "stopwords", "wordnet", "averaged_perceptron_tagger")
    for pkg in required:
        try:
            if pkg == "punkt":
                nltk.data.find("tokenizers/punkt")
            else:
                nltk.data.find(f"corpora/{pkg}")
        except LookupError:
            nltk.download(pkg, quiet=True)
    return nltk
