"""Tests for the Crossref HTTP client, using a fake urlopen -- no live
network calls, so these are fast and deterministic in CI.
"""

import json
import urllib.error
from io import BytesIO
from unittest.mock import patch

import pytest

from citeguard.crossref import CrossrefError, DoiNotFoundError, build_fetcher, polite_fetcher


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_returns_the_message_object_on_success():
    fake_payload = json.dumps({"status": "ok", "message": {"DOI": "10.1/x", "title": ["Hello"]}}).encode()
    with patch("urllib.request.urlopen", return_value=FakeResponse(fake_payload)):
        fetch = build_fetcher()
        message = fetch("10.1/x")
    assert message == {"DOI": "10.1/x", "title": ["Hello"]}


def test_fetch_raises_doi_not_found_on_404():
    error = urllib.error.HTTPError(url="x", code=404, msg="Not Found", hdrs=None, fp=BytesIO(b""))
    with patch("urllib.request.urlopen", side_effect=error):
        fetch = build_fetcher()
        with pytest.raises(DoiNotFoundError):
            fetch("10.9999/nope")


def test_fetch_raises_crossref_error_on_other_http_status():
    error = urllib.error.HTTPError(url="x", code=500, msg="Server Error", hdrs=None, fp=BytesIO(b""))
    with patch("urllib.request.urlopen", side_effect=error):
        fetch = build_fetcher()
        with pytest.raises(CrossrefError):
            fetch("10.1/x")


def test_fetch_raises_crossref_error_on_network_failure():
    error = urllib.error.URLError("connection refused")
    with patch("urllib.request.urlopen", side_effect=error):
        fetch = build_fetcher()
        with pytest.raises(CrossrefError):
            fetch("10.1/x")


def test_fetch_raises_crossref_error_on_malformed_json():
    with patch("urllib.request.urlopen", return_value=FakeResponse(b"not json{{{")):
        fetch = build_fetcher()
        with pytest.raises(CrossrefError):
            fetch("10.1/x")


def test_fetch_raises_crossref_error_when_message_field_missing():
    fake_payload = json.dumps({"status": "ok"}).encode()
    with patch("urllib.request.urlopen", return_value=FakeResponse(fake_payload)):
        fetch = build_fetcher()
        with pytest.raises(CrossrefError):
            fetch("10.1/x")


def test_mailto_is_included_in_user_agent_when_provided():
    captured_requests = []

    def fake_urlopen(request, timeout=None):
        captured_requests.append(request)
        return FakeResponse(json.dumps({"message": {"DOI": "10.1/x"}}).encode())

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        fetch = build_fetcher(contact_email="me@example.com")
        fetch("10.1/x")

    assert "me@example.com" in captured_requests[0].get_header("User-agent")


def test_doi_with_special_characters_is_url_encoded():
    captured_urls = []

    def fake_urlopen(request, timeout=None):
        captured_urls.append(request.full_url)
        return FakeResponse(json.dumps({"message": {"DOI": "x"}}).encode())

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        fetch = build_fetcher()
        fetch("10.1016/S0140-6736(97)11096-0")

    assert "S0140-6736(97)11096-0" not in captured_urls[0]  # parens must be encoded
    assert "%28" in captured_urls[0] and "%29" in captured_urls[0]


def test_polite_fetcher_calls_underlying_fetcher_and_sleeps():
    calls = []

    def underlying(doi):
        calls.append(doi)
        return {"DOI": doi}

    with patch("time.sleep") as mock_sleep:
        wrapped = polite_fetcher(underlying, delay_seconds=0.05)
        result = wrapped("10.1/x")

    assert result == {"DOI": "10.1/x"}
    assert calls == ["10.1/x"]
    mock_sleep.assert_called_once_with(0.05)
