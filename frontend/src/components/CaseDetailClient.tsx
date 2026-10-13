"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, loadCaseDetail, type CaseDetailBundle, type WorkflowState } from "@/lib/api";
import { DocumentsSection, FactsSection, PeopleSection, RequirementsSection, TasksSection } from "./CaseSections";
import { NextActionCard } from "./NextActionCard";
import { StatusBadge } from "./StatusBadge";
import { WorkflowStepper } from "./WorkflowStepper";
import { CommunicationsSection } from "./CommunicationsSection";
import { CanadaApplicationSection } from "./CanadaApplicationSection";
import { CanonicalIntakeSection } from "./CanonicalIntakeSection";
import { PreparationSection } from "./PreparationReadinessSection";
import { useCurrentUser } from "./AuthShell";
import { CaseAuditSection } from "./CaseAuditSection";

const actor = process.env.NEXT_PUBLIC_WORKFLOW_ACTOR ?? "manual-ui";
export function workflowActionLabel(current: WorkflowState, target: WorkflowState): string {
  if (current === "PREPARE" && target === "REVIEW") return "Send for review";
  if (current === "REVIEW" && target === "PREPARE") return "Return to preparation";
  if (current === "REVIEW" && target === "READY") return "Approve application";
  if (current === "READY" && target === "SUBMITTED") return "Mark submitted";
  if (target === "DOCUMENTS") return "Continue application";
  return `Continue to ${target}`;
}

