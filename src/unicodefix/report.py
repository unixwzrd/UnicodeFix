import csv
import json
import os
import sys

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Column, Table
from rich.text import Text

__all__ = ["print_human", "print_json", "print_metrics_help", "print_csv"]

# Fixed column widths (as preferred)
CAT_COL_WIDTH = 24      # left column width (Category / Metric)
VALUE_COL_WIDTH = 8     # right-justified numeric column width (Total / Value)

# Optional clamped body width (unset or 0 = no clamping)
# e.g. UNICODEFIX_WIDTH=96 to create side margins on wide terminals
REPORT_BODY_WIDTH = int(os.environ.get("UNICODEFIX_WIDTH", "0"))

_SPECIAL_NAMES = {
    "ai_score": "AI score",
    "ascii_ratio": "ASCII ratio",
    "avg_sentence_len_tokens": "Avg sentence len (tokens)",
    "avg_token_len": "Avg token len",
    "type_token_ratio": "Type–token ratio",
    "sentence_len_cv": "Sentence len CV",
}


# -------------------- Console / helpers --------------------
def _console(no_color: bool) -> Console:
    return Console(no_color=no_color)


def _sumv(d: dict) -> int:
    return sum(int(v) for v in d.values())


def _sev_count(v: int | str) -> str:
    """Severity color for integer counts (or status markers '/' / 'X')."""
    if isinstance(v, str) and v in {"X", "/"}:
        return "blue"
    n = int(v)
    if n == 0:
        return "green"
    if n <= 2:
        return "yellow3"
    return "red"


def _sev_ratio(name: str, x: float) -> str:
    if name == "ai_score":
        return "green" if x < 0.40 else ("yellow3" if x < 0.70 else "red")
    if name == "type_token_ratio":
        return "red" if x < 0.35 else ("yellow3" if x < 0.50 else "green")
    if name == "repetition_ratio":
        return "green" if x < 0.20 else ("yellow3" if x < 0.35 else "red")
    if name == "sentence_len_cv":
        return "red" if x <= 0.15 else ("yellow3" if x <= 0.30 else "green")
    if name == "stopword_ratio":
        return "red" if (x < 0.20 or x > 0.70) else ("yellow3" if (x < 0.30 or x > 0.60) else "green")
    if name == "punctuation_ratio":
        return "red" if (x < 0.01 or x > 0.15) else ("yellow3" if (x < 0.02 or x > 0.08) else "green")
    if name == "ascii_ratio":
        return "red" if x < 0.80 else ("yellow3" if x < 0.95 else "green")
    if name == "digits_ratio":
        return "green" if x <= 0.05 else ("yellow3" if x <= 0.20 else "red")
    if name == "avg_sentence_len_tokens":
        return "red" if (x < 8 or x > 45) else ("yellow3" if (x < 12 or x > 30) else "green")
    return ""


def _fmt_float(val) -> str:
    return f"{float(val):.4f}"


def _overall_score(metrics: dict) -> float:
    """Heuristic blend—transparent & tunable."""
    base = float(metrics.get("ai_score", 0.0) or 0.0)
    ttr  = float(metrics.get("type_token_ratio", 0.0) or 0.0)
    rep  = float(metrics.get("repetition_ratio", 0.0) or 0.0)
    cv   = float(metrics.get("sentence_len_cv", 0.0) or 0.0)
    score = base + 0.20 * rep + 0.20 * max(0.0, 0.55 - ttr) + 0.15 * max(0.0, 0.20 - cv)
    return max(0.0, min(1.0, score))


def _pretty_metric(name: str) -> str:
    if name in _SPECIAL_NAMES:
        return _SPECIAL_NAMES[name]
    return name.replace("_", " ").title()


def _cols_for_anomalies():
    """Locked columns for anomalies + summary so numbers align exactly."""
    return (
        Column("Category", style="bold", no_wrap=True,
               width=CAT_COL_WIDTH, min_width=CAT_COL_WIDTH, max_width=CAT_COL_WIDTH),
        Column("Total", justify="right", no_wrap=True,
               width=VALUE_COL_WIDTH, min_width=VALUE_COL_WIDTH, max_width=VALUE_COL_WIDTH),
        Column("Details", overflow="fold", no_wrap=False),
    )


def _cols_for_metrics(signal_w: int):
    """Locked columns for metrics + overall score."""
    return (
        Column("Metric", no_wrap=True,
               width=CAT_COL_WIDTH, min_width=CAT_COL_WIDTH, max_width=CAT_COL_WIDTH),
        Column("Value", justify="right", no_wrap=True,
               width=VALUE_COL_WIDTH, min_width=VALUE_COL_WIDTH, max_width=VALUE_COL_WIDTH),
        Column("Signal", max_width=signal_w, no_wrap=False, overflow="fold"),
    )


