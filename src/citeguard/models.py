"""Data models for citeguard.

Kept dependency-free (stdlib dataclasses only) so the library has zero
runtime dependencies beyond the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SignalType(Enum):
    RETRACTION = "retraction"
    REMOVAL = "removal"
    EXPRESSION_OF_CONCERN = "expression_of_concern"
    CORRECTION = "correction"


class Verdict(Enum):
    """Overall status for a checked work, ordered worst-to-best for sorting."""

    RETRACTED = "retracted"
    CONCERN = "concern"
    CORRECTED = "corrected"
    CLEAN = "clean"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass(frozen=True)
class Signal:
    """One piece of evidence about a work's status, from one source."""

    type: SignalType
    source: str  # e.g. "publisher", "retraction-watch", "title_prefix"
    label: str | None = None
    notice_doi: str | None = None
    date: str | None = None  # ISO date string, if known


@dataclass(frozen=True)
class RetractionStatus:
    """Result of checking a single DOI."""

    doi: str
    verdict: Verdict
    title: str | None
    signals: list[Signal] = field(default_factory=list)
    error: str | None = None

    @property
    def is_problematic(self) -> bool:
        return self.verdict in (Verdict.RETRACTED, Verdict.CONCERN)


@dataclass(frozen=True)
class Citation:
    """A citation extracted from a bibliography or free text, before checking."""

    doi: str
    source_label: str | None = None  # e.g. a BibTeX cite key, or line number
