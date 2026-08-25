"""Extract citations (as DOIs) from plain text, BibTeX, and RIS.

These are intentionally lightweight, regex-based parsers -- not full
implementations of the BibTeX or RIS grammars. They're built to reliably
pull out the one thing this tool needs (a DOI per entry), not to
round-trip arbitrary bibliography files.
"""

from __future__ import annotations

import re

from .models import Citation

# The DOI syntax Crossref itself documents: "10." + a >= 4-digit registrant
# code + "/" + a permissive suffix. Suffixes commonly include parentheses
# (e.g. 10.1016/S0140-6736(97)11096-0), so those must be allowed.
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")


def _clean_doi(raw: str) -> str:
    """Strip common trailing punctuation a DOI regex match can accidentally include."""
    return raw.rstrip(").,;:]}\"'")


def extract_dois(text: str) -> list[str]:
    """Find every DOI-shaped substring in free text, in order of appearance, deduplicated."""
    seen: dict[str, None] = {}
    for match in DOI_RE.finditer(text):
        doi = _clean_doi(match.group(0))
        seen.setdefault(doi, None)
    return list(seen.keys())


def parse_bibtex(text: str) -> list[Citation]:
    """Extract one Citation per BibTeX entry that has (or contains) a DOI.

    Looks for an explicit ``doi = {...}`` / ``doi = "..."`` field first;
    falls back to scanning the whole entry body for a DOI-shaped string
    (covers DOIs embedded in a ``url`` or ``note`` field instead).
    """
    citations = []
    # The cite-key must not cross whitespace/braces: a malformed or keyless
    # entry (e.g. a @comment{...} block with no comma at all) must fail to
    # match here rather than greedily consuming text up to the next
    # entry's comma and swallowing it in the process.
    for entry_match in re.finditer(r"@(\w+)\s*\{\s*([^,{}\s]+)\s*,", text):
        entry_type, cite_key = entry_match.groups()
        if entry_type.lower() == "comment":
            continue
        body_start = entry_match.end()
        body_end = _find_matching_brace(text, entry_match.start())
        body = text[body_start:body_end]

        doi_field = re.search(r"doi\s*=\s*[{\"]\s*([^}\"]+?)\s*[}\"]", body, re.IGNORECASE)
        if doi_field:
            doi = _clean_doi(doi_field.group(1).strip())
            citations.append(Citation(doi=doi, source_label=cite_key.strip()))
            continue

        fallback = DOI_RE.search(body)
        if fallback:
            citations.append(Citation(doi=_clean_doi(fallback.group(0)), source_label=cite_key.strip()))

    return citations


def _find_matching_brace(text: str, entry_start: int) -> int:
    """Given the index of the '@' starting a BibTeX entry, find the index of its closing '}'."""
    open_index = text.index("{", entry_start)
    depth = 0
    for i in range(open_index, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text)


def parse_ris(text: str) -> list[Citation]:
    """Extract one Citation per RIS record that has a DOI.

    RIS uses ``TAG  - value`` lines; DOIs typically appear on a ``DO`` tag,
    sometimes only inside a ``UR``/``L1``/``L2`` URL field instead.
    """
    citations = []
    current_doi: str | None = None
    record_index = 0

    for line in text.splitlines():
        tag_match = re.match(r"^([A-Z][A-Z0-9])\s*-\s*(.*)$", line)
        if not tag_match:
            continue
        tag, value = tag_match.groups()

        if tag == "TY":
            current_doi = None
        elif tag in ("DO", "UR", "L1", "L2", "L3") and current_doi is None:
            found = DOI_RE.search(value)
            if found:
                current_doi = _clean_doi(found.group(0))
        elif tag == "ER":
            record_index += 1
            if current_doi:
                citations.append(Citation(doi=current_doi, source_label=f"record {record_index}"))
            current_doi = None

    return citations
