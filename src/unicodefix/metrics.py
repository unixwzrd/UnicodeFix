"""
Semantic metrics for --report --metrics.
Requires nltk. Install with: pip install unicodefix[nlp]
"""

from __future__ import annotations

import math
import re
from collections import Counter

import nltk  # type: ignore

from unicodefix.nlp import init_nltk

# Ensure resources on import
init_nltk()

# --- tokenization helpers
_WORD_RE = re.compile(r"\w+", re.UNICODE)
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _words(text: str):
    # NLTK's tokenizer handles quotes/dashes better than regex
    return nltk.word_tokenize(text)


def _sentences(text: str):
    return nltk.sent_tokenize(text)


def _stopwords():
    try:
        from nltk.corpus import stopwords  # type: ignore
        return set(stopwords.words("english"))
    except Exception:
        return set()


# --- core metrics
def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def ascii_ratio(s: str) -> float:
    if not s:
        return 1.0
    return sum(1 for ch in s if ord(ch) < 128) / len(s)


def ttr(tokens) -> float:
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def avg_token_len(tokens) -> float:
    if not tokens:
        return 0.0
    return sum(len(t) for t in tokens) / len(tokens)


def avg_sentence_len(tokens, sentences) -> float:
    if not sentences:
        return float(len(tokens))
    return len(tokens) / len(sentences)


# --- auxiliary features for ai_score
def punctuation_ratio(text: str) -> float:
    if not text:
        return 0.0
    return len(_PUNCT_RE.findall(text)) / len(text)


def stopword_ratio(tokens) -> float:
    if not tokens:
        return 0.0
    sw = _stopwords()
    if not sw:
        return 0.0
    return sum(1 for t in tokens if t.lower() in sw) / len(tokens)


def repetition_ratio(tokens) -> float:
    """Share of tokens accounted for by the top 5 most frequent tokens (lowercased)."""
    if not tokens:
        return 0.0
    counts = Counter(t.lower() for t in tokens)
    top5 = sum(c for _, c in counts.most_common(5))
    return top5 / len(tokens)


def sentence_len_cv(tokens, sentences) -> float:
    """Coefficient of variation of sentence lengths (in tokens): std/mean."""
    if not sentences:
        return 0.0
    # Rough per-sentence tokenization
    lens = []
    start = 0
    toks = tokens
    # Simple split: distribute tokens evenly by sentence count (cheap and robust enough)
    per = max(1, len(toks) // max(1, len(sentences)))
    for i in range(len(sentences) - 1):
        lens.append(per)
    lens.append(len(toks) - per * (len(sentences) - 1))
    if not lens:
        return 0.0
    mean = sum(lens) / len(lens)
    if mean == 0:
        return 0.0
    var = sum((x - mean) ** 2 for x in lens) / len(lens)
    std = math.sqrt(var)
    return std / mean


def digits_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(ch.isdigit() for ch in text) / len(text)


# --- heuristic AI-likeness score
def ai_score(text: str, tokens, sentences) -> float:
    """
    Heuristic 0..1 "AI-like" score:
      - higher repetition → more AI-like
      - lower TTR → more AI-like
      - lower sentence-length variance (lower burstiness) → more AI-like
      - moderate punctuation usage
      - stopword ratio near common English range
    This is NOT a detector—just a rough ranking signal.
    """
    if not tokens:
        return 0.0

    # base features
    ttr_v = ttr(tokens)                       # 0..1 (higher = more human/diverse)
    rep_v = repetition_ratio(tokens)          # 0..1 (higher = more repetitive = more AI-like)
    cv_v  = sentence_len_cv(tokens, sentences) # 0..inf (lower = more AI-like)
    punc  = punctuation_ratio(text)           # ~0..0.2 typical
    swr   = stopword_ratio(tokens)            # ~0.3..0.6 typical English
    # normalize-ish
    ttr_h = 1 - min(max(ttr_v, 0.0), 1.0)     # invert so higher = more AI-like
    rep_h = min(max(rep_v, 0.0), 1.0)
    cv_h  = 1 - min(cv_v / 1.0, 1.0)          # treat CV<=1 as fully AI-like, >1 bleeds to 0
    punc_h = 1 - min(abs(punc - 0.05) / 0.05, 1.0)  # 0.05 sweet spot
    swr_h  = 1 - min(abs(swr - 0.45) / 0.25, 1.0)   # 0.45 sweet spot

    # weights (sum ~1)
    w_ttr, w_rep, w_cv, w_punc, w_swr = 0.25, 0.30, 0.20, 0.15, 0.10
    score = (w_ttr * ttr_h) + (w_rep * rep_h) + (w_cv * cv_h) + (w_punc * punc_h) + (w_swr * swr_h)
    return round(max(0.0, min(1.0, score)), 3)


# --- public API
def compute_metrics(text: str) -> dict:
    tokens = _words(text)
    sents = _sentences(text)
    return {
        "entropy": round(shannon_entropy(text), 4),
        "ascii_ratio": round(ascii_ratio(text), 4),
        "type_token_ratio": round(ttr(tokens), 4),
        "avg_token_len": round(avg_token_len(tokens), 4),
        "avg_sentence_len_tokens": round(avg_sentence_len(tokens, sents), 4),
        "tokens": len(tokens),
        "sentences": len(sents),

        # extra features useful for ranking
        "punctuation_ratio": round(punctuation_ratio(text), 4),
        "stopword_ratio": round(stopword_ratio(tokens), 4),
        "repetition_ratio": round(repetition_ratio(tokens), 4),
        "sentence_len_cv": round(sentence_len_cv(tokens, sents), 4),
        "digits_ratio": round(digits_ratio(text), 4),

        # heuristic overall score
        "ai_score": ai_score(text, tokens, sents),
    }
