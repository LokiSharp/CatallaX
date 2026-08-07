#!/usr/bin/env bash
# Idempotently create the development role and database.
# Does NOT drop existing databases or roles.
set -euo pipefail

DB_USER="${CATALLAX_DB_USER:-catallax}"
DB_PASSWORD="${CATALLAX_DB_PASSWORD:-catallax}"
DB_NAME="${CATALLAX_DB_NAME:-catallax_dev}"
PG_HOST="${CATALLAX_PG_HOST:-localhost}"
PG_PORT="${PGPORT:-15432}"

if ! pg_isready -h "$PG_HOST" -p "$PG_PORT" >/dev/null 2>&1; then
  echo "error: PostgreSQL is not ready on ${PG_HOST}:${PG_PORT}." >&2
  echo "Run: devbox run db-start" >&2
  exit 1
fi

# Admin ops use the Devbox Unix socket + local trust auth (superuser = OS user).
# Application connections still use TCP + password via DATABASE_URL.
psql_admin() {
  local db="${1:-postgres}"
  shift || true
  if [[ -n "${PGHOST:-}" ]]; then
    # PGHOST is the socket directory in Devbox's PostgreSQL plugin.
    env PGHOST="$PGHOST" PGPORT="$PG_PORT" psql -d "$db" "$@"
  else
    psql -h "$PG_HOST" -p "$PG_PORT" -d "$db" "$@"
  fi
}

echo "Ensuring role '${DB_USER}' exists ..."
role_exists="$(
  psql_admin postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}'" | tr -d '[:space:]'
)"
if [[ "$role_exists" != "1" ]]; then
  psql_admin postgres -v ON_ERROR_STOP=1 -c \
    "CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}'"
  echo "Created role ${DB_USER}."
else
  # Keep password in sync for local dev without failing if role already exists.
  psql_admin postgres -v ON_ERROR_STOP=1 -c \
    "ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}'"
  echo "Role ${DB_USER} already exists (password refreshed)."
fi

echo "Ensuring database '${DB_NAME}' exists ..."
db_exists="$(
  psql_admin postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | tr -d '[:space:]'
)"
if [[ "$db_exists" != "1" ]]; then
  psql_admin postgres -v ON_ERROR_STOP=1 -c \
    "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}"
  echo "Created database ${DB_NAME}."
else
  echo "Database ${DB_NAME} already exists (left unchanged)."
fi

psql_admin postgres -v ON_ERROR_STOP=1 -c \
  "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER}"

# On PostgreSQL 15+, schema privileges matter for non-superusers.
psql_admin "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
SQL

echo "db-init complete: ${DB_USER}@${PG_HOST}:${PG_PORT}/${DB_NAME}"
