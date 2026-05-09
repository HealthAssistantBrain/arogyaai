#!/bin/sh
set -eu

DB_WAIT_RETRIES="${DB_WAIT_RETRIES:-30}"
DB_WAIT_SLEEP_SECONDS="${DB_WAIT_SLEEP_SECONDS:-2}"
ANALYTICS_WAIT_RETRIES="${ANALYTICS_WAIT_RETRIES:-15}"
ANALYTICS_WAIT_SLEEP_SECONDS="${ANALYTICS_WAIT_SLEEP_SECONDS:-2}"

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
  if alembic upgrade head; then
    echo "[startup] Migrations complete"
    return 0
  fi

  echo "[startup] Alembic migrations failed"
  return 1
}

wait_for_analytics_database() {
  analytics_url="${NEON_DIRECT_URL:-${ANALYTICS_DIRECT_URL:-${NEON_DATABASE_URL:-${ANALYTICS_DATABASE_URL:-}}}}"
  if [ -z "$analytics_url" ]; then
    echo "[startup] Analytics database URL not configured; skipping Neon wait"
    return 0
  fi

  attempt=1
  while [ "$attempt" -le "$ANALYTICS_WAIT_RETRIES" ]; do
    if ANALYTICS_DATABASE_URL="$analytics_url" python - <<'PY'
import os
import sys

from sqlalchemy import create_engine, text

database_url = os.environ.get("ANALYTICS_DATABASE_URL")
if not database_url:
    raise SystemExit(1)

connect_args = {}
if database_url.startswith("postgresql"):
    connect_args["connect_timeout"] = int(os.environ.get("DB_CONNECT_TIMEOUT_SECONDS", "3"))

try:
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
except Exception as exc:  # pragma: no cover - runtime guard
    print(f"[startup] analytics database probe failed: {exc}", file=sys.stderr)
    raise SystemExit(1)
PY
    then
      echo "[startup] Analytics database is ready"
      return 0
    fi

    echo "[startup] Waiting for analytics database... ($attempt/$ANALYTICS_WAIT_RETRIES)"
    attempt=$((attempt + 1))
    sleep "$ANALYTICS_WAIT_SLEEP_SECONDS"
  done

  echo "[startup] Analytics database did not become ready after $ANALYTICS_WAIT_RETRIES attempts"
  return 1
}

run_analytics_migrations() {
  analytics_url="${NEON_DIRECT_URL:-${ANALYTICS_DIRECT_URL:-${NEON_DATABASE_URL:-${ANALYTICS_DATABASE_URL:-}}}}"
  if [ -z "$analytics_url" ]; then
    echo "[startup] Analytics migrations requested but Neon URLs are not configured; skipping"
    return 0
  fi

  echo "[startup] Running analytics Alembic migrations once"
  if alembic -c alembic_analytics.ini upgrade head; then
    echo "[startup] Analytics migrations complete"
    return 0
  fi

  echo "[startup] Analytics Alembic migrations failed"
  return 1
}

echo "[startup] Waiting for database before starting backend"
wait_for_database

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  run_migrations
else
  echo "[startup] Skipping migrations (RUN_MIGRATIONS != true)"
fi

if [ "${RUN_ANALYTICS_MIGRATIONS:-false}" = "true" ]; then
  wait_for_analytics_database
  run_analytics_migrations
else
  echo "[startup] Skipping analytics migrations (RUN_ANALYTICS_MIGRATIONS != true)"
fi

echo "[startup] Starting backend: $*"
exec "$@"
