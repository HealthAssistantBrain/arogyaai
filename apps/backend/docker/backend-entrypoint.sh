#!/bin/sh
set -eu

DB_WAIT_RETRIES="${DB_WAIT_RETRIES:-30}"
DB_WAIT_SLEEP_SECONDS="${DB_WAIT_SLEEP_SECONDS:-2}"

if [ "$#" -eq 0 ]; then
  set -- uvicorn main:app --host 0.0.0.0 --port 8000
fi

wait_for_database() {
  attempt=1
  while [ "$attempt" -le "$DB_WAIT_RETRIES" ]; do
    if python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, text

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("[startup] DATABASE_URL is not set", file=sys.stderr)
    raise SystemExit(1)

connect_args = {}
if database_url.startswith("postgresql"):
    connect_args["connect_timeout"] = int(os.environ.get("DB_CONNECT_TIMEOUT_SECONDS", "3"))

try:
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as exc:  # pragma: no cover - runtime guard
    print(f"[startup] database probe failed: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
    then
      echo "[startup] Database is ready"
      return 0
    fi

    echo "[startup] Waiting for database... ($attempt/$DB_WAIT_RETRIES)"
    attempt=$((attempt + 1))
    sleep "$DB_WAIT_SLEEP_SECONDS"
  done

  echo "[startup] Database did not become ready after $DB_WAIT_RETRIES attempts"
  return 1
}

run_migrations() {
  echo "[startup] Running Alembic migrations once"
  if alembic upgrade heads; then
    echo "[startup] Migrations complete"
    return 0
  fi

  echo "[startup] Alembic migrations failed"
  return 1
}

echo "[startup] Waiting for database before starting backend"
wait_for_database

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  run_migrations
else
  echo "[startup] Skipping migrations (RUN_MIGRATIONS != true)"
fi

echo "[startup] Starting backend: $*"
exec "$@"
