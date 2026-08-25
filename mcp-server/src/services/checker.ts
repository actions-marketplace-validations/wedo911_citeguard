import { analyzeWork } from "./analyze.js";
import { buildFetcher, CrossrefError, DoiNotFoundError, type Fetcher } from "./crossref.js";
import type { RetractionStatus } from "./models.js";

/** Check a single DOI. Never throws for an expected failure -- becomes a NOT_FOUND/ERROR verdict instead. */
export async function checkDoi(doi: string, fetch?: Fetcher): Promise<RetractionStatus> {
  const fetcher = fetch ?? buildFetcher();
  try {
    const message = await fetcher(doi);
    return analyzeWork(message);
  } catch (err) {
    if (err instanceof DoiNotFoundError) {
      return { doi, verdict: "not_found", title: null, signals: [], error: err.message };
    }
    if (err instanceof CrossrefError) {
      return { doi, verdict: "error", title: null, signals: [], error: err.message };
    }
    throw err;
  }
}

/** Check multiple DOIs, preserving order; duplicates are only fetched once. */
export async function checkDois(dois: string[], fetch?: Fetcher): Promise<RetractionStatus[]> {
  const fetcher = fetch ?? buildFetcher();
  const cache = new Map<string, Promise<RetractionStatus>>();
  for (const doi of dois) {
    if (!cache.has(doi)) cache.set(doi, checkDoi(doi, fetcher));
  }
  const results = await Promise.all(dois.map((doi) => cache.get(doi)!));
  return results;
}
