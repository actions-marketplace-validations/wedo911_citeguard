import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from citeguard.cli import main


def fake_fetcher_factory(messages):
    def build_fetcher(**kwargs):
        def fetch(doi):
            return messages[doi]

        return fetch

    return build_fetcher


def test_doi_command_clean_exits_zero(capsys):
    messages = {"10.1/a": {"DOI": "10.1/a", "title": ["Fine"]}}
    with patch("citeguard.cli.build_fetcher", fake_fetcher_factory(messages)):
        code = main(["doi", "10.1/a"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Checked 1 DOI" in out


def test_doi_command_retracted_exits_nonzero_by_default(capsys):
    messages = {"10.1/a": {"DOI": "10.1/a", "title": ["RETRACTED: Bad paper"]}}
    with patch("citeguard.cli.build_fetcher", fake_fetcher_factory(messages)):
        code = main(["doi", "10.1/a"])
    assert code == 1
    out = capsys.readouterr().out
    assert "RETRACTED" in out


def test_fail_on_never_always_exits_zero_even_for_retraction(capsys):
    messages = {"10.1/a": {"DOI": "10.1/a", "title": ["RETRACTED: Bad paper"]}}
    with patch("citeguard.cli.build_fetcher", fake_fetcher_factory(messages)):
        code = main(["doi", "10.1/a", "--fail-on", "never"])
    assert code == 0


def test_fail_on_retracted_does_not_fail_on_correction_only(capsys):
    messages = {"10.1/a": {"DOI": "10.1/a", "title": ["Corrigendum: minor fix"]}}
    with patch("citeguard.cli.build_fetcher", fake_fetcher_factory(messages)):
        code = main(["doi", "10.1/a", "--fail-on", "retracted"])
    assert code == 0


def test_json_format_output_is_valid_and_matches_input(capsys):
    messages = {"10.1/a": {"DOI": "10.1/a", "title": ["RETRACTED: Bad paper"]}}
    with patch("citeguard.cli.build_fetcher", fake_fetcher_factory(messages)):
        main(["doi", "10.1/a", "--format", "json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload[0]["doi"] == "10.1/a"
    assert payload[0]["verdict"] == "retracted"


def test_file_command_reads_bibtex_and_checks_its_dois(capsys):
    messages = {"10.1/a": {"DOI": "10.1/a", "title": ["RETRACTED: Bad paper"]}}
    with tempfile.TemporaryDirectory() as tmp:
        bib_path = Path(tmp) / "refs.bib"
        bib_path.write_text("@article{k1, doi = {10.1/a}}", encoding="utf-8")
        with patch("citeguard.cli.build_fetcher", fake_fetcher_factory(messages)):
            code = main(["file", str(bib_path)])
    assert code == 1


def test_file_command_nonexistent_path_exits_2(capsys):
    code = main(["file", "/definitely/does/not/exist.bib"])
    assert code == 2
    err = capsys.readouterr().err
    assert "does not exist" in err


def test_file_command_with_no_dois_exits_zero(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "empty.txt"
        path.write_text("no citations here", encoding="utf-8")
        code = main(["file", str(path)])
    assert code == 0
    err = capsys.readouterr().err
    assert "No DOIs found" in err


def test_multiple_dois_on_command_line(capsys):
    messages = {
        "10.1/a": {"DOI": "10.1/a", "title": ["Fine"]},
        "10.1/b": {"DOI": "10.1/b", "title": ["Also fine"]},
    }
    with patch("citeguard.cli.build_fetcher", fake_fetcher_factory(messages)):
        code = main(["doi", "10.1/a", "10.1/b"])
    assert code == 0
    out = capsys.readouterr().out
    assert "Checked 2 DOI" in out
