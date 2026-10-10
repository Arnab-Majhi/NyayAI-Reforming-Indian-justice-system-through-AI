"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Bell, BookOpen, ChartNoAxesCombined, ChevronRight, FileCheck2, FolderOpen, LayoutDashboard, LogOut, Menu, MessageSquareText, Scale, Search, Settings, ShieldCheck } from "lucide-react";
import { api, post, type User, type Task } from "@/lib/api";
import { Empty, ErrorMessage, Loading, Notice, Panel, useResource } from "./ui";
import { Dashboard, Analytics } from "./dashboard";
import { Cases } from "./cases";
import { Research, Assistant } from "./research";
import { Filing } from "./filing";
import { Decision } from "./decision";
import { ThemeControl } from "./theme";

const navigation = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "cases", label: "Smart Case Management", icon: FolderOpen },
  { key: "research", label: "Legal Research", icon: BookOpen },
  { key: "filing", label: "Filing Assistant", icon: FileCheck2 },
  { key: "assistant", label: "Citizen Legal Assistant", icon: MessageSquareText },
  { key: "analytics", label: "Predictive Analysis", icon: ChartNoAxesCombined, staff: true },
  { key: "decision", label: "Decision Support", icon: Scale, staff: true },
  { key: "notifications", label: "Notifications", icon: Bell },
  { key: "settings", label: "Settings", icon: Settings },
];
export type Notify = (message: string) => void;

