/** Extract DOI-shaped substrings from free text -- mirrors extract_dois() in the Python package. */

const DOI_RE = /10\.\d{4,9}\/[-._;()/:A-Za-z0-9]+/g;

function cleanDoi(raw: string): string {
  return raw.replace(/[).,;:\]}"']+$/, "");
}

export function extractDois(text: string): string[] {
  const seen = new Set<string>();
  for (const match of text.matchAll(DOI_RE)) {
    seen.add(cleanDoi(match[0]));
  }
  return [...seen];
}
