export type User = { id: string; name: string; role: "citizen" | "staff" | "admin" };
export type Task = { id: string; case_id: string; title: string; deadline: string; status: string; assigned_staff: string };
export type DocumentRecord = { id: string; filename: string; processing_status: string; warnings?: string[]; extracted_text?: string; sections?: { location: string; text: string }[] };
export type Risk = { case_id: string; reference: string; probability: number; band: string; reasons: string[]; features: Record<string, number>; model_version: string; limitations: string };
export type CaseRecord = {
  id: string; reference: string; title: string; category: string; court: string; stage: string; status: string;
  filing_date: string; next_hearing: string | null; assigned_staff: string; updated_at: string;
  scenario: { summary?: string; claimant?: string; opponent?: string; evidence?: string; questions?: string };
  tasks?: Task[]; documents?: DocumentRecord[]; events: { id: string; at: string; type: string; note: string }[];
  risk?: Risk; reports?: { id: string; created_at: string; label: string }[]; filings?: FilingReport[];
};
export type Passage = { passage_id: string; source_id: string; text: string; title: string; url: string | null; publication_date: string | null; effective_date: string | null; verified_on: string | null; verification_status: string };
export type ResearchResult = { question: string; mode: string; answer: string; passages: Passage[]; citations: string[]; limitations: string; next_steps: string[]; follow_up: string };
export type FilingReport = { id: string; checks: { check_id: string; requirement: string; status: string; explanation: string; correction: string; document_id: string | null; evidence_location: string | null }[]; summary: Record<string, number>; limitations: string; rules: { title: string; applicability: string } };
export type Overview = { total: number; pending: number; upcoming: number; overdue: number; filings: number; documents: number; recently_updated: number; storage: string; categories: Count[]; workload: Count[]; stages: Count[]; risk_bands: Count[]; risks: Risk[]; filing_trend: Count[]; recent_research: { id: string; question: string }[]; projection: { expected_delayed_milestones: number; assumption: string } };
export type Count = { name: string; count: number };
export type DecisionReport = { id: string; label: string; mode: string; case_summary: string; alleged_provisions: string; facts: { id: string; classification: string; text: string; source: string }[]; issues: string[]; legal_sources: Passage[]; legal_elements: { requirement: string; unresolved: string }[]; both_sides: { issue: string; claimant_argument: string; opposing_argument: string; evidence_references: string[]; uncertainty: string; human_examination: string }[]; potential_contradictions: { reference: string; observation: string; status: string }[]; missing_information: string[]; scenarios: { outcome: string; assumptions: string; reasoning: string }[]; human_questions: string[]; limitations: string; model_version: string; human_review_status: string };

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("X-Nyaya-Request", "1");
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`/api${path}`, { ...options, headers, credentials: "same-origin", cache: "no-store" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Server unavailable. Start the FastAPI backend and retry." }));
    const detail: unknown = body.detail;
    throw new Error(typeof detail === "string" ? detail : Array.isArray(detail) ? "Please check the required fields and formats." : JSON.stringify(detail));
  }
  return response.json() as Promise<T>;
}
export const post = <T>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export function downloadJSON(value: unknown, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const link = document.createElement("a"); link.href = url; link.download = `${name}.json`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function displayDate(value: string | null) {
  if (!value) return "Not scheduled";
  return new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" });
}