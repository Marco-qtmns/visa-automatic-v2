#!/usr/bin/env bash
set -euo pipefail

EXPECTED_DATABASE=""
EXPECTED_REVISION="0001_consolidated_schema"
EXPECTED_TABLE_COUNT="57"
ENV_FILE=".env.production"
CONFIRM_DATABASE=""
CREATE_BACKUP="true"

usage() {
  echo "Usage: $0 [--env-file PATH] [--skip-backup] --expected-database NAME --confirm-destroy NAME" >&2
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --env-file)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      ENV_FILE="$2"
      shift 2
      ;;
    --skip-backup)
      CREATE_BACKUP="false"
      shift
      ;;
    --expected-database)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      EXPECTED_DATABASE="$2"
      shift 2
      ;;
    --confirm-destroy)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      CONFIRM_DATABASE="$2"
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ ! "$EXPECTED_DATABASE" =~ ^[A-Za-z_][A-Za-z0-9_]*_staging$ ]]; then
  echo "Refusing destructive operation: --expected-database must be a safe identifier ending in _staging." >&2
  exit 2
fi
if [ "$CONFIRM_DATABASE" != "$EXPECTED_DATABASE" ]; then
  echo "Refusing destructive operation: --confirm-destroy must exactly match --expected-database." >&2
  exit 2
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file was not found." >&2
  exit 2
fi
if [ ! -x deployment/backup-staging.sh ]; then
  echo "Run this script from the repository root." >&2
  exit 2
fi

compose() {
  docker compose --env-file "$ENV_FILE" "$@"
}

# The resolved Compose JSON may contain secrets.  Feed it directly to Python
# and emit only validated, non-secret identifiers.
resolved_identity="$({ compose config --format json || exit 1; } | python3 -c '
import json, re, sys
config = json.load(sys.stdin)
environment = config["services"]["postgres"].get("environment", {})
database = str(environment.get("POSTGRES_DB", ""))
owner = str(environment.get("POSTGRES_USER", ""))
identifier = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
if not identifier.fullmatch(database) or not identifier.fullmatch(owner):
    raise SystemExit("resolved PostgreSQL identifiers are unsafe")
print(database + "\t" + owner)
')"
IFS=$'\t' read -r resolved_database resolved_owner <<< "$resolved_identity"

if [ "$resolved_database" != "$EXPECTED_DATABASE" ]; then
  echo "Refusing destructive operation: resolved Compose database is not the expected staging database." >&2
  exit 2
fi

failed() {
  echo "Staging database reinitialization failed." >&2
  echo "Application services may remain stopped. Inspect Compose status and backend logs before recovery." >&2
  echo "If a backup was requested, preserve it and follow docs/database/raspberry-database-rebuild.md." >&2
}
trap failed ERR

if [ "$CREATE_BACKUP" = "true" ]; then
  echo "Creating the standard pre-reset staging backup."
  deployment/backup-staging.sh --env-file "$ENV_FILE"
else
  echo "WARNING: operator explicitly skipped the pre-reset backup."
fi

echo "Stopping application services before database replacement."
compose stop proxy frontend backend
compose up -d postgres

echo "Recreating only the validated staging database; PostgreSQL volumes remain intact."
compose exec -T postgres psql --set=ON_ERROR_STOP=1 --username "$resolved_owner" --dbname postgres \
  --set=target_database="$resolved_database" --set=target_owner="$resolved_owner" <<'SQL'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = :'target_database' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS :"target_database";
CREATE DATABASE :"target_database" OWNER :"target_owner";
SQL

echo "Starting backend; its entrypoint applies the consolidated baseline."
compose up -d backend

ready="false"
for _attempt in $(seq 1 24); do
  if compose exec -T backend python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=5).read()" \
    >/dev/null 2>&1; then
    ready="true"
    break
  fi
  sleep 5
done
if [ "$ready" != "true" ]; then
  echo "Backend did not become ready after applying the baseline." >&2
  exit 1
fi

revision="$(compose exec -T postgres psql --tuples-only --no-align \
  --username "$resolved_owner" --dbname "$resolved_database" \
  --command 'SELECT version_num FROM alembic_version')"
if [ "$revision" != "$EXPECTED_REVISION" ]; then
  echo "Unexpected Alembic revision after reinitialization." >&2
  exit 1
fi

table_count="$(compose exec -T postgres psql --tuples-only --no-align \
  --username "$resolved_owner" --dbname "$resolved_database" \
  --command "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")"
if [ "$table_count" != "$EXPECTED_TABLE_COUNT" ]; then
  echo "Unexpected application table count after reinitialization." >&2
  exit 1
fi

echo "Starting frontend and proxy after backend readiness passed."
compose up -d frontend proxy
compose ps
trap - ERR
echo "Staging database reinitialized at $EXPECTED_REVISION with $EXPECTED_TABLE_COUNT application tables."
echo "Document, intake, and generated-artifact storage were not deleted."
