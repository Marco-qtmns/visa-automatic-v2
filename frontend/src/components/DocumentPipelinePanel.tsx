"use client";

import { useEffect, useState, type FormEvent } from "react";
import {
  api,
  type DocumentProcessingAttempt,
  type DocumentRemediationIssue,
} from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

const reviewer = process.env.NEXT_PUBLIC_WORKFLOW_ACTOR ?? "manual-ui";

function requestKey(documentId: string): string {
  return `${documentId}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function DocumentPipelinePanel({ documentId }: { documentId: string }) {
  const [attempts, setAttempts] = useState<DocumentProcessingAttempt[]>([]);
  const [issues, setIssues] = useState<DocumentRemediationIssue[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    const [nextAttempts, nextIssues] = await Promise.all([
      api.listDocumentPipelineAttempts(documentId),
      api.listDocumentRemediationIssues(documentId),
    ]);
    setAttempts(nextAttempts);
    setIssues(nextIssues);
  }

  useEffect(() => {
    void refresh().catch(reason => setError(
      reason instanceof Error ? reason.message : "Document processing history could not be loaded.",
    ));
  }, [documentId]);

  async function run(retry?: DocumentProcessingAttempt) {
    setBusy(true); setError("");
    try {
      if (retry) {
        await api.retryDocumentPipeline(documentId, retry.id, requestKey(documentId));
      } else {
        await api.runDocumentPipeline(documentId, requestKey(documentId));
      }
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Document processing failed.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft(event: FormEvent<HTMLFormElement>, issueId: string) {
    event.preventDefault(); setError("");
    const draft = String(new FormData(event.currentTarget).get("notification_draft") ?? "").trim();
    try { await api.updateDocumentRemediationIssue(issueId, draft); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Draft could not be saved."); }
  }

  async function resolve(issueId: string) {
    setError("");
    try { await api.resolveDocumentRemediationIssue(issueId, reviewer); await refresh(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Issue could not be resolved."); }
  }

  const latest = attempts[0];
  const openIssues = issues.filter(issue => issue.status === "open");
  return <details className="pipeline-panel">
    <summary>Processing pipeline{latest ? ` · ${latest.stage}` : ""}</summary>
    <p className="muted">Validation → quality → classification → matching → completeness. Customer messages remain drafts and are never sent automatically.</p>
    <div className="button-row">
      <button className="button button-secondary button-small" disabled={busy} onClick={() => void run()}>
        {busy ? "Processing…" : latest ? "Run new attempt" : "Process document"}
      </button>
      {latest && ["failed", "needs_review"].includes(latest.status) && <button className="button button-secondary button-small" disabled={busy} onClick={() => void run(latest)}>Retry</button>}
    </div>
    {error && <div className="form-error" role="alert">{error}</div>}
    {latest && <div className="summary-item"><strong>Latest attempt</strong><div className="record-meta"><StatusBadge value={latest.status} /><StatusBadge value={latest.stage} /></div>{latest.error_summary && <p>{latest.error_summary}</p>}<p className="muted">{new Date(latest.created_at).toLocaleString()}</p></div>}
    {openIssues.map(issue => <form className="form-grid" key={issue.id} onSubmit={event => void saveDraft(event, issue.id)}>
      <div className="field field-full"><strong>{issue.problem_type.replaceAll("_", " ")}</strong><p>{issue.explanation}</p><p className="muted">Correction: {issue.correction}</p></div>
      <div className="field field-full"><label>Customer notification draft</label><textarea name="notification_draft" defaultValue={issue.notification_draft} /><span className="muted">Editable draft only. No notification is sent from this screen.</span></div>
      <div className="button-row field-full"><button className="button button-secondary button-small">Save draft</button><button type="button" className="button button-small" onClick={() => void resolve(issue.id)}>Mark resolved</button></div>
    </form>)}
    {attempts.length > 1 && <details><summary>Attempt history ({attempts.length})</summary><ul>{attempts.map(attempt => <li key={attempt.id}>{new Date(attempt.created_at).toLocaleString()} — {attempt.status} at {attempt.stage}</li>)}</ul></details>}
  </details>;
}
