"""Turn a raw Crossref "work" message into a RetractionStatus.

The detection logic here is deliberately based on empirically-verified
Crossref response shapes, not assumptions about the API:

- ``update-to``: forward-looking notices the *publisher* attached directly
  to the work (``source: "publisher"``). Seen e.g. on the Surgisphere-linked
  Lancet paper (Mehra et al. 2020, DOI 10.1016/s0140-6736(20)31180-6).
- ``updated-by``: a *separate* field where Crossref has backfilled
  retraction/correction data from the Retraction Watch database
  (``source: "retraction-watch"``) -- present even when the publisher never
  added structured metadata of its own. Confirmed on the Wakefield 1998
  Lancet paper (DOI 10.1016/S0140-6736(97)11096-0), which has an *empty*
  ``update-to`` but a populated ``updated-by`` recording both its 2004
  correction and its 2010 retraction.
- A title-prefix heuristic ("RETRACTED:", "WITHDRAWN:", etc.) as a last
  resort for the (presumably shrinking, but real) set of cases with no
  structured signal on either field at all.

Verified against real Crossref responses for these three cases plus a
clean control (Watson & Crick 1953, DOI 10.1038/171737a0, no signals on
any of the three checks) -- see tests/fixtures/.
"""

from __future__ import annotations

import re

from .models import RetractionStatus, Signal, SignalType, Verdict

_RELEVANT_TYPES = {
    "retraction": SignalType.RETRACTION,
    "removal": SignalType.REMOVAL,
    "expression_of_concern": SignalType.EXPRESSION_OF_CONCERN,
    "correction": SignalType.CORRECTION,
}

_TITLE_PREFIX_RE = re.compile(
    r"^\s*(RETRACTED(?:\s+ARTICLE)?|RETRACTION|WITHDRAWN|EXPRESSION OF CONCERN|CORRIGENDUM)\s*:",
    re.IGNORECASE,
)

# Maps a matched title prefix to the signal type it's equivalent to -- a
# "Corrigendum:" or "Expression of Concern:" title is real signal, but not
# the same severity as an actual retraction, so it must not be lumped into
# one generic "title heuristic -> always retracted" bucket.
_TITLE_PREFIX_SIGNAL_TYPE = {
    "RETRACTED": SignalType.RETRACTION,
    "RETRACTED ARTICLE": SignalType.RETRACTION,
    "RETRACTION": SignalType.RETRACTION,
    "WITHDRAWN": SignalType.RETRACTION,
    "EXPRESSION OF CONCERN": SignalType.EXPRESSION_OF_CONCERN,
    "CORRIGENDUM": SignalType.CORRECTION,
}


def _extract_field_signals(items: list[dict]) -> list[Signal]:
    signals = []
    for item in items:
        raw_type = item.get("type")
        sig_type = _RELEVANT_TYPES.get(raw_type)
        if sig_type is None:
            continue
        date = None
        updated = item.get("updated") or {}
        date_parts = updated.get("date-parts")
        if date_parts and date_parts[0]:
            date = "-".join(str(p).zfill(2) for p in date_parts[0])
        signals.append(
            Signal(
                type=sig_type,
                source=item.get("source", "publisher"),
                label=item.get("label"),
                notice_doi=item.get("DOI"),
                date=date,
            )
        )
    return signals


def _title_text(message: dict) -> str:
    titles = message.get("title") or []
    return " ".join(titles).strip()


def analyze_work(message: dict) -> RetractionStatus:
    """Analyze a Crossref ``message`` object (the ``.message`` field of a
    ``/works/{doi}`` response) and return a RetractionStatus.
    """
    doi = message.get("DOI", "")
    title = _title_text(message) or None

    signals = _extract_field_signals(message.get("update-to", []))
    signals += _extract_field_signals(message.get("updated-by", []))

    if not signals and title:
        match = _TITLE_PREFIX_RE.match(title)
        if match:
            matched_label = match.group(1)
            sig_type = _TITLE_PREFIX_SIGNAL_TYPE.get(matched_label.upper(), SignalType.RETRACTION)
            signals.append(Signal(type=sig_type, source="title_prefix", label=matched_label))

    verdict = _verdict_from_signals(signals)
    return RetractionStatus(doi=doi, verdict=verdict, title=title, signals=signals)


def _verdict_from_signals(signals: list[Signal]) -> Verdict:
    types = {s.type for s in signals}
    if SignalType.RETRACTION in types or SignalType.REMOVAL in types:
        return Verdict.RETRACTED
    if SignalType.EXPRESSION_OF_CONCERN in types:
        return Verdict.CONCERN
    if SignalType.CORRECTION in types:
        return Verdict.CORRECTED
    return Verdict.CLEAN