function businessLabel(value: string): string {
  const text = value.split(".").at(-1)?.replaceAll("_", " ") ?? value;
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function issueTarget(category: string, fieldPath: string | null): string | null {
  if (fieldPath) {
    const normalized = fieldPath.startsWith("facts.") ? fieldPath.slice("facts.".length) : fieldPath;
    const directlyEditable = new Set([
      "case.visa_type", "applicant.given_names", "applicant.family_name",
      "applicant.biography.date_of_birth", "applicant.biography.other_names",
      "applicant.biography.sex", "applicant.biography.birth_city",
      "applicant.biography.birth_state_province", "applicant.biography.birth_country_code",
      "applicant.biography.marital_status", "applicant.citizenship.primary",
      "applicant.current_residence.country_code", "applicant.passport.number",
      "applicant.passport.issuing_country_code", "applicant.passport.issue_date",
      "applicant.passport.expiry_date", "application.mailing_same_as_residential",
      "application.official_application_date", "trip.purpose", "trip.imm5257_purpose_code",
      "trip.arrival_date", "trip.departure_date", "trip.available_funds_amount",
      "trip.available_funds_currency", "trip.funds_source_reference", "contact.email",
      "contact.phone", "sponsor.exists", "sponsor.person_id", "host.exists", "host.person_id",
      "trip.payer",
    ]);
    if (directlyEditable.has(normalized) || normalized.startsWith("applicant.residential_address.")) {
      return `#canonical-${normalized.replaceAll(".", "-")}`;
    }
    if (fieldPath.startsWith("requirements.") || fieldPath === "documents") return "#documents";
    if (fieldPath.startsWith("fact_candidates.")) return "#communications";
  }
  if (category === "evidence") return "#communications";
  if (category === "task") return "#tasks";
  if (category === "document") return "#documents";
  return category === "canonical" || category === "decision" ? "#canonical-intake" : null;
}

export function visibleWorkflowTargets(
  currentState: WorkflowState,
  targets: WorkflowState[],
  role?: string,
): WorkflowState[] {
  if (role !== "CASE_WORKER") return targets;
  if (currentState === "READY") return [];
  if (currentState === "REVIEW") return targets.filter(target => target === "PREPARE");
  return targets.filter(target => !["READY", "SUBMITTED"].includes(target));
}

export function CaseDetailClient({ caseId }: { caseId: string }) {
  const currentUser = useCurrentUser();
  const [data, setData] = useState<CaseDetailBundle | null>(null);
  const [error, setError] = useState(""); const [workflowError, setWorkflowError] = useState(""); const [busy, setBusy] = useState(false);
  const load = useCallback(async () => { setError(""); try { setData(await loadCaseDetail(caseId)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Case could not be loaded."); } }, [caseId]);
  useEffect(() => { void load(); }, [load]);
  if (error) return <div className="error-panel" role="alert">{error} <button className="button button-small" onClick={() => void load()}>Retry</button></div>;
  if (!data) return <div className="state-panel">Loading case…</div>;

  async function transition(target: WorkflowState, event: FormEvent<HTMLFormElement>) { event.preventDefault(); setBusy(true); setWorkflowError(""); const values = new FormData(event.currentTarget); try { await api.transition(caseId, target, actor, String(values.get("reason") || "") || undefined); await load(); } catch (reason) { setWorkflowError(reason instanceof Error ? reason.message : "Transition was rejected."); } finally { setBusy(false); } }
  const refresh = async () => {
    await load();
    window.dispatchEvent(new Event("visa-bootstrap-refresh"));
  };
  const applicant = data.people.find(person => person.roles.includes("applicant"));
  const allowedTargets = visibleWorkflowTargets(data.workflow.current_state, data.workflow.allowed_targets, currentUser?.role);
  const readiness = data.preparation.readiness;
  const issues = data.dynamicStatus.issues;
  const blockingCount = issues.filter(item => item.severity === "blocking").length;

  return <div className="detail-stack">
    <div className="page-heading"><div><p className="eyebrow">{data.case.case_number}</p><h1>{applicant ? `${applicant.first_name} ${applicant.last_name}` : "Applicant not identified yet"}</h1><p className="subtitle">Lifecycle: {data.dynamicStatus.lifecycle_stage} · {blockingCount} blocking · {issues.length - blockingCount} warnings</p></div><Link className="button button-secondary" href="/cases">Back to applications</Link></div>
    <nav className="anchor-nav" aria-label="Application workspace">{["needs-attention", "information-sources", "application-summary", "requirements", "documents", "primary-action", ...(currentUser?.role === "ADMIN" ? ["advanced"] : [])].map(section => <a href={`#${section}`} key={section}>{section.replaceAll("-", " ")}</a>)}</nav>
    <NextActionCard action={data.nextAction} />
    <details className="section-card attention-panel" id="needs-attention"><summary className="section-heading"><div><h2>Needs attention</h2><span className="muted">{issues.length} total · {blockingCount} blocking</span></div><StatusBadge value={blockingCount ? `${blockingCount} blocking` : "No blockers"} /></summary>
      {!issues.length ? <div className="empty-state">No operational exceptions require attention.</div> : <div className="record-list compact-records">
        {issues.map(item => { const href = issueTarget(item.category, item.field_path); const content = <><span><strong>{item.title}</strong></span><span>{item.message} {item.action} Source: {businessLabel(item.source_type)}.</span><StatusBadge value={item.severity} /></>; return href ? <a className="record attention-record" href={href} key={item.issue_key} onClick={() => setTimeout(() => { const target = document.querySelector<HTMLElement>(href); target?.closest("details")?.setAttribute("open", ""); target?.focus(); }, 0)}>{content}</a> : <div className="record attention-record" key={item.issue_key}>{content}</div>; })}
      </div>}
    </details>
    <section className="section-card" id="information-sources"><div className="section-heading"><h2>Information sources</h2></div><div className="summary-grid">
      <a className="summary-item" href="#canada-import"><strong>Google Forms / CSV</strong><span>Import and review exceptions</span></a>
      <a className="summary-item" href="#communications"><strong>Commercial messages</strong><span>{data.conversations.length} conversations, including WhatsApp</span></a>
      <a className="summary-item" href="#documents"><strong>Documents</strong><span>{data.documents.length} received</span></a>
    </div></section>
    <section className="section-card" id="application-summary"><div className="section-heading"><h2>Application summary</h2></div><div className="summary-grid">{data.dynamicStatus.dimensions.map(dimension => <div className="summary-item" key={dimension.key}><strong>{businessLabel(dimension.key)}</strong><StatusBadge value={dimension.ready ? "COMPLETE" : "NEEDS ATTENTION"} /><span>{dimension.blocking_count} blocking · {dimension.warning_count} warnings</span></div>)}</div></section>
    <section className="section-card" id="overview"><div className="section-heading"><h2>Overview</h2></div>
      <div className="summary-grid"><div className="summary-item"><strong>{data.case.case_number}</strong><span>Case number</span></div><div className="summary-item"><strong>{data.people.length}</strong><span>People</span></div><div className="summary-item"><strong>{data.facts.length}</strong><span>Facts</span></div><div className="summary-item"><strong>{data.requirements.filter(item => item.active).length}</strong><span>Active requirements</span></div><div className="summary-item"><strong>{data.documents.length}</strong><span>Documents</span></div><div className="summary-item"><strong>{data.tasks.filter(task => task.status === "open" || task.status === "in_progress").length}</strong><span>Open tasks</span></div><div className="summary-item"><strong>{new Date(data.case.created_at).toLocaleDateString()}</strong><span>Created</span></div><div className="summary-item"><strong>{new Date(data.case.updated_at).toLocaleDateString()}</strong><span>Updated</span></div></div>
    </section>
    <CanonicalIntakeSection caseId={caseId} status={data.dynamicStatus} revisions={data.canonicalRevisions} people={data.people} onChanged={refresh} />
    <CanadaApplicationSection caseId={caseId} people={data.people} value={data.canadaApplication} onChanged={refresh} />
    <CommunicationsSection caseId={caseId} conversations={data.conversations} messages={data.conversationMessages} runs={data.factExtractionRuns} candidates={data.factCandidates} facts={data.facts} onChanged={refresh} />
    <section className="section-card" id="document-status"><div className="section-heading"><h2>Document status</h2><span className="muted">Received files, requirement match, and quality</span></div><div className="record-list">
      {data.requirements.filter(item => item.active).map(requirement => { const matches = data.documentMatches.filter(match => match.requirement_id === requirement.id); const documents = matches.map(match => data.documents.find(document => document.id === match.document_id)).filter(item => item !== undefined); return <div className="record" key={requirement.id}><strong>{businessLabel(requirement.owner_role)} — {businessLabel(requirement.document_type)}</strong><span>{requirement.fulfillment_status === "fulfilled" ? "Received" : "Missing"} · {documents.length ? documents.map(document => `${document.original_filename} · ${businessLabel(document.quality_status)}`).join(", ") : "No matching document"}{requirement.is_blocking && requirement.fulfillment_status === "pending" ? " · Action required" : ""}</span></div>; })}
      {!data.requirements.some(item => item.active) ? <div className="empty-state">No active document requirements.</div> : null}
    </div></section>
    <DocumentsSection caseId={caseId} items={data.documents} people={data.people} requirements={data.requirements} documentTypes={data.documentTypes} matches={data.documentMatches} classifications={data.documentClassifications} qualityChecks={data.documentQualityChecks} onChanged={refresh} />
    <PreparationSection caseId={caseId} workflowState={data.case.workflow_state} value={data.preparation} history={data.preparationRuns} onChanged={refresh} />
    <div className="detail-grid"><PeopleSection caseId={caseId} items={data.people} onChanged={refresh} /><FactsSection caseId={caseId} items={data.facts} people={data.people} onChanged={refresh} /></div>
    <TasksSection caseId={caseId} items={data.tasks} requirements={data.requirements} documents={data.documents} onChanged={refresh} />
    <RequirementsSection caseId={caseId} items={data.requirements} people={data.people} documents={data.documents} matches={data.documentMatches} completenessEvaluations={data.requirementCompletenessEvaluations} onChanged={refresh} />
    <section className="section-card" id="primary-action"><div className="section-heading"><h2>Primary action</h2><StatusBadge value={data.workflow.current_state} /></div>{!allowedTargets.length ? <EmptyWorkflow /> : <div className="transition-forms">{allowedTargets.map(target => <form className="transition-form" key={target} onSubmit={event => void transition(target, event)}><strong>{workflowActionLabel(data.workflow.current_state, target)}</strong><input name="reason" aria-label={`Reason for ${target}`} placeholder="Reason (optional)" /><button className="button" disabled={busy}>{workflowActionLabel(data.workflow.current_state, target)}</button></form>)}</div>}{workflowError && <div className="form-error" role="alert">{workflowError}</div>}</section>
    {currentUser?.role === "ADMIN" && <details className="section-card" id="advanced"><summary><strong>Advanced / Diagnostics</strong></summary><p className="muted">Raw facts, canonical data, tasks, workflow history, provenance, and audit tools.</p>
    <section className="section-card" id="workflow"><div className="section-heading"><div><h2>Compatibility workflow</h2><span className="muted">Legacy transitions remain available while the case lifecycle is projected as {data.dynamicStatus.lifecycle_stage}. Actor: {actor}</span></div><StatusBadge value={data.workflow.current_state} /></div><WorkflowStepper current={data.workflow.current_state} />
      <h3 className="history-title">Transition history</h3>{!data.workflow.history.length ? <div className="empty-state">No transitions recorded.</div> : <div>{data.workflow.history.map(entry => <div className="transition-entry" key={entry.id}><div><strong>{new Date(entry.created_at).toLocaleString()}</strong><div className="muted">{entry.actor || "Unknown actor"}</div></div><div><div className="transition-arrow">{entry.from_state} → {entry.to_state}</div>{entry.reason && <p>{entry.reason}</p>}</div></div>)}</div>}
    </section>
    </details>}
    {currentUser && ["REVIEWER", "ADMIN"].includes(currentUser.role) ? <CaseAuditSection caseId={caseId} /> : null}
  </div>;
}

function EmptyWorkflow() { return <div className="empty-state">No transition is currently available.</div>; }
