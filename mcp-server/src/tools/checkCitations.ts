import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { checkDois } from "../services/checker.js";
import { extractDois } from "../services/parsers.js";
import { isProblematic, type RetractionStatus } from "../services/models.js";
import { MAX_TEXT_LENGTH, MAX_DOIS_PER_CALL } from "../constants.js";

const CheckCitationsInputSchema = z
  .object({
    text: z
      .string()
      .min(1, "text must not be empty")
      .max(MAX_TEXT_LENGTH, `text must not exceed ${MAX_TEXT_LENGTH} characters`)
      .describe("Free text to scan for DOIs -- a reference list, a paper draft with inline citations, or a bibliography exported as plain text."),
  })
  .strict();

type CheckCitationsInput = z.infer<typeof CheckCitationsInputSchema>;

function renderMarkdown(results: RetractionStatus[]): string {
  const problematic = results.filter(isProblematic);
  const lines = [`# Checked ${results.length} DOI(s); ${problematic.length} flagged`, ""];
  if (problematic.length === 0) {
    lines.push("No retracted, concerning citations found.");
    return lines.join("\n");
  }
  for (const r of problematic) {
    lines.push(`- **[${r.verdict.toUpperCase()}]** ${r.doi}${r.title ? ` — ${r.title}` : ""}`);
  }
  return lines.join("\n");
}

export function registerCheckCitations(server: McpServer): void {
  server.registerTool(
    "check_citations",
    {
      title: "Check All Citations in a Block of Text",
      description: `Extract every DOI found in a block of text (a reference list, a paper draft, an exported bibliography) and check each one for retraction/correction/expression-of-concern status via Crossref. Use this to sanity-check a whole reference list at once before finalizing a document, rather than checking citations one at a time.

Finds DOIs in any form: bare ("10.1016/S0140-6736(97)11096-0"), as a doi.org URL, or embedded in a formatted citation. Up to ${MAX_DOIS_PER_CALL} unique DOIs are checked per call; if more are found, only the first ${MAX_DOIS_PER_CALL} (in order of first appearance) are checked and the response says so.

Args:
  - text (string, 1-${MAX_TEXT_LENGTH} chars): the text to scan.

Returns:
  For JSON format: {
    "totalFound": number,
    "checked": number,
    "truncated": boolean,
    "results": [ { "doi": string, "verdict": string, "title": string|null, "signals": [...], "error": string|null } ]
  }

Examples:
  - Use when: finishing a literature review or research summary -- paste the whole reference list to check it in one call
  - Don't use when: checking just one citation you already have the DOI for -- use check_citation instead, it's simpler

Error Handling:
  - Returns an error if text is empty or exceeds ${MAX_TEXT_LENGTH} characters. Text with no DOI-shaped substrings returns totalFound: 0, not an error.`,
      inputSchema: CheckCitationsInputSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: CheckCitationsInput) => {
      const allDois = extractDois(params.text);
      const truncated = allDois.length > MAX_DOIS_PER_CALL;
      const dois = allDois.slice(0, MAX_DOIS_PER_CALL);

      const results = dois.length > 0 ? await checkDois(dois) : [];

      const output = {
        totalFound: allDois.length,
        checked: results.length,
        truncated,
        results: results.map((r) => ({ ...r, isProblematic: isProblematic(r) })),
      };

      const text =
        dois.length === 0
          ? "# No DOIs found\n\nNo DOI-shaped substrings were found in the given text."
          : renderMarkdown(results) + (truncated ? `\n\n(Only the first ${MAX_DOIS_PER_CALL} of ${allDois.length} DOIs found were checked.)` : "");

      return {
        content: [{ type: "text" as const, text }],
        structuredContent: output as unknown as Record<string, unknown>,
      };
    }
  );
}
