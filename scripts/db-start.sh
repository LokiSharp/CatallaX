#!/usr/bin/env bash
# Initialize (if needed) and start local PostgreSQL for CatallaX development.
set -euo pipefail

if [[ -z "${PGDATA:-}" ]]; then
  echo "error: PGDATA is not set. Run this inside 'devbox shell' or via 'devbox run'." >&2
  exit 1
fi

# Non-default port to avoid clashing with a system/Docker PostgreSQL on 5432.
PG_PORT="${PGPORT:-15432}"
SOCKET_DIR="${PGHOST:-$PWD/.devbox/virtenv/postgresql}"
LOG_FILE="${SOCKET_DIR}/postgres.log"

mkdir -p "$SOCKET_DIR"

if [[ ! -f "$PGDATA/PG_VERSION" ]]; then
  echo "Initializing PostgreSQL cluster at $PGDATA ..."
  # Local sockets: trust (admin ops). TCP: scram-sha-256 (matches app password auth).
  initdb \
    --pgdata="$PGDATA" \
    --auth-local=trust \
    --auth-host=scram-sha-256 \
    --username="$(whoami)" \
    --encoding=UTF8 \
    --locale=C

  conf="$PGDATA/postgresql.conf"
  if grep -qE "^#?listen_addresses" "$conf"; then
    sed -i "s/^#\\?listen_addresses.*/listen_addresses = 'localhost'/" "$conf"
  else
    echo "listen_addresses = 'localhost'" >>"$conf"
  fi
  if grep -qE "^#?port" "$conf"; then
    sed -i "s/^#\\?port.*/port = ${PG_PORT}/" "$conf"
  else
    echo "port = ${PG_PORT}" >>"$conf"
  fi
fi

if pg_isready -h localhost -p "$PG_PORT" >/dev/null 2>&1; then
  echo "PostgreSQL is already running on localhost:${PG_PORT}"
  exit 0
fi

echo "Starting PostgreSQL ..."
# Prefer pg_ctl for a self-contained local cluster (no process-compose required).
pg_ctl \
  -D "$PGDATA" \
  -l "$LOG_FILE" \
  -o "-k ${SOCKET_DIR} -p ${PG_PORT}" \
  start

for _ in $(seq 1 30); do
  if pg_isready -h localhost -p "$PG_PORT" >/dev/null 2>&1; then
    echo "PostgreSQL is ready on localhost:${PG_PORT}"
    exit 0
  fi
  sleep 0.5
done

echo "error: PostgreSQL did not become ready in time. See ${LOG_FILE}" >&2
exit 1
