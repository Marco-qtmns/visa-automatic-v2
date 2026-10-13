# Database rebuild verification

Date: 2026-10-13
Result: **database baseline verified; Raspberry deployment not approved**

Machine-readable result: [`database-rebuild-verification.json`](database-rebuild-verification.json)
Machine-readable schema: [`schema-architecture.json`](schema-architecture.json)

## Starting state and source protection

- Starting branch: `codex/fix-fresh-db-migrations`
- Starting commit: `74b3cbf4f367a148872cf74191b111f8e69ff394`
- Actual working tree: 28 modified tracked files and 5 untracked source files.
- Phase-C/D checkpoint: local commit `cd2093e` (`checkpoint: preserve local
  dynamic case phases C and D`).
- The checkpoint was created only after a placeholder/secret review. No remote
  was changed and nothing was pushed.
- The separate legacy production repository was not inspected.

## Implemented changes

1. Replaced the mutable 18-revision chain with explicit immutable revision
   `0001_consolidated_schema`; archived old scripts outside Alembic discovery.
2. Added deterministic baseline and machine-readable schema generators.
3. Added same-Document retry/remediation ownership constraints, pipeline-stage
   validation, and remediation-resolution consistency.
4. Bound artifacts and package approvals to the correct Case, preparation run,
   and payload hash.
5. Added PostgreSQL 17 fresh-install, repeated-upgrade, catalog, CRUD, negative
   integrity, and Alembic-drift tests.
6. Updated runtime/deployment head checks and added the PostgreSQL CI gate.
7. Added a guarded, backup-by-default Raspberry staging rebuild script and
   runbook. The destructive command was not executed.

## Schema result

| Check | Result |
| --- | --- |
| Active Alembic heads | PASS: exactly `0001_consolidated_schema` |
| Application tables | PASS: 57 |
| ORM columns | 642 |
| Primary-key constraints | 57 |
| Foreign-key constraints/edges | 96 |
| Unique constraints | 43 |
| Check constraints | 66 |
| Explicit indexes | 74 |
| Baseline snapshot vs generator | PASS: byte-identical |
| Migrated schema vs ORM | PASS: `alembic check` found no differences |
| Repeated `upgrade head` | PASS |

PostgreSQL verification used native PostgreSQL 17.11 (Homebrew) and an isolated
disposable test database. The PostgreSQL tests
dropped and recreated only that test database's `public` schema. No staging or
production database was connected to or modified.

## Test evidence

| Verification | Runtime | Result |
| --- | --- | --- |
| Full backend/cross-cutting regression | Python 3.13.15 | 470 passed, 3 PostgreSQL-gated tests skipped, 0 failed |
| PostgreSQL baseline suite, run separately with test URL | PostgreSQL 17.11 / Python 3.13.15 | 3 passed, 0 failed |
| Final PostgreSQL baseline plus JSON-conformity rerun | PostgreSQL 17.11 / Python 3.13.15 | 4 passed, 0 failed |
| Final Phase-C/D and deployment focus | Python 3.13.15 | 52 passed, 0 failed |
| Frontend unit/component suite | local Node 26.10.0 | 64 passed, 0 failed |
| Next.js production build | local Node 26.10.0 | PASS; 8 routes generated |
| Rebuild shell syntax | Bash | PASS |
| Missing destructive confirmation | Bash | PASS: refused with exit code 2 |
| Docker Compose / image / proxy execution | n/a | NOT RUN: Docker executable unavailable locally |
| Raspberry Pi ARM64 execution | n/a | NOT RUN: no device operation authorized |

The frontend result verifies source behavior but does not replace the pending
Docker Node 22 and Raspberry ARM64 image/build checks.

## Remaining known defects and risks

- Legacy typed Canada CRUD paths in `backend/app/api/canada.py` and
  `backend/app/services/canada.py` can bypass the canonical decision boundary.
- `backend/app/services/preparation_runs.py` may regress a stale READY workflow
  state while reading package status; query/command separation remains debt.
- CSV and commercial-message candidates remain source-specific models.
- Business lifecycle stages remain a compatibility projection over the legacy
  workflow enum.
- Document processing is synchronous.
- Database administrator access can still mutate rows whose append-only
  behavior is enforced by services and role discipline rather than triggers.
- Docker Compose, container health, backup/restore, proxy routing, native ARM64
  imports, filesystem persistence, and SSD behavior remain unverified on the
  target platform.

These items do not require another canonical aggregate or an additional table
to make a fresh database correct. They remain follow-up service/deployment work.

## Deployment decision

The consolidated schema is accepted as the fresh-install database baseline for
development and CI. The application is **not approved for production** and D1
Raspberry staging is **not accepted** until its hardware, Docker, persistence,
backup, and separate-restore checks pass.

The following operation still requires separate explicit user approval and must
run only on the Raspberry checkout after preflight:

```bash
export DEPLOY_ROOT='<absolute-deployment-checkout>'
export STAGING_DB='<database-name-ending-in-_staging>'
cd "$DEPLOY_ROOT"
./deployment/reinitialize-staging-db.sh \
  --env-file .env.production \
  --expected-database "$STAGING_DB" \
  --confirm-destroy "$STAGING_DB"
```

That command destroys all rows in the explicitly confirmed staging database. It does not delete
the PostgreSQL volume or document/intake/generated-artifact storage. Follow it
with the exact verification and administrator-bootstrap sequence in
[`raspberry-database-rebuild.md`](raspberry-database-rebuild.md). No push,
merge, staging reset, or storage cleanup is authorized by this report.
