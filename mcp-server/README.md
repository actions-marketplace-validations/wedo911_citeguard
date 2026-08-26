# citeguard-mcp-server

An [MCP](https://modelcontextprotocol.io) server that checks a citation
against [Crossref](https://www.crossref.org/) for retraction, correction,
or expression-of-concern status — so an AI agent doing research, writing,
or literature review can check its own citations before including them.
No API key required; Crossref's REST API is free and open.

Part of the [citeguard](https://github.com/wedo911/citeguard) project —
see the repository root for the shared detection logic and the Python
CLI/library. This server is an independent TypeScript implementation of
the same, empirically-verified detection algorithm, tested against the
same real Crossref fixtures as the Python package (`tests/fixtures/`) so
both surfaces agree on ground truth.

## Tools

- **`check_citation`** — check a single DOI.
- **`check_citations`** — extract every DOI from a block of text (a
  reference list, a paper draft) and check them all in one call.

## Install and configure

Nothing to clone or build — add this to your MCP client's config
(e.g. `claude_desktop_config.json`, or a project's `.mcp.json` for
Claude Code):

```json
{
  "mcpServers": {
    "citeguard": {
      "command": "npx",
      "args": ["-y", "citeguard-mcp-server"]
    }
  }
}
```

<details>
<summary>Running from a local checkout instead</summary>

```bash
git clone https://github.com/wedo911/citeguard.git
cd citeguard/mcp-server
npm install
npm run build
```

```json
{
  "mcpServers": {
    "citeguard": {
      "command": "node",
      "args": ["/absolute/path/to/citeguard/mcp-server/dist/index.js"]
    }
  }
}
```

</details>

## Troubleshooting: network errors for every DOI

If `check_citation` fails on *every* DOI (not just retracted or unusual
ones) with a network/fetch error, this is very likely an environment
issue, not a bug: many MCP clients spawn servers with a minimal,
security-conscious environment — the official SDK's default, for example,
only passes through `HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM`, and `USER`,
not your full shell environment. If your network requires something
outside that list to make outbound HTTPS calls — `NODE_EXTRA_CA_CERTS`
(common with corporate proxies or antivirus TLS inspection, e.g. Norton),
`HTTP_PROXY`/`HTTPS_PROXY`, or similar — the spawned server won't have it
and every HTTPS request will fail with a generic error.

This is exactly what happened during this project's own development and
testing: this server's Crossref client was independently verified correct
via direct execution, then failed with `fetch failed` the moment it was
spawned as a child process by an MCP client using default environment
inheritance — resolved once `NODE_EXTRA_CA_CERTS` was included in the
spawned environment. If you hit this, configure your MCP client to pass
through the specific variable your network needs (check your client's
documentation for an `env` field in its server configuration).

## Run the tests

```bash
npm run build
node --test tests/analyze.test.mjs tests/parsers.test.mjs
```

## Try it without a client

```bash
npx @modelcontextprotocol/inspector --cli node dist/index.js \
  --method tools/call --tool-name check_citation \
  --tool-arg doi="10.1016/S0140-6736(97)11096-0"
```

## License

MIT — see [LICENSE](../LICENSE) in the repository root.
