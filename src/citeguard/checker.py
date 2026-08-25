"""High-level API: check one or many DOIs, with optional caching."""

from __future__ import annotations

from .analyze import analyze_work
from .cache import FileCache
from .crossref import CrossrefError, DoiNotFoundError, Fetcher, build_fetcher
from .models import RetractionStatus, Verdict


def check_doi(doi: str, *, fetch: Fetcher | None = None, cache: FileCache | None = None) -> RetractionStatus:
    """Check a single DOI against Crossref and return its retraction status.

    Never raises for an expected failure (unknown DOI, network error) --
    those become a RetractionStatus with verdict NOT_FOUND or ERROR, so
    callers checking a whole bibliography can keep going past one bad
    entry.
    """
    fetch = fetch or build_fetcher()

    cached = cache.get(doi) if cache else None
    if cached is not None:
        return analyze_work(cached)

    try:
        message = fetch(doi)
    except DoiNotFoundError:
        return RetractionStatus(doi=doi, verdict=Verdict.NOT_FOUND, title=None, error="DOI not found in Crossref")
    except CrossrefError as exc:
        return RetractionStatus(doi=doi, verdict=Verdict.ERROR, title=None, error=str(exc))

    if cache:
        cache.set(doi, message)

    return analyze_work(message)


def check_dois(dois: list[str], *, fetch: Fetcher | None = None, cache: FileCache | None = None) -> list[RetractionStatus]:
    """Check multiple DOIs, preserving input order. Duplicate DOIs are only fetched once."""
    fetch = fetch or build_fetcher()
    results_by_doi: dict[str, RetractionStatus] = {}
    for doi in dois:
        if doi not in results_by_doi:
            results_by_doi[doi] = check_doi(doi, fetch=fetch, cache=cache)
    return [results_by_doi[doi] for doi in dois]
