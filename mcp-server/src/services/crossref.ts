/**
 * Minimal Crossref REST API client using the native `fetch` (Node 18+) --
 * no HTTP library dependency. Mirrors ../../../src/citeguard/crossref.py.
 */

const CROSSREF_BASE_URL = "https://api.crossref.org/works";
const DEFAULT_USER_AGENT = "citeguard-mcp-server/1.0 (https://github.com/wedo911/citeguard)";

export class DoiNotFoundError extends Error {
  constructor(doi: string) {
    super(`DOI not found in Crossref: ${doi}`);
    this.name = "DoiNotFoundError";
  }
}

export class CrossrefError extends Error {}

export type Fetcher = (doi: string) => Promise<Record<string, unknown>>;

export function buildFetcher(options: { contactEmail?: string; timeoutMs?: number } = {}): Fetcher {
  const userAgent = options.contactEmail ? `${DEFAULT_USER_AGENT} (mailto:${options.contactEmail})` : DEFAULT_USER_AGENT;
  const timeoutMs = options.timeoutMs ?? 10000;

  return async function fetchWork(doi: string): Promise<Record<string, unknown>> {
    const url = `${CROSSREF_BASE_URL}/${encodeURIComponent(doi)}`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    let response: Response;
    try {
      response = await fetch(url, { headers: { "User-Agent": userAgent }, signal: controller.signal });
    } catch (err) {
      throw new CrossrefError(
        `Network error contacting Crossref for ${doi}: ${(err as Error).message}. ` +
          "If this happens for every DOI, your MCP client may be spawning this server with a " +
          "minimal environment that drops a variable needed for outbound HTTPS in your network " +
          "(e.g. NODE_EXTRA_CA_CERTS for corporate/antivirus TLS inspection, or HTTP(S)_PROXY) -- " +
          "many MCP clients only pass a small default env allowlist to child processes rather than " +
          "the full parent environment. Try configuring your client to inherit the full environment, " +
          "or explicitly pass the specific variable your network requires. See the README's " +
          "Troubleshooting section."
      );
    } finally {
      clearTimeout(timeout);
    }

    if (response.status === 404) {
      throw new DoiNotFoundError(doi);
    }
    if (!response.ok) {
      throw new CrossrefError(`Crossref returned HTTP ${response.status} for ${doi}`);
    }

    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new CrossrefError(`Crossref returned malformed JSON for ${doi}`);
    }

    const message = (payload as { message?: unknown })?.message;
    if (!message || typeof message !== "object") {
      throw new CrossrefError(`Crossref response for ${doi} had no 'message' object`);
    }
    return message as Record<string, unknown>;
  };
}

/** Wrap a fetcher with a small fixed delay so checking many DOIs doesn't hammer Crossref. */
export function politeFetcher(fetcher: Fetcher, delayMs = 100): Fetcher {
  return async (doi: string) => {
    const result = await fetcher(doi);
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    return result;
  };
}
