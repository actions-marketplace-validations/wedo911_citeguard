export type SignalType = "retraction" | "removal" | "expression_of_concern" | "correction";

export type Verdict = "retracted" | "concern" | "corrected" | "clean" | "not_found" | "error";

export interface Signal {
  type: SignalType;
  source: string;
  label: string | null;
  noticeDoi: string | null;
  date: string | null;
}

export interface RetractionStatus {
  doi: string;
  verdict: Verdict;
  title: string | null;
  signals: Signal[];
  error: string | null;
}

export function isProblematic(status: RetractionStatus): boolean {
  return status.verdict === "retracted" || status.verdict === "concern";
}
