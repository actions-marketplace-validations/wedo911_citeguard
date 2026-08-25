# citeguard

Retracted papers get cited for years after retraction. Andrew Wakefield's
fraudulent 1998 paper linking the MMR vaccine to autism — retracted in
2010 — has been cited well over a thousand times *since* its retraction,
by researchers who had no easy way to know. A 2026 JMIR study found that
freely available AI tools "cannot reliably flag retracted literature,"
right as AI-assisted research and writing has exploded. citeguard closes
that gap: check a citation against [Crossref](https://www.crossref.org/)
— free, no API key — before it goes in a paper, a summary, or a review.

Three surfaces, one verified detection algorithm:

| Surface | For | Location |
|---|---|---|
| **Python library + CLI** | academic writers, scripts | [`src/citeguard/`](src/citeguard/) |
| **MCP server** | AI agents doing research/writing | [`mcp-server/`](mcp-server/) |
| **GitHub Action** | CI on a lab's or journal's repo | [`action.yml`](action.yml) |

## Why this is built the way it is

The detection logic isn't guessed at from documentation — it was built by
querying Crossref's real API for known cases and reading the actual
response shapes, then writing tests against the saved real responses
(committed in `tests/fixtures/`, shared by both the Python and TypeScript
implementations). Two real papers anchor the ground truth:

- **[Wakefield et al., 1998, *The Lancet*](https://doi.org/10.1016/S0140-6736(97)11096-0)**
  (the MMR-autism paper): the publisher's own Crossref metadata has *no*
  structured retraction data — an `update-to` check alone would silently
  miss it. What actually carries the signal is a separate `updated-by`
  field, where Crossref has backfilled the retraction (and an earlier
  2004 correction) from the **Retraction Watch database** itself. Missing
  this field would have meant missing the single most famous retracted
  paper in medicine.
- **[Mehra et al., 2020, *The Lancet*](https://doi.org/10.1016/S0140-6736(20)31180-6)**
  (the Surgisphere-linked COVID/hydroxychloroquine paper): here the
  *publisher* did attach structured data directly, via `update-to`. A
  different field, a different provenance, same underlying fact.
- **[Watson & Crick, 1953, *Nature*](https://doi.org/10.1038/171737a0)**
  serves as the clean control in every test suite — a definitely-real,
  definitely-not-retracted paper that must never be flagged.

So the checker looks at three independent signals, in order: `update-to`
(publisher-asserted), `updated-by` (often Retraction-Watch-sourced,
catching what publishers miss), and a title-prefix fallback
("RETRACTED:", "WITHDRAWN:", etc.) for older or unlinked cases with no
structured metadata on either field. Each signal is mapped to the right
severity — an "Expression of Concern:" title is not the same thing as a
retraction, and earlier versions of this code collapsing that distinction
was itself a bug caught by testing against real titles, not just
synthetic ones. See [`src/citeguard/analyze.py`](src/citeguard/analyze.py)
for the fully-commented implementation.

## Quick start

**CLI:**

```bash
pip install -e .
citeguard doi 10.1016/S0140-6736(97)11096-0
citeguard file references.bib --fail-on retracted   # for CI, see below
```

**MCP server** (add to your client's config, e.g. `.mcp.json`):

```json
{ "mcpServers": { "citeguard": { "command": "node", "args": ["/path/to/citeguard/mcp-server/dist/index.js"] } } }
```

**GitHub Action** (in another repo's workflow):

```yaml
- uses: wedo911/citeguard@main
  with:
    path: references.bib
    fail-on: concern   # never | retracted | concern | corrected
```

## What this is *not*

- **Not proof a paper's content is correct.** It only checks retraction
  status, not whether a non-retracted paper's findings hold up.
- **Not exhaustive.** The title-prefix heuristic only catches the
  publisher conventions it's been tested against; a clean result means
  "no known signal found," not "guaranteed never retracted."
- **Not a bulk-scraping tool.** It's built for the size of a real
  bibliography (tens of citations), with a small fixed delay between
  Crossref requests and an optional persistent cache
  ([`src/citeguard/cache.py`](src/citeguard/cache.py)) — good API
  citizenship for a free public service, not a tool for scanning millions
  of DOIs.

## Running the tests

```bash
# Python (55 tests, including against the real fixtures above)
pip install -e ".[dev]" && pytest -v

# MCP server (17 tests against the same real fixtures)
cd mcp-server && npm install && npm run build && npm test
```

Both suites are network-free and deterministic — they run against the
committed real API responses, not live calls, so they're fast and don't
depend on Crossref being reachable. Live end-to-end behavior (the actual
CLI, the actual MCP tool, hitting the real API) was separately verified
by hand during development; the GitHub Action additionally has its own
CI job (`action-smoke-test`) that runs the real composite action against
a known-retracted and a known-clean bibliography on every push, so the
Action itself — not just the underlying library — is continuously
verified against the live API.

## Contributing

New signal types, additional publisher title conventions, and
false-positive reports are all welcome. If you add a case, prefer adding
it as a real, cited Crossref fixture over a synthetic one where possible
— that's what caught the two real bugs this project's own test suite
found during development (a URL-encoding bug in the DOI request path, and
a BibTeX parser that could swallow an adjacent entry when parsing a
malformed `@comment` block).

## License

MIT — see [LICENSE](LICENSE).
