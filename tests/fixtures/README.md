# Fixtures

Real, unmodified Crossref API responses (`https://api.crossref.org/works/{doi}`),
captured during development and used as ground truth by the test suite —
not hand-written approximations of what the API might return. The same
three files are duplicated in `../../mcp-server/tests/fixtures/` so both
the Python and TypeScript implementations are tested against identical
ground truth.

| File | DOI | Why it's here |
|---|---|---|
| `wakefield_1998.json` | `10.1016/S0140-6736(97)11096-0` | The retracted 1998 MMR-autism paper. Has an *empty* `update-to` — the publisher never added structured retraction metadata — but a populated `updated-by` with `source: "retraction-watch"`, recording both a 2004 correction and the 2010 retraction. This is the case that proves checking `update-to` alone is not enough. |
| `surgisphere_mehra_2020.json` | `10.1016/S0140-6736(20)31180-6` | The Surgisphere-linked hydroxychloroquine paper, retracted in 2020. Has a populated `update-to` with `source: "publisher"` — the opposite provenance from the Wakefield case. |
| `watson_crick_1953_clean.json` | `10.1038/171737a0` | Watson & Crick's DNA structure paper — a famous, definitely-not-retracted control. Has no `update-to`, no `updated-by`, and an empty `relation`. Used in every test suite to confirm no false positive. |

To refresh a fixture (Crossref metadata can gain new fields over time):

```bash
curl -s "https://api.crossref.org/works/<doi>" \
  -H "User-Agent: citeguard-fixture-capture/1.0 (mailto:you@example.com)" \
  -o tests/fixtures/<name>.json
```
