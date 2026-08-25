"""A trivial persistent cache: DOI -> raw Crossref message dict, as JSON.

Not a general-purpose cache library -- just enough to avoid re-querying
Crossref for DOIs a CI run has already checked before, which is both
faster and more polite to a free public API. No TTL/expiry: retraction
status only ever moves in one direction (a paper doesn't get "un-flagged"
back to clean), so a stale cache entry is never wrong in the way that
matters for this tool -- at worst it misses a *new* retraction that
happened since the entry was cached, which the ``--no-cache`` flag exists
to handle for anyone who wants a fully fresh check.
"""

from __future__ import annotations

import json
from pathlib import Path


class FileCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def get(self, doi: str) -> dict | None:
        return self._data.get(doi)

    def set(self, doi: str, message: dict) -> None:
        self._data[doi] = message

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
