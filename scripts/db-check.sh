#!/usr/bin/env bash
# Smoke-test: application config → SQLAlchemy → PostgreSQL.
set -euo pipefail

uv run python - <<'PY'
from sqlalchemy import text

from catallax.config import settings
from catallax.db.session import get_engine

print(f"env          = {settings.env}")
print(f"database_url = {settings.database_url}")

engine = get_engine()
with engine.connect() as conn:
    version = conn.execute(text("SELECT version()")).scalar_one()
    db = conn.execute(text("SELECT current_database()")).scalar_one()
    user = conn.execute(text("SELECT current_user")).scalar_one()

print(f"connected as = {user}")
print(f"database     = {db}")
print(f"server       = {version.split(',')[0]}")
print("db-check: OK")
PY
