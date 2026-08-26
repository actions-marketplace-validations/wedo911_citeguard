#!/usr/bin/env node
/**
 * citeguard-mcp-server
 *
 * No API key required -- Crossref's REST API is free and open. Lets any
 * MCP-compatible agent check whether a citation it's about to use has
 * been retracted, corrected, or flagged with an expression of concern,
 * before that citation ends up in a summary, report, or literature
 * review. Shares its detection logic and real-world test fixtures with
 * the sibling Python package in this repository (../src/citeguard).
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerCheckCitation } from "./tools/checkCitation.js";
import { registerCheckCitations } from "./tools/checkCitations.js";

const server = new McpServer({
  name: "citeguard-mcp-server",
  version: "0.1.2",
});

registerCheckCitation(server);
registerCheckCitations(server);

async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("citeguard-mcp-server running via stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