def _clamp_body_width(con: Console) -> int:
    """Return target body width. 0 = no clamp (use terminal width)."""
    term = con.width or 80
    if REPORT_BODY_WIDTH <= 0:
        return term
    return min(term, REPORT_BODY_WIDTH)


def _print_clamped(con: Console, renderable, body_w: int) -> None:
    """Left-align inside a fixed-width block to create side margins on wide terminals."""
    if REPORT_BODY_WIDTH <= 0:
        # No clamping requested: just print as-is (full terminal width)
        con.print(renderable)
    else:
        con.print(Align.left(renderable, width=body_w))


# -------------------- Renderers --------------------
def _render_anomalies(con: Console, path: str, data: dict) -> None:
    body_w = _clamp_body_width(con)
    ug = data["unicode_ghosts"]; ty = data["typographic"]; ws = data["whitespace"]
    ug_total = _sumv(ug); ty_total = _sumv(ty); ws_total = _sumv(ws)
    final_ok = bool(data["final_newline"])
    total    = int(data["total"])

    # Header + blank line
    _print_clamped(con, Text(f"File: {path}", style="bold"), body_w)
    _print_clamped(con, Text(""), body_w)

    # Main anomalies table
    t = Table(*_cols_for_anomalies(), show_header=True, header_style="bold",
              box=None, pad_edge=False, expand=False)
    ug_details = ", ".join(f"{k}={v}" for k, v in ug.items() if v)
    ty_details = ", ".join(f"{k}={v}" for k, v in ty.items() if v)
    ws_details = ", ".join(f"{k}={v}" for k, v in ws.items() if v)

    t.add_row("unicode_ghosts", Text(str(ug_total), style=_sev_count(ug_total)), ug_details)
    t.add_row("typographic",    Text(str(ty_total), style=_sev_count(ty_total)), ty_details)
    t.add_row("whitespace",     Text(str(ws_total), style=_sev_count(ws_total)), ws_details)

    fn_mark = "/" if final_ok else "X"
    t.add_row("final_newline", Text(fn_mark, style=_sev_count(fn_mark)), "ok" if final_ok else "missing")

    _print_clamped(con, t, body_w)
    _print_clamped(con, Rule(), body_w)

    # Summary mini-table
    t2 = Table(*_cols_for_anomalies(), show_header=False, box=None, pad_edge=False, expand=False)
    t2.add_row("Total", Text(str(total), style=_sev_count(total)), "Overall anomaly count")
    _print_clamped(con, t2, body_w)
    _print_clamped(con, Text(""), body_w)


def _render_metrics(con: Console, metrics: dict) -> None:
    if not isinstance(metrics, dict) or not metrics:
        return
    body_w = _clamp_body_width(con)

    # Heading
    _print_clamped(con, Text(""), body_w)
    _print_clamped(con, Text("Metrics", style="bold"), body_w)
    _print_clamped(con, Text(""), body_w)

    # Signal column width from current body width (no arbitrary 80-col clamp)
    signal_w = max(24, body_w - (CAT_COL_WIDTH + VALUE_COL_WIDTH + 8))

    mt = Table(*_cols_for_metrics(signal_w), show_header=True, header_style="bold magenta",
               box=None, pad_edge=False, expand=False)

    order = [
        "ai_score","type_token_ratio","repetition_ratio","sentence_len_cv",
        "avg_sentence_len_tokens","avg_token_len","stopword_ratio","punctuation_ratio",
        "ascii_ratio","entropy","digits_ratio","tokens","sentences",
    ]
    labels = {
        "ai_score": "Heuristic 0–1; higher ≈ more AI-like. Not a detector.",
        "type_token_ratio": "Unique words ÷ total words. Higher = more lexical diversity.",
        "repetition_ratio": "Share of tokens covered by the top-5 most frequent words. Higher = more repetitive.",
        "sentence_len_cv": "Coefficient of variation (std ÷ mean) of sentence lengths. Lower = more uniform; higher = burstier.",
        "avg_sentence_len_tokens": "Mean sentence length (in tokens).",
        "avg_token_len": "Mean token length (avg characters per token/word).",
        "stopword_ratio": "Fraction of English stopwords. Typical prose ≈ 0.30–0.60.",
        "punctuation_ratio": "Punctuation characters ÷ total characters. Typical prose ≈ 0.02–0.08.",
        "ascii_ratio": "ASCII characters ÷ total characters.",
        "entropy": "Character-level Shannon entropy (variety/complexity indicator).",
        "digits_ratio": "Digits ÷ total characters.",
        "tokens": "Total token count (words).",
        "sentences": "Total sentence count.",
    }

    for name in order:
        if name not in metrics:
            continue
        disp_name = _pretty_metric(name)
        val = metrics[name]
        note = labels.get(name, "—")
        if isinstance(val, (int, float)):
            style = _sev_ratio(name, float(val))
            shown = _fmt_float(val) if isinstance(val, float) else str(val)
            mt.add_row(disp_name, Text(shown, style=style), note)
        else:
            mt.add_row(disp_name, str(val), note)

    _print_clamped(con, mt, body_w)
    _print_clamped(con, Rule(), body_w)

    overall = _overall_score(metrics)
    mt2 = Table(*_cols_for_metrics(signal_w), show_header=False, box=None, pad_edge=False, expand=False)
    mt2.add_row(
        "Overall score",
        Text(f"{overall:.4f}", style=_sev_ratio("ai_score", overall)),
        "Composite probability (0–1) from ai_score + repetition/TTR/burstiness.",
    )
    _print_clamped(con, mt2, body_w)
    _print_clamped(con, Text(""), body_w)


