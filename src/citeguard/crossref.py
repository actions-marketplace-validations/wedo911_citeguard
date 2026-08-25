"""Minimal Crossref REST API client.

Uses only ``urllib`` from the standard library -- no ``requests``
dependency. Crossref's API is free and requires no API key; including a
``mailto`` in the User-Agent opts a caller into Crossref's faster "polite
pool" (see https://api.crossref.org), which this client does by default
when a contact email is configured.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

CROSSREF_BASE_URL = "https://api.crossref.org/works"
DEFAULT_USER_AGENT = "citeguard/1.0 (https://github.com/wedo911/citeguard)"


class DoiNotFoundError(Exception):
    """The DOI does not exist in Crossref."""


class CrossrefError(Exception):
    """Any other Crossref API failure (network error, unexpected status, malformed response)."""


Fetcher = Callable[[str], dict]


def build_fetcher(*, contact_email: str | None = None, timeout: float = 10.0) -> Fetcher:
    """Build a fetch function: doi -> Crossref ``message`` dict.

    Kept as a factory (rather than a single hardcoded function) so tests
    can inject a fake fetcher instead of hitting the network, and so
    callers can configure the polite-pool contact email and timeout.
    """
    user_agent = DEFAULT_USER_AGENT
    if contact_email:
        user_agent = f"{DEFAULT_USER_AGENT} (mailto:{contact_email})"

    def fetch(doi: str) -> dict:
        url = f"{CROSSREF_BASE_URL}/{urllib.parse.quote(doi, safe='')}"
        request = urllib.request.Request(url, headers={"User-Agent": user_agent})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise DoiNotFoundError(doi) from exc
            raise CrossrefError(f"Crossref returned HTTP {exc.code} for {doi}") from exc
        except urllib.error.URLError as exc:
            raise CrossrefError(f"Network error contacting Crossref for {doi}: {exc.reason}") from exc

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise CrossrefError(f"Crossref returned malformed JSON for {doi}") from exc

        message = payload.get("message")
        if not isinstance(message, dict):
            raise CrossrefError(f"Crossref response for {doi} had no 'message' object")
        return message

    return fetch


def polite_fetcher(fetcher: Fetcher, *, delay_seconds: float = 0.1) -> Fetcher:
    """Wrap a fetcher with a small fixed delay between calls, so checking a
    whole bibliography doesn't hammer Crossref's API in a tight loop.
    """

    def wrapped(doi: str) -> dict:
        result = fetcher(doi)
        time.sleep(delay_seconds)
        return result

    return wrapped
