#!/usr/bin/env bash
# Drop and recreate the local development database, then run migrations.
# For local/dev testing only — refuses non-local database names.
set -euo pipefail

DB_USER="${CATALLAX_DB_USER:-catallax}"
DB_PASSWORD="${CATALLAX_DB_PASSWORD:-catallax}"
DB_NAME="${CATALLAX_DB_NAME:-catallax_dev}"
PG_HOST="${CATALLAX_PG_HOST:-localhost}"
PG_PORT="${PGPORT:-15432}"

# Safety: only reset known local database names.
case "$DB_NAME" in
  catallax_dev | catallax_test) ;;
  *)
    echo "error: refusing to reset database '${DB_NAME}'." >&2
    echo "Only catallax_dev / catallax_test are allowed (override CATALLAX_DB_NAME carefully)." >&2
    exit 1
    ;;
esac

if ! pg_isready -h "$PG_HOST" -p "$PG_PORT" >/dev/null 2>&1; then
  echo "error: PostgreSQL is not ready on ${PG_HOST}:${PG_PORT}." >&2
  echo "Run: devbox run db-start" >&2
  exit 1
fi

# Admin ops use the Devbox Unix socket + local trust auth (superuser = OS user).
psql_admin() {
  local db="${1:-postgres}"
  shift || true
  if [[ -n "${PGHOST:-}" ]]; then
    env PGHOST="$PGHOST" PGPORT="$PG_PORT" psql -d "$db" "$@"
  else
    psql -h "$PG_HOST" -p "$PG_PORT" -d "$db" "$@"
  fi
}

echo "Resetting database '${DB_NAME}' on ${PG_HOST}:${PG_PORT} ..."

db_exists="$(
  psql_admin postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | tr -d '[:space:]'
)"
if [[ "$db_exists" == "1" ]]; then
  # FORCE terminates remaining client connections (PostgreSQL 13+).
  psql_admin postgres -v ON_ERROR_STOP=1 -c \
    "DROP DATABASE ${DB_NAME} WITH (FORCE)"
  echo "Dropped database ${DB_NAME}."
else
  echo "Database ${DB_NAME} did not exist (nothing to drop)."
fi

# Recreate role + database + grants (idempotent).
bash "$(dirname "$0")/db-init.sh"

echo "Running migrations ..."
uv run alembic upgrade head

echo "db-reset complete: ${DB_USER}@${PG_HOST}:${PG_PORT}/${DB_NAME}"
