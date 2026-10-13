"use client";

import Link from "next/link";
import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import { api, type CaseSummary, type IntakeMetrics, type IntakeSubmission } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";
import { useCurrentUser } from "./AuthShell";


export function IntakeQueueClient() {
  const currentUser = useCurrentUser();
  const [items, setItems] = useState<IntakeSubmission[]>([]);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [metrics, setMetrics] = useState<IntakeMetrics | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [caseChoices, setCaseChoices] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [view, setView] = useState<"active" | "archived">("active");

  async function load(nextView = view) {
    const [submissions, counters, bootstrap] = await Promise.all([
      api.listIntakeSubmissions(nextView), api.intakeMetrics(), api.bootstrap(),
    ]);
    setItems(submissions); setMetrics(counters); setCases(bootstrap.case_summary);
  }

  useEffect(() => { load().catch(reason => setError(reason instanceof Error ? reason.message : "Intake queue could not be loaded.")); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) { setError("Choose a Google Forms CSV file."); return; }
    const values = new FormData(event.currentTarget);
    setBusy("upload"); setError(""); setMessage("");
    try {
      const result = await api.uploadGoogleFormsIntake(
        file,
        String(values.get("source_external_id") || "").trim() || undefined,
        String(values.get("case_id") || "") || undefined,
      );
      setMessage(result.processing_status === "PROCESSED"
        ? "Submission processed automatically."
        : result.processing_status === "NEEDS_REVIEW"
          ? "Submission processed and added to the review queue."
          : result.failure_message ?? "Submission received.");
      setFile(null); await load(); window.dispatchEvent(new Event("visa-bootstrap-refresh"));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Submission could not be received."); }
    finally { setBusy(""); }
  }

  async function retry(item: IntakeSubmission) {
    setBusy(item.id); setError(""); setMessage("");
    try {
      const result = await api.retryIntakeSubmission(item.id, caseChoices[item.id] || undefined);
      setMessage(result.processing_status === "PROCESSED" ? "Retry completed." : result.failure_message ?? "Retry completed with review items.");
      await load(); window.dispatchEvent(new Event("visa-bootstrap-refresh"));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Retry failed."); }
    finally { setBusy(""); }
  }

  async function lifecycle(item: IntakeSubmission, action: "archive" | "restore" | "delete") {
    if (action === "delete" && window.prompt("Type DELETE to remove this intake from active use. Its source and audit history remain retained.") !== "DELETE") return;
    setBusy(item.id); setError(""); setMessage("");
    try {
      if (action === "archive") await api.archiveIntakeSubmission(item.id);
      else if (action === "restore") await api.restoreIntakeSubmission(item.id);
      else await api.deleteIntakeSubmission(item.id);
      setMessage(action === "archive" ? "Intake archived." : action === "restore" ? "Intake restored." : "Intake deleted under the retention policy.");
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Intake lifecycle action failed."); }
    finally { setBusy(""); }
  }

  function chooseFile(event: ChangeEvent<HTMLInputElement>) { setFile(event.target.files?.[0] ?? null); }

  return <div className="detail-stack">
    <section className="section-card"><div className="section-heading"><div><h2>Receive Google Forms CSV</h2><span className="muted">The source is preserved, deduplicated, mapped and safely applied automatically.</span></div></div>
      {message && <div className="success-message" role="status">{message}</div>}{error && <div className="form-error" role="alert">{error}</div>}
      <form className="form-grid" onSubmit={upload}>
        <div className="field"><label htmlFor="intake-file">CSV source</label><input id="intake-file" type="file" accept=".csv,text/csv" onChange={chooseFile} /></div>
        <div className="field"><label htmlFor="intake-external-id">Google submission ID (optional)</label><input id="intake-external-id" name="source_external_id" /></div>
        <div className="field field-full"><label htmlFor="intake-case">Existing application (optional)</label><select id="intake-case" name="case_id" defaultValue=""><option value="">Create or resolve automatically</option>{cases.map(item => <option key={item.id} value={item.id}>{item.display_name} · {item.case_number}</option>)}</select></div>
        <div className="button-row field-full"><button className="button" disabled={busy === "upload"}>{busy === "upload" ? "Processing…" : "Receive and process"}</button></div>
      </form>
    </section>
    {metrics && <section className="summary-grid" aria-label="Intake counters">{[
      ["Received", metrics.submissions_received], ["Processed", metrics.successfully_processed],
      ["Duplicates ignored", metrics.duplicates_ignored], ["New applications", metrics.new_cases_created],
      ["Matched applications", metrics.existing_cases_matched], ["Need review", metrics.review_required],
      ["Failed", metrics.failed],
    ].map(([label, value]) => <div className="summary-item" key={label}><strong>{value}</strong><span>{label}</span></div>)}</section>}
    <section className="section-card"><div className="section-heading"><div><h2>Intake queue</h2><span className="muted">Failed and review-required submissions appear first.</span></div><span className="badge">{items.length}</span></div>
      <div className="button-row" aria-label="Intake record filter"><button className={view === "active" ? "button" : "button button-secondary"} onClick={() => { setView("active"); void load("active"); }}>Active</button><button className={view === "archived" ? "button" : "button button-secondary"} onClick={() => { setView("archived"); void load("archived"); }}>Archived</button></div>
      {!items.length ? <div className="empty-state">No intake submissions received.</div> : <div className="record-list">{items.map(item => <article className="record" key={item.id}>
        <div className="record-head"><div><h3>{item.applicant_display_name ?? "Applicant not identified yet"}</h3><div className="record-meta"><StatusBadge value={item.processing_status} /><span className="badge">{item.issue_count} issues</span></div></div><span className="muted">{new Date(item.received_at).toLocaleString()}</span></div>
        <p><strong>Source:</strong> Google Forms CSV{item.source_filename ? ` · ${item.source_filename}` : ""}<br /><strong>Application:</strong> {item.case_number ?? "Not linked"}</p>
        {item.failure_message && <div className="form-error" role="alert"><strong>{item.failure_detail_json?.section ?? "Intake"}{item.failure_detail_json?.field_path ? ` · ${item.failure_detail_json.field_path}` : ""}</strong><p>{item.failure_message}</p>{item.failure_detail_json?.suggested_correction && <p>{item.failure_detail_json.suggested_correction}</p>}</div>}
        <div className="button-row">{item.case_id && <Link className="button button-secondary button-small" href={`/cases/${item.case_id}`}>Open application</Link>}
          {view === "active" && item.can_retry && <>{item.processing_status !== "PROCESSED" && <select aria-label={`Application for ${item.source_filename ?? item.id}`} value={caseChoices[item.id] ?? ""} onChange={event => setCaseChoices(current => ({ ...current, [item.id]: event.target.value }))}><option value="">Retry current resolution</option>{cases.map(candidate => <option key={candidate.id} value={candidate.id}>{candidate.display_name} · {candidate.case_number}</option>)}</select>}<button className="button button-small" disabled={busy === item.id} onClick={() => void retry(item)}>{busy === item.id ? "Retrying…" : item.processing_status === "PROCESSED" ? "Reprocess" : "Retry"}</button></>}
          {view === "active" ? <button className="button button-secondary button-small" disabled={busy === item.id} onClick={() => void lifecycle(item, "archive")}>Archive</button> : <><button className="button button-secondary button-small" disabled={busy === item.id} onClick={() => void lifecycle(item, "restore")}>Restore</button>{currentUser?.role === "ADMIN" && <button className="button button-danger button-small" disabled={busy === item.id} onClick={() => void lifecycle(item, "delete")}>Delete</button>}</>}
        </div>
      </article>)}</div>}
    </section>
  </div>;
}
