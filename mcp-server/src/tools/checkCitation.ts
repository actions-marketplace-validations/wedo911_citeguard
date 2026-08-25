import { z } from "zod";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { checkDoi } from "../services/checker.js";
import { isProblematic, type RetractionStatus } from "../services/models.js";

const CheckCitationInputSchema = z
  .object({
    doi: z
      .string()
      .min(1, "doi must not be empty")
      .max(500, "doi must not exceed 500 characters")
      .describe('A DOI, e.g. "10.1016/S0140-6736(97)11096-0" (with or without a "https://doi.org/" prefix).'),
  })
  .strict();

type CheckCitationInput = z.infer<typeof CheckCitationInputSchema>;

function stripDoiPrefix(input: string): string {
  return input.replace(/^https?:\/\/(dx\.)?doi\.org\//i, "").replace(/^doi:\s*/i, "");
}

function renderMarkdown(result: RetractionStatus): string {
  if (result.verdict === "not_found") return `# Not found\n\n${result.error}`;
  if (result.verdict === "error") return `# Could not check\n\n${result.error}`;
  if (result.verdict === "clean") return `# Clean\n\nNo retraction, correction, or expression-of-concern signal found for this DOI.`;

  const lines = [`# ${result.verdict.toUpperCase()}`, "", result.title ? `**${result.title}**` : "", ""];
  for (const s of result.signals) {
    const notice = s.noticeDoi ? ` -> notice ${s.noticeDoi}` : "";
    const date = s.date ? ` (${s.date})` : "";
    lines.push(`- ${s.type} via ${s.source}${date}${notice}`);
  }
  return lines.join("\n");
}

export function registerCheckCitation(server: McpServer): void {
  server.registerTool(
    "check_citation",
    {
      title: "Check a Citation for Retraction",
      description: `Check a single DOI against Crossref for retraction, correction, or expression-of-concern status. Use this before citing a paper in a document, summary, or literature review -- retracted papers (including fraudulent or debunked ones) continue to be cited for years after retraction, often because whoever is citing them has no easy way to check. This tool checks three independent signal sources: publisher-asserted updates, Crossref's ingested Retraction Watch data (which catches many retractions the publisher's own metadata misses), and a title-prefix fallback ("RETRACTED:", etc.) for older or unlinked cases.

Args:
  - doi (string): a DOI, with or without a "https://doi.org/" prefix.

Returns:
  For JSON format: {
    "doi": string,
    "verdict": "retracted" | "concern" | "corrected" | "clean" | "not_found" | "error",
    "title": string | null,
    "signals": [ { "type": string, "source": string, "label": string | null, "noticeDoi": string | null, "date": string | null } ],
    "error": string | null
  }

Examples:
  - Use when: about to cite a paper in a summary, report, or literature review -- check it first
  - Use when: reviewing someone else's bibliography for outdated or unreliable sources
  - Don't use when: you need to verify a claim's accuracy generally -- this only checks retraction status, not whether the paper's content is correct

Error Handling:
  - A DOI Crossref doesn't recognize returns verdict "not_found", not an error -- it may still be a real paper Crossref just doesn't index (e.g. some preprints), not necessarily an invalid citation.`,
      inputSchema: CheckCitationInputSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: CheckCitationInput) => {
      const doi = stripDoiPrefix(params.doi.trim());
      const result = await checkDoi(doi);
      return {
        content: [{ type: "text" as const, text: renderMarkdown(result) }],
        structuredContent: { ...result, isProblematic: isProblematic(result) } as unknown as Record<string, unknown>,
      };
    }
  );
}