export default function Workspace({ section = "overview" }: { section?: string }) {
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const [mobile, setMobile] = useState(false);
  const [account, setAccount] = useState("citizen-1");
  useEffect(() => {
    const queryAccount = new URLSearchParams(window.location.search).get("account");
    if (queryAccount && ["citizen-1", "staff-1"].includes(queryAccount)) setAccount(queryAccount);
    api<User>("/auth/me").then(setUser).catch(() => setUser(null)).finally(() => setChecking(false));
  }, []);
  useEffect(() => { if (toast) { const timer = setTimeout(() => setToast(""), 5000); return () => clearTimeout(timer); } }, [toast]);
  const signIn = async () => {
    setBusy(true); setError("");
    try { setUser(await post<User>("/auth/login", { account })); setToast("Demo account ready. All case records are fictional."); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  };
  const signOut = async () => {
    try { await post("/auth/logout", {}); setUser(null); } catch (e) { setError((e as Error).message); }
  };
  if (checking) return <main id="main-content" className="auth-page"><Loading /></main>;
  if (!user) return <main id="main-content" className="auth-page"><section className="auth-card"><div className="auth-brand-row"><Link href="/" className="brand"><Scale /><span>Nyaya<span className="brand-accent">AI</span></span></Link><ThemeControl /></div><span className="eyebrow">WELCOME TO THE DEMO</span><h1>A shared workspace.<br />A human-first approach.</h1><p>Choose a fictional account to explore. Citizens can only access their own sample records; court staff can manage the demo registry.</p><label>Demo account<select value={account} onChange={e => setAccount(e.target.value)}><option value="citizen-1">Citizen 1 · own sample cases</option><option value="citizen-2">Citizen 2 · separate sample records</option><option value="citizen-3">Citizen 3 · separate sample records</option><option value="staff-1">Court staff · Registry Officer 1</option><option value="staff-2">Court staff · Registry Officer 2</option><option value="admin-1">Demo administrator</option></select></label><ErrorMessage error={error} /><button onClick={signIn} disabled={busy}>{busy ? "Connecting…" : "Enter demo workspace"}<ChevronRight size={17} /></button><Notice>Public demo access is not production authentication. Use synthetic documents only. No real court records or confidential information.</Notice><Link href="/">← Back to platform overview</Link></section></main>;
  const isStaff = user.role !== "citizen";
  const selected = navigation.find(n => n.key === section);
  const title = selected?.label || "Page not found";
  return <div className="app-shell"><aside className={`sidebar ${mobile ? "open" : ""}`}><Link href="/" className="brand"><Scale /><span>Nyaya<span className="brand-accent">AI</span></span></Link><div className="workspace-label">{isStaff ? "COURT STAFF WORKSPACE" : "CITIZEN WORKSPACE"}</div><nav aria-label="Main navigation">{navigation.filter(n => !n.staff || isStaff).map(n => <Link key={n.key} href={n.key === "overview" ? "/workspace" : `/workspace/${n.key}`} className={section === n.key ? "active" : ""} aria-current={section === n.key ? "page" : undefined} onClick={() => setMobile(false)}><n.icon size={18} />{n.label}</Link>)}</nav><div className="sidebar-bottom"><ShieldCheck size={22} /><strong>Human authority. Always.</strong><p>Sample records, simulated actions and transparent AI limitations.</p><span className="badge">Independent prototype</span></div></aside>
    <div className="workspace"><header className="app-header"><button className="icon-button mobile-menu" aria-label="Toggle navigation" onClick={() => setMobile(!mobile)}><Menu size={22} /></button><form className="global-search" action="/workspace/cases"><Search size={18} /><input name="q" aria-label="Global case search" placeholder="Search authorized sample cases…" /></form><div className="header-account"><ThemeControl /><span className="demo-dot" />Demo environment<span className="avatar">{isStaff ? "RS" : "DC"}</span><div><strong>{user.name.replace(" (fictional)", "")}</strong><small>{user.role}</small></div><button className="icon-button" onClick={signOut} aria-label="Sign out"><LogOut size={18} /></button></div></header>
      <main id="main-content" className="workspace-content"><div className="breadcrumbs">Workspace <ChevronRight size={13} /> {title}</div><div className="page-heading"><div><span className="eyebrow">NYAYAAI · {isStaff ? "COURT OPERATIONS" : "CITIZEN SERVICES"}</span><h1>{title}</h1><p>{section === "overview" ? `Welcome, ${user.name.replace(" (fictional)", "")}. Here is your sample workspace at a glance.` : "Connected information. Traceable sources. Decisions remain with people."}</p></div><span className="badge">All records are synthetic</span></div><ErrorMessage error={error} />
        {!selected ? <Empty>This page does not exist. Use the navigation to choose a module.</Empty> : selected.staff && !isStaff ? <Notice danger>Court staff permission is required. Your account cannot access this module.</Notice> : <>
          {section === "overview" && <Dashboard user={user} />}
          {section === "cases" && <Cases user={user} notify={setToast} />}
          {section === "research" && <Research notify={setToast} />}
          {section === "filing" && <Filing notify={setToast} />}
          {section === "assistant" && <Assistant notify={setToast} />}
          {section === "analytics" && <Analytics />}
          {section === "decision" && <Decision notify={setToast} />}
          {section === "notifications" && <Notifications />}
          {section === "settings" && <SettingsPanel user={user} />}
        </>}<footer className="workspace-footer">NyayaAI is not an official court service. No real filing, hearing booking or binding decision is made here.</footer></main></div>{toast && <div className="toast" role="status"><ShieldCheck size={18} />{toast}<button className="icon-button" aria-label="Dismiss notification" onClick={() => setToast("")}>×</button></div>}</div>;
}

function Notifications() {
  const { data, loading, error } = useResource<{ tasks: Task[]; audit: { id: string; action: string; actor: string; at: string; record_id: string }[] }>("/notifications");
  if (loading) return <Loading />;
  return <><ErrorMessage error={error} />{data && <div className="two-col"><Panel title="Pending tasks & reminders">{!data.tasks.length && <Empty>All tasks are complete.</Empty>}{data.tasks.map(t => <Link className="list-row" href={`/workspace/cases?case=${t.case_id}`} key={t.id}><div><strong>{t.title}</strong><p className="muted small">{t.case_id} · Due {t.deadline}</p></div><ChevronRight size={16} /></Link>)}</Panel><Panel title="Recent audit activity">{!data.audit.length && <Empty>No recorded activity yet.</Empty>}{data.audit.map(a => <div className="list-row" key={a.id}><div><strong>{a.action}</strong><p className="muted small">{a.actor} · {a.record_id}<br />{new Date(a.at).toLocaleString("en-IN")}</p></div></div>)}</Panel></div>}</>;
}
function SettingsPanel({ user }: { user: User }) {
  const health = useResource<{ storage: string; status: string; ai: string; demo: boolean }>("/health");
  return <div className="two-col"><Panel title="Account & permissions"><dl className="details"><dt>Account</dt><dd>{user.name}</dd><dt>Role</dt><dd>{user.role}</dd><dt>Session</dt><dd>HttpOnly cookie · expires after 8 hours</dd><dt>Records</dt><dd>{user.role === "citizen" ? "Only your own sample cases and documents" : "Fictional registry, task, schedule and analysis access"}</dd></dl><Notice>Demo account selection is intentional public access—not identity verification. Do not expose this prototype to the internet with real data.</Notice></Panel><Panel title="Environment & privacy"><ErrorMessage error={health.error} />{health.loading ? <Loading /> : <dl className="details"><dt>Storage</dt><dd>{health.data?.storage} · explicit persistent demo mode</dd><dt>Status</dt><dd>{health.data?.status}</dd><dt>AI provider</dt><dd>{health.data?.ai}</dd><dt>Configuration</dt><dd>Managed through server environment variables. API keys are never sent to this page.</dd></dl>}<p>Only an explicitly configured live provider receives retrieved approved guidance and the question. Demo mode makes no model-provider requests. Uploaded files stay in private local storage.</p><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">Open local API documentation ↗</a></Panel></div>;
}