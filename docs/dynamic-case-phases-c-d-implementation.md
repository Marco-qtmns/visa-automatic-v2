# Dynamic Case Management — Phases C–D

Status: implemented in the working tree after the Phase B foundation.

## Phase C — document processing

The existing upload, quality, classification, matching, and completeness
services are now coordinated by one source-neutral pipeline:

`RECEIVED → BASIC_VALIDATION → QUALITY_ASSESSMENT → CLASSIFICATION → MATCHING → COMPLETENESS`

- Every run has a stable idempotency key, current stage, structured stage
  results, terminal status, timestamps, and safe failure summary.
- Repeating the same document/idempotency-key pair returns the original
  attempt. A retry creates a new attempt linked to the previous one.
- Basic validation records the content hash and size and detects duplicates
  already observed in the same Case. Stored-file access, MIME signature,
  decoding, quality findings, evaluator identity/version, evidence, and issue
  history remain auditable in the existing quality records.
- A document that fails quality never fulfills a Requirement. An unassigned
  but technically readable document may proceed only far enough to create a
  classification suggestion; matching still waits for employee-confirmed
  document type and owner.
- Automatic matching occurs only when confirmed metadata has exactly one
  compatible active Requirement. Ambiguous matches become employee work.
- Completeness remains derived from confirmed compatible matches with passed
  or manually accepted quality. Existing evaluations and fulfillment events
  are retained rather than overwritten.
- A processing or review problem creates a structured remediation issue with
  explanation, correction, customer instructions, language, and an editable
  notification draft. Open remediation is included in the Case-level Open
  Issues projection. The UI never sends this draft automatically.
- Failure of one document attempt is contained to that document and can be
  retried without modifying other documents.

The UI exposes processing, retry, attempt history, remediation-draft editing,
and explicit resolution directly on each document.

## Phase D — final review and generation

The authenticated API now enforces this sequence:

1. Resolve canonical and documentary blockers and enter `REVIEW`.
2. Explicitly approve the current canonical payload hash for generation.
3. Generate the form package through the existing
   `LegacyCanadaFormGeneratorAdapter` boundary.
4. Inspect the generated PDFs and explicitly approve or reject that exact run.
5. Transition to `READY` only when the current package is valid and its latest
   package-review decision is approved.

Generation and package decisions are immutable approval events. They record
the Case, canonical payload hash, optional PreparationRun, actor, reason, and
timestamp. Existing PreparationRun and PreparationArtifact records continue to
retain schema/policy/adapter/generator versions, template hashes, file hashes,
manifest identity, timing, and failure state.

If canonical data changes, the payload hash changes. The earlier generation
approval and package cease to qualify; the existing stale-package regression
and history behavior remain intact. No prior run or artifact is deleted.

## Schema and API

Migration `0001_consolidated_schema` adds:

- `document_processing_attempts`
- `document_remediation_issues`
- `preparation_approvals`

New document endpoints:

- `POST /documents/{document_id}/pipeline`
- `POST /documents/{document_id}/pipeline/{attempt_id}/retry`
- `GET /documents/{document_id}/pipeline`
- `GET /documents/{document_id}/remediation-issues`
- `PATCH /document-remediation-issues/{issue_id}`
- `POST /document-remediation-issues/{issue_id}/resolve`

New final-review endpoints:

- `POST /cases/{case_id}/preparation-generation-approval`
- `POST /preparation-runs/{run_id}/review`

## Boundaries

- The pipeline is synchronous behind a replaceable service boundary; it does
  not introduce a queue or external provider dependency.
- Upload transport continues to accept only PDF, JPEG, and PNG. Files accepted
  by that boundary are retained even when decoding or quality processing later
  fails.
- Remediation notifications are drafts only. Sending belongs to Phase E
  channel integrations.
- Form generation still uses the existing isolated legacy PDF adapter; no
  customer data or import source is read by the generation boundary.
