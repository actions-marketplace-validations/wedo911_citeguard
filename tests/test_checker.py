import tempfile
from pathlib import Path

from citeguard.cache import FileCache
from citeguard.checker import check_doi, check_dois
from citeguard.crossref import CrossrefError, DoiNotFoundError
from citeguard.models import Verdict


def clean_message(doi="10.1/clean"):
    return {"DOI": doi, "title": ["A perfectly normal title"]}


def retracted_message(doi="10.1/bad"):
    return {"DOI": doi, "title": ["RETRACTED: A bad paper"]}


def test_check_doi_returns_clean_result():
    result = check_doi("10.1/clean", fetch=lambda doi: clean_message(doi))
    assert result.verdict == Verdict.CLEAN


def test_check_doi_returns_not_found_when_fetch_raises_doi_not_found():
    def fetch(doi):
        raise DoiNotFoundError(doi)

    result = check_doi("10.9999/nope", fetch=fetch)
    assert result.verdict == Verdict.NOT_FOUND
    assert result.error is not None


def test_check_doi_returns_error_verdict_on_crossref_error_instead_of_raising():
    def fetch(doi):
        raise CrossrefError("network exploded")

    result = check_doi("10.1/x", fetch=fetch)
    assert result.verdict == Verdict.ERROR
    assert "network exploded" in result.error


def test_check_dois_preserves_input_order():
    messages = {"10.1/a": clean_message("10.1/a"), "10.1/b": retracted_message("10.1/b"), "10.1/c": clean_message("10.1/c")}
    results = check_dois(["10.1/b", "10.1/a", "10.1/c"], fetch=lambda doi: messages[doi])
    assert [r.doi for r in results] == ["10.1/b", "10.1/a", "10.1/c"]
    assert results[0].verdict == Verdict.RETRACTED


def test_check_dois_only_fetches_each_unique_doi_once():
    call_count = {"n": 0}

    def fetch(doi):
        call_count["n"] += 1
        return clean_message(doi)

    results = check_dois(["10.1/a", "10.1/a", "10.1/b", "10.1/a"], fetch=fetch)
    assert len(results) == 4
    assert call_count["n"] == 2  # only 10.1/a and 10.1/b actually fetched


def test_check_doi_uses_cache_when_present_and_does_not_call_fetch():
    with tempfile.TemporaryDirectory() as tmp:
        cache_path = Path(tmp) / "cache.json"
        cache = FileCache(cache_path)
        cache.set("10.1/a", retracted_message("10.1/a"))

        def fetch_should_not_be_called(doi):
            raise AssertionError("fetch should not be called for a cached DOI")

        result = check_doi("10.1/a", fetch=fetch_should_not_be_called, cache=cache)
        assert result.verdict == Verdict.RETRACTED


def test_check_doi_populates_cache_on_miss():
    with tempfile.TemporaryDirectory() as tmp:
        cache_path = Path(tmp) / "cache.json"
        cache = FileCache(cache_path)

        check_doi("10.1/a", fetch=lambda doi: clean_message(doi), cache=cache)

        assert cache.get("10.1/a") is not None


def test_filecache_round_trips_through_save_and_reload():
    with tempfile.TemporaryDirectory() as tmp:
        cache_path = Path(tmp) / "sub" / "cache.json"
        cache = FileCache(cache_path)
        cache.set("10.1/a", {"DOI": "10.1/a", "title": ["X"]})
        cache.save()

        reloaded = FileCache(cache_path)
        assert reloaded.get("10.1/a") == {"DOI": "10.1/a", "title": ["X"]}


def test_filecache_missing_file_starts_empty():
    with tempfile.TemporaryDirectory() as tmp:
        cache = FileCache(Path(tmp) / "does-not-exist.json")
        assert cache.get("10.1/a") is None


def test_filecache_corrupt_file_starts_empty_instead_of_raising():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "corrupt.json"
        path.write_text("{not valid json", encoding="utf-8")
        cache = FileCache(path)
        assert cache.get("anything") is None
