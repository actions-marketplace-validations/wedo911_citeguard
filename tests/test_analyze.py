"""Tests against REAL, committed Crossref API responses (tests/fixtures/),
captured live during development -- not hand-written approximations of
what the API might return. See fixtures/README.md for provenance.
"""

import json
from pathlib import Path

import pytest

from citeguard.analyze import analyze_work
from citeguard.models import SignalType, Verdict

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return payload["message"]


def test_wakefield_1998_is_retracted_via_updated_by_retraction_watch_signal():
    """This is the case that matters most: the publisher (Elsevier) never
    added structured update-to metadata, but Crossref's ingested
    Retraction Watch data (updated-by, source=retraction-watch) still
    surfaces the 2010 retraction -- and the 2004 correction before it.
    """
    message = load_fixture("wakefield_1998.json")
    result = analyze_work(message)

    assert result.verdict == Verdict.RETRACTED
    assert result.is_problematic
    retraction_signals = [s for s in result.signals if s.type == SignalType.RETRACTION]
    assert len(retraction_signals) == 1
    assert retraction_signals[0].source == "retraction-watch"
    assert retraction_signals[0].date == "2010-02-06"

    correction_signals = [s for s in result.signals if s.type == SignalType.CORRECTION]
    assert len(correction_signals) == 1
    assert correction_signals[0].date == "2004-03-06"


def test_wakefield_title_carries_the_retracted_prefix_too():
    message = load_fixture("wakefield_1998.json")
    result = analyze_work(message)
    assert result.title is not None
    assert result.title.upper().startswith("RETRACTED:")


def test_surgisphere_lancet_paper_is_retracted_via_publisher_update_to_signal():
    """The publisher-direct case: update-to, source=publisher."""
    message = load_fixture("surgisphere_mehra_2020.json")
    result = analyze_work(message)

    assert result.verdict == Verdict.RETRACTED
    retraction_signals = [s for s in result.signals if s.type == SignalType.RETRACTION]
    assert len(retraction_signals) >= 1
    assert retraction_signals[0].source == "publisher"
    assert retraction_signals[0].notice_doi is not None


def test_watson_crick_1953_is_clean_no_false_positive():
    """Control case: a famous, definitely-not-retracted paper must not be flagged."""
    message = load_fixture("watson_crick_1953_clean.json")
    result = analyze_work(message)

    assert result.verdict == Verdict.CLEAN
    assert not result.is_problematic
    assert result.signals == []
    assert "nucleic acid" in result.title.lower()


# -- synthetic cases for signal types the three real fixtures don't cover --------


def test_expression_of_concern_via_update_to():
    message = {
        "DOI": "10.9999/example",
        "title": ["A perfectly normal-sounding title"],
        "update-to": [
            {"DOI": "10.9999/notice", "type": "expression_of_concern", "label": "Expression of Concern", "source": "publisher", "updated": {"date-parts": [[2023, 5, 1]]}}
        ],
    }
    result = analyze_work(message)
    assert result.verdict == Verdict.CONCERN
    assert result.is_problematic


def test_correction_only_is_not_treated_as_problematic():
    message = {
        "DOI": "10.9999/example",
        "title": ["A perfectly normal-sounding title"],
        "update-to": [{"DOI": "10.9999/notice", "type": "correction", "label": "Correction", "source": "publisher", "updated": {"date-parts": [[2021, 1, 1]]}}],
    }
    result = analyze_work(message)
    assert result.verdict == Verdict.CORRECTED
    assert not result.is_problematic


def test_title_heuristic_expression_of_concern_is_not_upgraded_to_retracted():
    """A title-only 'Expression of Concern:' prefix must map to CONCERN, not
    RETRACTED -- these are different severities and must not be collapsed
    into one bucket just because both come from the title heuristic path.
    """
    message = {"DOI": "10.9999/example", "title": ["Expression of Concern: Some paper"]}
    result = analyze_work(message)
    assert result.verdict == Verdict.CONCERN


def test_title_heuristic_corrigendum_maps_to_corrected_not_retracted():
    message = {"DOI": "10.9999/example", "title": ["Corrigendum: Some paper"]}
    result = analyze_work(message)
    assert result.verdict == Verdict.CORRECTED


def test_title_heuristic_withdrawn_maps_to_retracted():
    message = {"DOI": "10.9999/example", "title": ["WITHDRAWN: Some paper"]}
    result = analyze_work(message)
    assert result.verdict == Verdict.RETRACTED


def test_title_heuristic_is_skipped_when_structured_signals_already_present():
    """If update-to/updated-by already gave a verdict, the (weaker) title
    heuristic must not run and potentially override it with a different
    signal source -- structured data always takes precedence.
    """
    message = {
        "DOI": "10.9999/example",
        "title": ["RETRACTED: Some paper"],
        "update-to": [{"DOI": "10.9999/notice", "type": "correction", "label": "Correction", "source": "publisher", "updated": {"date-parts": [[2021, 1, 1]]}}],
    }
    result = analyze_work(message)
    assert result.verdict == Verdict.CORRECTED
    assert all(s.source != "title_prefix" for s in result.signals)


def test_unrelated_update_type_is_ignored():
    """Crossref's update-to/updated-by can carry unrelated relation types
    (e.g. 'new_version', 'addendum') that shouldn't affect the verdict.
    """
    message = {
        "DOI": "10.9999/example",
        "title": ["A perfectly normal-sounding title"],
        "update-to": [{"DOI": "10.9999/notice", "type": "new_version", "label": "New Version", "source": "publisher"}],
    }
    result = analyze_work(message)
    assert result.verdict == Verdict.CLEAN


def test_missing_title_does_not_crash():
    message = {"DOI": "10.9999/example"}
    result = analyze_work(message)
    assert result.verdict == Verdict.CLEAN
    assert result.title is None
