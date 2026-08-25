"""Command-line interface.

    citeguard doi 10.1016/S0140-6736(97)11096-0
    citeguard file references.bib
    citeguard file paper.md --format json
    citeguard file references.bib --fail-on retracted   # CI use
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cache import FileCache
from .checker import check_dois
from .crossref import build_fetcher, polite_fetcher
from .models import RetractionStatus, Verdict
from .parsers import extract_dois, parse_bibtex, parse_ris

_FAIL_LEVELS = {
    "never": (),
    "retracted": (Verdict.RETRACTED,),
    "concern": (Verdict.RETRACTED, Verdict.CONCERN),
    "corrected": (Verdict.RETRACTED, Verdict.CONCERN, Verdict.CORRECTED),
}

_VERDICT_LABEL = {
    Verdict.RETRACTED: "RETRACTED",
    Verdict.CONCERN: "EXPRESSION OF CONCERN",
    Verdict.CORRECTED: "corrected",
    Verdict.CLEAN: "clean",
    Verdict.NOT_FOUND: "not found in Crossref",
    Verdict.ERROR: "error",
}


def _dois_from_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()
    if suffix in (".bib", ".bibtex"):
        return [c.doi for c in parse_bibtex(text)]
    if suffix == ".ris":
        return [c.doi for c in parse_ris(text)]
    return extract_dois(text)


def _render_text(results: list[RetractionStatus]) -> str:
    lines = []
    problematic = [r for r in results if r.is_problematic]
    lines.append(f"Checked {len(results)} DOI(s); {len(problematic)} flagged.")
    lines.append("")
    for r in results:
        if r.verdict == Verdict.CLEAN:
            continue
        lines.append(f"[{_VERDICT_LABEL[r.verdict]}] {r.doi}")
        if r.title:
            lines.append(f"    {r.title}")
        for s in r.signals:
            notice = f" -> notice {s.notice_doi}" if s.notice_doi else ""
            date = f" ({s.date})" if s.date else ""
            lines.append(f"    signal: {s.type.value} via {s.source}{date}{notice}")
        if r.error:
            lines.append(f"    error: {r.error}")
        lines.append("")
    if not problematic:
        lines.append("No retracted, concerning, or corrected citations found among the clean/checked DOIs.")
    return "\n".join(lines).rstrip() + "\n"


def _render_json(results: list[RetractionStatus]) -> str:
    payload = [
        {
            "doi": r.doi,
            "verdict": r.verdict.value,
            "title": r.title,
            "error": r.error,
            "signals": [
                {"type": s.type.value, "source": s.source, "label": s.label, "notice_doi": s.notice_doi, "date": s.date}
                for s in r.signals
            ],
        }
        for r in results
    ]
    return json.dumps(payload, indent=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="citeguard", description="Check citations for retractions, corrections, and expressions of concern via Crossref.")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--format", choices=["text", "json"], default="text")
    common.add_argument("--mailto", help="Contact email for Crossref's polite API pool (recommended).")
    common.add_argument("--cache", help="Path to a JSON cache file to read from and write to.")
    common.add_argument("--no-cache", action="store_true", help="Disable caching even if --cache is set.")
    common.add_argument("--fail-on", choices=list(_FAIL_LEVELS), default="concern", help="Exit non-zero if any result reaches this severity or worse (default: concern).")

    doi_cmd = sub.add_parser("doi", parents=[common], help="Check one or more DOIs directly.")
    doi_cmd.add_argument("dois", nargs="+")

    file_cmd = sub.add_parser("file", parents=[common], help="Check every DOI found in a file (.bib, .ris, or plain text).")
    file_cmd.add_argument("path", type=Path)

    args = parser.parse_args(argv)

    if args.command == "doi":
        dois = args.dois
    else:
        if not args.path.exists():
            print(f"Error: {args.path} does not exist", file=sys.stderr)
            return 2
        dois = _dois_from_file(args.path)
        if not dois:
            print("No DOIs found in the input.", file=sys.stderr)
            return 0

    fetch = polite_fetcher(build_fetcher(contact_email=args.mailto))
    cache = None
    if args.cache and not args.no_cache:
        cache = FileCache(args.cache)

    results = check_dois(dois, fetch=fetch, cache=cache)

    if cache:
        cache.save()

    output = _render_json(results) if args.format == "json" else _render_text(results)
    print(output)

    fail_verdicts = _FAIL_LEVELS[args.fail_on]
    if any(r.verdict in fail_verdicts for r in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
