"""Human, JSON, and CSV rendering for the shared UnicodeFix report model."""

from __future__ import annotations

import csv
import json
import sys
from typing import Any, TextIO

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

__all__ = ["print_csv", "print_human", "print_json", "print_metrics_help"]


def _console(no_color: bool, file: TextIO) -> Console:
    return Console(no_color=no_color, file=file)


def _location(finding: dict[str, Any]) -> str:
    locations = finding.get("locations") or []
    if not locations:
        return "-"
    first = locations[0]
    suffix = f" (+{len(locations) - 1})" if len(locations) > 1 else ""
    return f"{first.get('line', '?')}:{first.get('column', '?')}{suffix}"


def _render_findings(console: Console, data: dict[str, Any]) -> None:
    findings = data.get("findings") or []
    if not findings:
        console.print("Findings: none", style="green")
        return
    table = Table(title="Observable findings", box=None, pad_edge=False)
    table.add_column("Category", style="bold")
    table.add_column("Signal")
    table.add_column("Count", justify="right")
    table.add_column("First location")
    table.add_column("Action")
    for finding in findings:
        table.add_row(
            str(finding.get("category", "-")),
            str(finding.get("signal", "-")),
            str(finding.get("count", 1)),
            _location(finding),
            str(finding.get("planned_action", "report")),
        )
    console.print(table)


def _render_mapping(console: Console, title: str, values: dict[str, Any]) -> None:
    if not values:
        return
    table = Table(title=title, box=None, pad_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    for name, value in values.items():
        shown = (
            json.dumps(value, ensure_ascii=False, sort_keys=True)
            if isinstance(value, (dict, list))
            else str(value)
        )
        table.add_row(name.replace("_", " "), shown)
    console.print(table)


def _render_watermarks(console: Console, results: list[dict[str, Any]]) -> None:
    if not results:
        return
    table = Table(title="Configured watermark profiles", box=None, pad_edge=False)
    table.add_column("Profile")
    table.add_column("Scheme")
    table.add_column("Status", style="bold")
    table.add_column("Score")
    table.add_column("Configuration")
    for result in results:
        table.add_row(
            str(result.get("profile", "-")),
            str(result.get("scheme", "-")),
            str(result.get("status", "-")),
            "-" if result.get("score") is None else str(result["score"]),
            str(result.get("configuration_fingerprint", "-")),
        )
    console.print(table)
    console.print(
        "A negative result applies only to the named profile and configuration.",
        style="dim",
    )


def _render_authorship(console: Console, results: list[dict[str, Any]]) -> None:
    if not results:
        return
    table = Table(title="Calibrated authorship signals", box=None, pad_edge=False)
    table.add_column("Profile")
    table.add_column("Method")
    table.add_column("Status", style="bold")
    table.add_column("Metric")
    table.add_column("Threshold")
    table.add_column("Flagged paragraphs", justify="right")
    for result in results:
        table.add_row(
            str(result.get("profile", "-")),
            str(result.get("method", "-")),
            str(result.get("status", "-")),
            str(result.get("metric", "-")),
            "-" if result.get("threshold") is None else str(result["threshold"]),
            str(sum(bool(item.get("flagged")) for item in result.get("segments", []))),
        )
    console.print(table)
    console.print(
        "These are profile-calibrated distribution signals, not watermark detections or proof of authorship.",
        style="dim",
    )


def print_human(
    path: str,
    data: dict[str, Any],
    *,
    no_color: bool = False,
    file: TextIO = sys.stdout,
) -> None:
    console = _console(no_color, file)
    console.print()
    console.print(f"File: {path}", style="bold")
    console.print(
        f"Schema: {data.get('schema_version', 'legacy')}  "
        f"Aggregate anomalies: {data.get('total', 0)}"
    )
    _render_findings(console, data)
    _render_mapping(console, "Metrics (deterministic)", data.get("metrics") or {})
    _render_mapping(console, "Markdown formatting", data.get("markdown") or {})
    source = data.get("source") or {}
    if source:
        _render_mapping(
            console,
            "Source contexts",
            {
                "language": source.get("language"),
                "parser": source.get("parser"),
                "parse_valid": source.get("parse_valid"),
                "counts": source.get("counts"),
            },
        )
    _render_watermarks(console, data.get("known_watermarks") or [])
    _render_authorship(console, data.get("authorship_signals") or [])
    _render_mapping(console, "Planned cleanup", data.get("planned") or {})


def print_json(all_results: dict[str, Any], *, file: TextIO = sys.stdout) -> None:
    print(json.dumps(all_results, indent=2, ensure_ascii=False), file=file)


def _category_counts(data: dict[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}
    for finding in data.get("findings") or []:
        category = str(finding.get("category", "unknown"))
        result[category] = result.get(category, 0) + int(finding.get("count", 1))
    return result


def print_csv(all_results: dict[str, Any], *, file: TextIO = sys.stdout) -> None:
    metric_keys = sorted(
        {
            key
            for data in all_results.values()
            for key, value in (data.get("metrics") or {}).items()
            if not isinstance(value, (dict, list))
        }
    )
    categories = [
        "provenance",
        "unicode_security",
        "known_watermark",
        "authorship_signal",
        "typography",
        "formatting",
    ]
    planned_keys = sorted(
        {
            key
            for data in all_results.values()
            for key, value in (data.get("planned") or {}).items()
            if not isinstance(value, (dict, list))
        }
    )
    before_after_keys = sorted(
        {
            key
            for data in all_results.values()
            for stage in ("before", "after")
            for key, value in (((data.get("planned") or {}).get(stage) or {}).items())
            if not isinstance(value, (dict, list))
        }
    )
    fieldnames = [
        "file",
        "schema_version",
        "total",
        *categories,
        *metric_keys,
        *(f"planned_{key}" for key in planned_keys),
        *(f"before_{key}" for key in before_after_keys),
        *(f"after_{key}" for key in before_after_keys),
    ]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    for label, data in all_results.items():
        row: dict[str, Any] = {
            "file": label,
            "schema_version": data.get("schema_version", "legacy"),
            "total": data.get("total", 0),
        }
        counts = _category_counts(data)
        row.update({category: counts.get(category, 0) for category in categories})
        row.update(
            {key: (data.get("metrics") or {}).get(key, "") for key in metric_keys}
        )
        planned = data.get("planned") or {}
        row.update({f"planned_{key}": planned.get(key, "") for key in planned_keys})
        for stage in ("before", "after"):
            values = planned.get(stage) or {}
            row.update(
                {f"{stage}_{key}": values.get(key, "") for key in before_after_keys}
            )
        writer.writerow(row)


def print_metrics_help(*, no_color: bool = False) -> None:
    console = Console(no_color=no_color)
    guide = """\
Metrics are deterministic document facts, not authorship probabilities.

bytes/characters/lines/words   Basic document size counts.
newline style                  LF, CRLF, CR, mixed, or none.
ASCII/non-ASCII                Character inventory split.
non-ASCII code points          Counts keyed by U+XXXX.
Markdown metrics               Soft-break candidates, list continuations, hard breaks, and common wrap widths.
Source metrics                 Suspicious characters classified as comments, strings, identifiers, or syntax.
Dry-run metrics                Before/after totals and whether the requested cleanup would change content.

Use --report for exact findings and --dry-run --diff to preview cleanup without writing files.
"""
    console.print(Panel(guide, title="Deterministic metrics", expand=False))
