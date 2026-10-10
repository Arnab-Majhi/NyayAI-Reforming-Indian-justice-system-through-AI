"use client";
import { useEffect, useState, type ReactNode } from "react";
import { AlertCircle, Download, LoaderCircle, SearchCheck } from "lucide-react";
import { api, downloadJSON, type Passage } from "@/lib/api";

export function useResource<T>(path: string, refresh = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true; setLoading(true); setError("");
    api<T>(path).then(value => { if (active) setData(value); }).catch((e: Error) => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, refresh]);
  return { data, error, loading };
}
export function Notice({ children, danger = false }: { children: ReactNode; danger?: boolean }) {
  return <div className={`notice ${danger ? "danger" : ""}`} role={danger ? "alert" : "note"}><AlertCircle size={18} /><div>{children}</div></div>;
}
export function Loading() { return <div className="skeleton" role="status"><LoaderCircle className="spin" size={20} /> Loading sample records…</div>; }
export function Empty({ children = "No records match your selection." }: { children?: ReactNode }) { return <div className="empty"><SearchCheck size={30} /><p>{children}</p></div>; }
export function Badge({ children }: { children: ReactNode }) {
  const text = String(children).toLowerCase();
  return <span className={`badge ${["pass", "ready", "complete", "low", "closed"].includes(text) ? "green" : ["fail", "failed", "high"].includes(text) ? "red" : ""}`}>{children}</span>;
}
export function Panel({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return <section className="panel"><div className="panel-heading"><h2>{title}</h2>{action}</div>{children}</section>;
}
export function ExportButton({ value, name = "nyayaai-report" }: { value: unknown; name?: string }) {
  return <button className="secondary" onClick={() => downloadJSON(value, name)}><Download size={16} /> Download report</button>;
}
export function Sources({ passages }: { passages: Passage[] }) {
  if (!passages.length) return <Empty>No supporting passages in the approved corpus. Further authoritative research is required.</Empty>;
  return <div className="stack">{passages.map(p => <article className="source" key={p.passage_id}>
    <span className="eyebrow">{p.passage_id}</span><h3>{p.title}</h3><blockquote>{p.text}</blockquote>
    <p className="muted small">Publication: {p.publication_date || "unknown"} · Effective: {p.effective_date || "not established"} · Checked: {p.verified_on || "unverified"}</p>
    <p className="small">{p.verification_status}</p>{p.url && <a href={p.url} target="_blank" rel="noreferrer">Inspect official source ↗</a>}
  </article>)}</div>;
}
export function ErrorMessage({ error }: { error: string }) { return error ? <Notice danger>{error}</Notice> : null; }