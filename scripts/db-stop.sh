#!/usr/bin/env bash
# Stop local PostgreSQL.
set -euo pipefail

if [[ -z "${PGDATA:-}" ]]; then
  echo "error: PGDATA is not set. Run this inside 'devbox shell' or via 'devbox run'." >&2
  exit 1
fi

PG_PORT="${PGPORT:-15432}"

if ! pg_isready -h localhost -p "$PG_PORT" >/dev/null 2>&1 \
  && ! pg_ctl -D "$PGDATA" status >/dev/null 2>&1; then
  echo "PostgreSQL is not running."
  exit 0
fi

pg_ctl -D "$PGDATA" stop -m fast
echo "PostgreSQL stopped."