# -------------------- Public API --------------------
def print_human(path: str, data: dict, *, no_color: bool = False) -> None:
    con = _console(no_color)
    con.print()  # spacer so header doesn’t collide with shell prompt
    _render_anomalies(con, path, data)
    _render_metrics(con, data.get("metrics") or {})


def print_json(all_results: dict) -> None:  # noqa: F401
    """Pretty-print the full results as JSON (to stdout)."""
    print(json.dumps(all_results, indent=2, ensure_ascii=False))


def print_csv(all_results: dict) -> None:
    """Print results in CSV format (one row per file)."""
    # base columns
    fieldnames = ["file", "ug_total", "ty_total", "ws_total", "final_newline", "total"]

    # collect metric keys across all files
    metrics_keys = set()
    for data in all_results.values():
        metrics_keys |= set((data.get("metrics") or {}).keys())

    # make sure we always include overall_score (computed)
    metrics_cols = sorted(metrics_keys)
    if "overall_score" not in metrics_cols:
        metrics_cols.append("overall_score")

    fieldnames += metrics_cols

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    for label, data in all_results.items():
        row = {"file": label}

        ug = data.get("unicode_ghosts", {})
        ty = data.get("typographic", {})
        ws = data.get("whitespace", {})

        row["ug_total"] = sum(int(v) for v in ug.values())
        row["ty_total"] = sum(int(v) for v in ty.values())
        row["ws_total"] = sum(int(v) for v in ws.values())
        row["final_newline"] = int(bool(data.get("final_newline")))
        row["total"] = int(data.get("total", 0))

        metrics = data.get("metrics") or {}
        for k in metrics_cols:
            if k == "overall_score":
                row[k] = _overall_score(metrics) if metrics else ""
            else:
                if k in metrics:
                    row[k] = metrics[k]

        writer.writerow(row)


def print_metrics_help(*, no_color: bool = False) -> None:  # noqa: F401
    con = Console(no_color=no_color)
    guide = """\
AI score (0–1)            — ↑ = more AI-like (heuristic blend of signals; NOT a detector).
Type–token ratio          — ↑ = more human-like (lexical diversity); low = repetitive or templated text.
Repetition ratio          — ↑ = more AI-like (few tokens dominate); moderate values typical for humans.
Sentence length CV        — ↓ = more AI-like (uniform sentences); ↑ = more natural variation in human text.
Avg sentence len (tokens) — context only; very short = list-like, very long = dense/technical.
Avg token len             — weak alone; longer tokens in jargon/code, shorter in casual prose.
Stopword ratio            — mid-range (~0.30–0.60) typical; very low/high suggests domain-specific or templated text.
Punctuation ratio         — extreme values unusual; humans cluster ~0.02–0.08.
ASCII ratio               — very low = markup, math, or non-English; context-dependent.
Entropy                   — ↑ = more variety/complexity; ↓ = repetition/templates; interpret with other metrics.
Digits ratio              — ↑ = structured/templated data; ↓ = narrative prose.

Overall score (0–1)       — composite probability combining AI score, diversity, repetition, and burstiness.

Green/yellow/red bands are heuristic guides for triage, not ground truth.
"""
    # Panel width follows clamp behavior: expand=False + Align in caller keeps margins when UNICODEFIX_WIDTH is set
    con.print(Panel(guide, title="Metrics guide", expand=False))
