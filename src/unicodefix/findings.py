"""Versioned, serialisable audit findings used by UnicodeFix.

The model deliberately describes observable evidence.  A finding is never an
authorship assertion: provenance and a configured watermark detector are
reported separately from Unicode and formatting observations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

FINDINGS_SCHEMA_VERSION = "2.0"
Category = Literal[
    "provenance",
    "unicode_security",
    "known_watermark",
    "authorship_signal",
    "typography",
    "formatting",
]


@dataclass(frozen=True)
class Location:
    """A zero-width or character span in one-based text coordinates."""

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    offset: int | None = None
    end_offset: int | None = None


@dataclass(frozen=True)
class Finding:
    category: Category
    signal: str
    count: int = 1
    locations: tuple[Location, ...] = ()
    confidence: Literal["high", "medium", "low", "informational"] = "high"
    removable: bool = False
    planned_action: str = "report"
    message: str = ""
    scheme: str | None = None
    vendor: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["locations"] = [asdict(location) for location in self.locations]
        return value


@dataclass
class Findings:
    """A stable envelope for JSON, CSV, and human report renderers."""

    items: list[Finding] = field(default_factory=list)
    schema_version: str = FINDINGS_SCHEMA_VERSION

    def add(self, finding: Finding) -> None:
        self.items.append(finding)

    def by_category(self, category: Category) -> list[Finding]:
        return [finding for finding in self.items if finding.category == category]

    def total(self, category: Category | None = None) -> int:
        findings = self.items if category is None else self.by_category(category)
        return sum(finding.count for finding in findings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "findings": [finding.to_dict() for finding in self.items],
        }
