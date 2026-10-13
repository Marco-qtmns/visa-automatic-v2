# Visa Automatic V2 – workflow, UX and data-integrity delivery

Date: 2026-10-13  
Branch: `codex/workflow-ux-data-integrity`  
Base: fetched `origin/main` at `74b3cbf` before the feature branch was created  
Data policy: synthetic fixtures only; no customer CSV, upload, secret, PDF or production environment file was added

## Delivered corrections

- Added audited, permission-enforced Archive/Restore and retention-safe soft Delete for Cases and Intake Submissions. Active and archived queues are separate; delete is administrator-only and retains dependent people, documents, attempts, raw-source references and audit rows.
- Added migration `0002_record_lifecycle` for lifecycle metadata and the nullable `PersonBiography.has_other_citizenship` gate. Deployment head checks and the machine-readable schema export now point to the new head.
- Replaced the Canonical Information description with the requested employee-facing text.
- Added normal case-worker inputs and typed canonical writes for required biography, country, current residence, primary passport, structured residential address, mailing choice, official application date, reviewed trip dates/purpose and available-funds values. Only changed controls are submitted; every write uses the existing immutable revision ledger and readiness is recalculated.
- Kept Host as Unknown/No/Yes and separately editable from Financial Sponsor. Host existence and identity changes remain revisioned and preserve source/reference metadata.
- Kept the backend recommendation card in the required semantic order and added a DOM-order regression test.
- Changed Needs Attention to an accessible, collapsed summary with total/blocking counts, compact rows and exact field destinations where a safe input exists. Non-actionable diagnostics no longer masquerade as links.
- Reworked CSV review state: Needs attention is the default; same-run refreshes preserve section/filter/drafts; changing runs resets navigation; All/Needs attention/Confirmed filters, status counts, progress and responsive 3/2/1-column cards were added.
- Added semantic Portuguese/English boolean normalization for Other Citizenship. `Não`/`No` persists `false`; `Sim`/`Yes` persists `true`; missing remains null; country records remain separate.
- Fixed the Save Confirmed Data rollback by reusing the existing primary funding row when payer and payer details are applied in one atomic transaction. Candidate-specific sanitized employee errors and administrator diagnostics remain separated.
- Standardized family relationship labels and separated names from relationships while retaining relationship IDs as record keys, including identical-name safety.
- Restricted the Advanced Canonical Application Editor and administrative diagnostics to administrators in both rendering and endpoint permissions. Case workers retain simplified canonical, activity and official-answer workflows; reviewer audit access remains unchanged.
- Humanized document requirement identifiers and split document identity from fulfillment/quality status.
- Added an official-field coverage matrix at `docs/canada-official-field-coverage.md`.

## Main modified areas

- Backend models/schemas/migration: `backend/app/models/{core,intake,canada}.py`, `backend/app/schemas/{core,intake,operational,canada}.py`, `backend/migrations/versions/0002_record_lifecycle_and_citizenship_gate.py`
- Backend services/API/security: `record_lifecycle.py`, `dynamic_cases.py`, `canada_imports.py`, `intake.py`, `core.py`, `operational.py`, the core/intake/operational APIs and `authorization.py`
- Frontend: case/intake queues, canonical intake, Canada import/application, Needs Attention, preparation navigation, document status, API types/client and responsive styles
- Operational contracts: deployment expected-head checks and `docs/database/schema-architecture.json`
- Tests: lifecycle, imports, canonical decisions/readiness, authorization, queue projections and frontend components

## Verification

| Check | Result |
| --- | --- |
| Full backend suite | 488 passed, 3 skipped, 0 failed (54.65 s) |
| Frontend component/unit suite | 70 passed across 15 files, 0 failed |
| TypeScript | `npx tsc --noEmit` passed |
| Production frontend build | `next build` passed; all routes compiled |
| Fresh SQLite migration | Upgraded `base -> 0001 -> 0002`; current head `0002_record_lifecycle` |
| Alembic metadata check | `No new upgrade operations detected` |
| PostgreSQL baseline | 3 tests skipped because `POSTGRES_TEST_DATABASE_URL` was not configured |
| Lint | No lint script or ESLint dependency is configured in `frontend/package.json`; no lint command was available |

The test warnings are existing Python/Starlette deprecation warnings (`SwigPy*` module metadata and TestClient/httpx transition); they do not indicate failed behavior.

## UX evidence

Automated component tests verify the after-state: collapsed Needs Attention with counts, precise blocker hrefs, case-worker exclusion from advanced editors, distinct family labels, document-readable labels, CSV Passport-section preservation after confirmation, immediate movement from Needs attention to Confirmed and next-action DOM order. The prior browser observations remain documented in `docs/visa-automatic-v2-browser-test-2026-10-13.md`. A live post-change deployment retest was not performed because this local branch has not been pushed or deployed.

## Integrity and authorization confirmation

Existing import provenance is retained in import candidates and field-provenance reviews. Manual edits continue to append canonical revisions rather than replacing history. Lifecycle operations append application audit events and never cascade-delete sensitive dependencies. Apply remains atomic: injected persistence failures roll back typed writes while confirmed review decisions remain available for a safe retry. New lifecycle and advanced-editor permissions are enforced by the route authorization graph, and lifecycle services repeat the permission check.

## Remaining boundaries

- Collection repair involving ambiguous multi-person education, family, representative profiles or official explanations remains administrator-only. Case workers can resolve ordinary scalar blockers, reviewed imports, applicant activities and official answers without administrator access.
- The three PostgreSQL-only baseline checks require a disposable `*_test` database and were therefore skipped locally.
- No pull request was opened: repository instructions prohibit automatic push, and a remote PR cannot be created until this local feature branch is pushed by an authorized human workflow.
