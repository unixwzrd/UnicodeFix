"""Local Unicode, provenance, source, and Markdown auditing."""

from unicodefix.authorship import (
    detect_authorship_profiles,
    detect_authorship_with_profile,
)
from unicodefix.markdown import audit_markdown, unwrap_markdown
from unicodefix.metrics import compute_metrics
from unicodefix.scanner import scan_findings, scan_text_for_report
from unicodefix.transforms import clean_text, handle_newlines

__all__ = [
    "audit_markdown",
    "clean_text",
    "compute_metrics",
    "detect_authorship_profiles",
    "detect_authorship_with_profile",
    "handle_newlines",
    "scan_findings",
    "scan_text_for_report",
    "unwrap_markdown",
]
__version__ = "2.0.0"
