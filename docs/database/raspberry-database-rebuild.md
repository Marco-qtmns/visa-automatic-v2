# Raspberry staging database rebuild

Status: prepared and locally guard-tested; **not executed on the Raspberry Pi**.

This procedure replaces only the explicitly named disposable staging database
so it can start from the consolidated `0001_consolidated_schema` Alembic
baseline. It does not remove the PostgreSQL volume, repository, Git history,
environment file, document storage, intake storage, or generated artifacts.

## Required approval

Execution destroys every Case, user, session, audit row, import record,
document metadata row, requirement, and preparation record in the staging
database. Run it only after the user separately approves the actual Raspberry
operation.

No approval has been given merely by adding this runbook or script.

## Prerequisites

1. Repository checkout is available as `$DEPLOY_ROOT` and contains the reviewed
   consolidated baseline.
2. `.env.production` exists with mode `0600` and resolves
   a `POSTGRES_DB` identifier ending in `_staging`.
3. Current code has passed the PostgreSQL baseline gate and application tests.
4. Docker Compose and the daemon are available.
5. The operator has sufficient free space for a backup.
6. No real customer data is present. If that statement is uncertain, stop.

## Preflight

```bash
export DEPLOY_ROOT='<absolute-deployment-checkout>'
export STAGING_DB='<database-name-ending-in-_staging>'
export STAGING_DB_USER='<database-owner>'
cd "$DEPLOY_ROOT"
git status --short --branch
./deployment/raspberry-preflight.sh \
  --env-file .env.production \
  --report deployment/reports/pre-rebuild.json
```

Record the commit and image IDs. Do not use `docker compose down -v`, delete
`DATA_ROOT`, or manually edit `alembic_version`.

## Command requiring explicit approval

After separate approval, run:

```bash
cd "$DEPLOY_ROOT"
./deployment/reinitialize-staging-db.sh \
  --env-file .env.production \
  --expected-database "$STAGING_DB" \
  --confirm-destroy "$STAGING_DB"
```

The script:

1. requires the exact destructive confirmation argument;
2. reads the resolved Compose configuration without printing it;
3. requires a safe expected database identifier ending in `_staging` and
   refuses a resolved Compose database that does not match it;
4. invokes the standard backup script unless `--skip-backup` is explicitly
   supplied;
5. stops proxy, frontend, and backend before database replacement;
6. terminates connections only to the validated database;
7. drops and recreates only that database with its resolved owner;
8. starts the backend so its normal entrypoint runs `alembic upgrade head`;
9. waits for backend readiness;
10. verifies revision `0001_consolidated_schema` and 57 application tables;
11. starts frontend and proxy only after those checks pass.

`--skip-backup` is intended only when an operator explicitly decides that the
synthetic database has no recovery value. It does not bypass the destructive
database-name confirmation.

## Filesystem storage after the rebuild

Database rows referring to existing files are deleted, but the following bind
mounts are intentionally untouched:

- `document-storage`
- `generated-artifact-storage`
- `intake-storage`

Those files become unreferenced staging data. This script does not remove them.
If cleanup is wanted, inventory the three roots after successful database
acceptance and execute a separate, narrowly scoped, explicitly approved cleanup
operation. Never delete `DATA_ROOT` or a PostgreSQL data directory recursively.

## Verification

```bash
docker compose --env-file .env.production exec -T postgres \
  psql -U "$STAGING_DB_USER" -d "$STAGING_DB" \
  -Atc 'select version_num from alembic_version'

docker compose --env-file .env.production exec -T postgres \
  psql -U "$STAGING_DB_USER" -d "$STAGING_DB" \
  -Atc "select count(*) from pg_tables where schemaname='public' and tablename <> 'alembic_version'"

./deployment/diagnose.sh .env.production

./deployment/raspberry-smoke.sh \
  --env-file .env.production \
  --report deployment/reports/post-rebuild.json \
  --force-recreate
```

Expected values are `0001_consolidated_schema`, `57`, healthy services, and a
successful wholly synthetic lifecycle/generation smoke test.

After the rebuild, create the initial administrator interactively:

```bash
docker compose --env-file .env.production exec backend \
  python -m backend.scripts.create_admin \
  --email '<admin-address>' \
  --display-name '<display-name>'
```

Do not put the password or TOTP secret in shell history or documentation.

## Failure and recovery

If backup creation fails, the database is not dropped. Resolve the backup
failure or obtain explicit approval to use `--skip-backup`.

If failure occurs after the drop:

1. leave application services stopped;
2. preserve `docker compose ps` and redacted backend/PostgreSQL logs;
3. do not stamp the database and do not rerun destructive steps blindly;
4. if the recreated database is empty, correct the migration/startup failure
   and run the backend entrypoint again;
5. if recovery of previous synthetic state is required, follow the existing
   separate-empty-target restore procedure using the recorded backup;
6. request review before deleting or replacing any storage directory.
