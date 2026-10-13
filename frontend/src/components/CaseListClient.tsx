"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api, loadCaseSummaries, type CaseSummary } from "@/lib/api";
import { useBootstrapCases } from "./AuthShell";
import { StatusBadge } from "./StatusBadge";
import { useCurrentUser } from "./AuthShell";

export function CaseListClient() {
  const bootstrapCases = useBootstrapCases();
  const currentUser = useCurrentUser();
  const [items, setItems] = useState<CaseSummary[] | null>(bootstrapCases);
  const [view, setView] = useState<"active" | "archived">("active");
  const [error, setError] = useState("");

  async function load(nextView = view) {
    setError("");
    try {
      setItems(await loadCaseSummaries(nextView));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Cases could not be loaded.");
    }
  }

  useEffect(() => { if (bootstrapCases === null) void load(); }, [bootstrapCases]);
  async function lifecycle(item: CaseSummary, action: "archive" | "restore" | "delete") {
    if (action === "delete" && window.prompt("Type DELETE to permanently remove this application from active use. Data is retained under the retention policy.") !== "DELETE") return;
    setError("");
    try {
      if (action === "archive") await api.archiveCase(item.id);
      else if (action === "restore") await api.restoreCase(item.id);
      else await api.deleteCase(item.id);
      await load(); window.dispatchEvent(new Event("visa-bootstrap-refresh"));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Application lifecycle action failed."); }
  }
  if (error) return <div className="error-panel" role="alert">{error} <button className="button button-small" onClick={() => void load()}>Retry</button></div>;
  if (items === null) return <div className="state-panel">Loading cases…</div>;
  const filters = <div className="button-row" aria-label="Application record filter"><button className={view === "active" ? "button" : "button button-secondary"} onClick={() => { setView("active"); void load("active"); }}>Active</button><button className={view === "archived" ? "button" : "button button-secondary"} onClick={() => { setView("archived"); void load("archived"); }}>Archived</button></div>;
  if (!items.length) return <div className="detail-stack">{filters}<div className="state-panel"><div><h2>No {view} applications</h2>{view === "active" && <><p>Start with a source or create an empty application.</p><Link className="button" href="/cases/new">New application</Link></>}</div></div></div>;

  const queues: CaseSummary["queue"][] = ["ACTION_REQUIRED", "REVIEW", "READY", "WAITING"];
  return <div className="case-queues">{filters}
    {queues.map(queue => {
      const group = items.filter(item => item.queue === queue);
      if (!group.length) return null;
      return <section key={queue} className="section-card"><div className="section-heading"><h2>{queue.replaceAll("_", " / ")}</h2><span className="badge">{group.length}</span></div><div className="table-wrap">
      <table>
        <thead><tr><th>Applicant</th><th>Case</th><th>Workflow stage</th><th>Queue issues</th><th>Next action</th><th>Last updated</th><th>Actions</th></tr></thead>
        <tbody>
          {group.map((item) => (
            <tr key={item.id}>
              <td><Link className="case-link" href={`/cases/${item.id}`}>{item.display_name}</Link></td>
              <td>{item.case_number}<br /><span className="muted">{item.visa_type}</span></td>
              <td><StatusBadge value={item.workflow_state} /></td>
              <td>{item.issue_count}</td>
              <td>{item.next_action}</td>
              <td>{new Date(item.updated_at).toLocaleString()}</td>
              <td><div className="button-row">{view === "active" ? <button className="button button-secondary button-small" onClick={() => void lifecycle(item, "archive")}>Archive</button> : <><button className="button button-secondary button-small" onClick={() => void lifecycle(item, "restore")}>Restore</button>{currentUser?.role === "ADMIN" && <button className="button button-danger button-small" onClick={() => void lifecycle(item, "delete")}>Delete</button>}</>}</div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div></section>;
    })}
  </div>;
}
