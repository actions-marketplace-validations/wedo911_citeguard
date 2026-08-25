/**
 * Turn a raw Crossref "work" message into a RetractionStatus.
 *
 * Ported line-for-line in spirit from the Python implementation
 * (../../../src/citeguard/analyze.py) and verified against the same real
 * Crossref fixtures (tests/fixtures/) so both surfaces agree on ground
 * truth, not just on their own unit tests. See the Python module's
 * docstring for the full empirical rationale behind checking three
 * distinct signal sources (update-to, updated-by, title prefix).
 */

import type { RetractionStatus, Signal, SignalType, Verdict } from "./models.js";

const RELEVANT_TYPES: Record<string, SignalType> = {
  retraction: "retraction",
  removal: "removal",
  expression_of_concern: "expression_of_concern",
  correction: "correction",
};

const TITLE_PREFIX_RE = /^\s*(RETRACTED(?:\s+ARTICLE)?|RETRACTION|WITHDRAWN|EXPRESSION OF CONCERN|CORRIGENDUM)\s*:/i;

const TITLE_PREFIX_SIGNAL_TYPE: Record<string, SignalType> = {
  RETRACTED: "retraction",
  "RETRACTED ARTICLE": "retraction",
  RETRACTION: "retraction",
  WITHDRAWN: "retraction",
  "EXPRESSION OF CONCERN": "expression_of_concern",
  CORRIGENDUM: "correction",
};

interface UpdateItem {
  type?: string;
  source?: string;
  label?: string;
  DOI?: string;
  updated?: { "date-parts"?: number[][] };
}

function extractFieldSignals(items: UpdateItem[] | undefined): Signal[] {
  const signals: Signal[] = [];
  for (const item of items ?? []) {
    const sigType = item.type ? RELEVANT_TYPES[item.type] : undefined;
    if (!sigType) continue;
    const dateParts = item.updated?.["date-parts"]?.[0];
    const date = dateParts ? dateParts.map((p) => String(p).padStart(2, "0")).join("-") : null;
    signals.push({
      type: sigType,
      source: item.source ?? "publisher",
      label: item.label ?? null,
      noticeDoi: item.DOI ?? null,
      date,
    });
  }
  return signals;
}

function titleText(message: Record<string, unknown>): string {
  const titles = (message.title as string[] | undefined) ?? [];
  return titles.join(" ").trim();
}

export function analyzeWork(message: Record<string, unknown>): RetractionStatus {
  const doi = (message.DOI as string) ?? "";
  const title = titleText(message) || null;

  let signals = extractFieldSignals(message["update-to"] as UpdateItem[] | undefined);
  signals = signals.concat(extractFieldSignals(message["updated-by"] as UpdateItem[] | undefined));

  if (signals.length === 0 && title) {
    const match = TITLE_PREFIX_RE.exec(title);
    if (match) {
      const matchedLabel = match[1];
      const sigType = TITLE_PREFIX_SIGNAL_TYPE[matchedLabel.toUpperCase()] ?? "retraction";
      signals.push({ type: sigType, source: "title_prefix", label: matchedLabel, noticeDoi: null, date: null });
    }
  }

  return { doi, verdict: verdictFromSignals(signals), title, signals, error: null };
}

function verdictFromSignals(signals: Signal[]): Verdict {
  const types = new Set(signals.map((s) => s.type));
  if (types.has("retraction") || types.has("removal")) return "retracted";
  if (types.has("expression_of_concern")) return "concern";
  if (types.has("correction")) return "corrected";
  return "clean";
}
