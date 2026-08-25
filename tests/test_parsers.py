from citeguard.parsers import extract_dois, parse_bibtex, parse_ris

# -- extract_dois -----------------------------------------------------------------


def test_extract_dois_finds_a_plain_doi_in_text():
    text = "See https://doi.org/10.1016/S0140-6736(97)11096-0 for details."
    assert extract_dois(text) == ["10.1016/S0140-6736(97)11096-0"]


def test_extract_dois_finds_multiple_and_deduplicates_preserving_order():
    text = "First 10.1000/abc then 10.1000/def then 10.1000/abc again."
    assert extract_dois(text) == ["10.1000/abc", "10.1000/def"]


def test_extract_dois_strips_trailing_sentence_punctuation():
    text = "This paper (see 10.1000/abc) is good. Also 10.1000/def."
    dois = extract_dois(text)
    assert "10.1000/abc" in dois
    assert "10.1000/def" in dois
    assert not any(d.endswith(")") or d.endswith(".") for d in dois)


def test_extract_dois_returns_empty_list_for_text_with_no_dois():
    assert extract_dois("Just some ordinary prose with no citations.") == []


# -- parse_bibtex ---------------------------------------------------------------


def test_parse_bibtex_extracts_explicit_doi_field():
    bib = """
    @article{wakefield1998,
      author = {Wakefield, AJ},
      title = {Ileal-lymphoid-nodular hyperplasia},
      doi = {10.1016/S0140-6736(97)11096-0},
      year = {1998}
    }
    """
    citations = parse_bibtex(bib)
    assert len(citations) == 1
    assert citations[0].doi == "10.1016/S0140-6736(97)11096-0"
    assert citations[0].source_label == "wakefield1998"


def test_parse_bibtex_handles_multiple_entries():
    bib = """
    @article{one, title={A}, doi={10.1000/aaa}}
    @book{two, title={B}, doi={10.1000/bbb}}
    """
    citations = parse_bibtex(bib)
    assert [c.doi for c in citations] == ["10.1000/aaa", "10.1000/bbb"]
    assert [c.source_label for c in citations] == ["one", "two"]


def test_parse_bibtex_falls_back_to_scanning_entry_body_when_no_doi_field():
    bib = """
    @article{key1,
      title = {Some paper},
      url = {https://doi.org/10.1000/ccc}
    }
    """
    citations = parse_bibtex(bib)
    assert len(citations) == 1
    assert citations[0].doi == "10.1000/ccc"


def test_parse_bibtex_skips_entries_with_no_doi_at_all():
    bib = "@article{key1, title = {No DOI here}}"
    assert parse_bibtex(bib) == []


def test_parse_bibtex_ignores_comment_entries():
    bib = """
    @comment{This is just a comment with 10.1000/fake in it}
    @article{real, doi = {10.1000/real}}
    """
    citations = parse_bibtex(bib)
    assert len(citations) == 1
    assert citations[0].doi == "10.1000/real"


def test_parse_bibtex_handles_nested_braces_in_fields():
    bib = """
    @article{key1,
      title = {A Study of {DNA} Structure},
      doi = {10.1000/nested}
    }
    """
    citations = parse_bibtex(bib)
    assert len(citations) == 1
    assert citations[0].doi == "10.1000/nested"


def test_parse_bibtex_quoted_field_syntax():
    bib = '@article{key1, doi = "10.1000/quoted"}'
    citations = parse_bibtex(bib)
    assert citations[0].doi == "10.1000/quoted"


# -- parse_ris --------------------------------------------------------------------


def test_parse_ris_extracts_doi_from_do_tag():
    ris = """TY  - JOUR
AU  - Smith, J.
TI  - A great paper
DO  - 10.1000/ris-example
ER  -
"""
    citations = parse_ris(ris)
    assert len(citations) == 1
    assert citations[0].doi == "10.1000/ris-example"


def test_parse_ris_falls_back_to_url_field():
    ris = """TY  - JOUR
TI  - Another paper
UR  - https://doi.org/10.1000/from-url
ER  -
"""
    citations = parse_ris(ris)
    assert citations[0].doi == "10.1000/from-url"


def test_parse_ris_handles_multiple_records():
    ris = """TY  - JOUR
DO  - 10.1000/first
ER  -
TY  - JOUR
DO  - 10.1000/second
ER  -
"""
    citations = parse_ris(ris)
    assert [c.doi for c in citations] == ["10.1000/first", "10.1000/second"]


def test_parse_ris_skips_records_with_no_doi():
    ris = """TY  - JOUR
TI  - No DOI here
ER  -
"""
    assert parse_ris(ris) == []
