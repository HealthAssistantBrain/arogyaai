# Troubleshooting

## `TypeError: Boolean value of this clause is not defined`

Cause:

- SQLAlchemy mapper/selectable objects were being resolved with boolean fallback logic such as `A or B`.

Fix:

- `apps/backend/database/session.py` now uses explicit `None` checks in `_resolve_table_name()`.

Verify:

```python
db.query(User).all()
db.query(HealthScoreRecord).all()
```

## Alembic `ModuleNotFoundError: No module named 'models.base'`

Cause:

- Alembic was prepending the wrong path and could resolve the wrong top-level `models/` package.

Fix:

- `apps/backend/alembic.ini`
- `apps/backend/alembic_analytics.ini`

Both now use:

```ini
prepend_sys_path = %(here)s
```

## Analytics Migration Fails With `InFailedSqlTransaction`

Cause:

- Best-effort Timescale statements were swallowing exceptions without rolling back the failed statement, leaving the outer transaction aborted.

Fix:

- Analytics migration `20260508_0001` now wraps best-effort statements in nested transactions (savepoints).

## Analytics Write Fails With `record "old" has no field "type"`

Cause:

- `notify_dashboard_updates()` referenced `OLD."type"` / `NEW."type"` directly even when attached to non-vital tables.

Fix:

- Analytics migration `20260508_0002` recreates the function using `to_jsonb(OLD)->>'type'` and `to_jsonb(NEW)->>'metric_type'`.

Verify:

```sql
SELECT pg_get_functiondef('notify_dashboard_updates()'::regprocedure);
```

## `/health/neon` or `/health/timescale` Reports Timeout While Neon Is Reachable

Cause:

- Cold Neon connections can take several seconds even when the database is healthy.

Fix:

```env
HEALTH_ANALYTICS_DB_TIMEOUT_SECONDS=12
HEALTH_TIMESCALE_TIMEOUT_SECONDS=12
```

Then restart the backend:

```bash
docker compose restart backend
```

## Hypertables Exist But No Continuous Aggregates or Policy Jobs Appear

Cause:

- The current Timescale environment may reject retention policies, compression policies, and continuous aggregates under the active `apache` license.

Verify:

```sql
SELECT hypertable_name
FROM timescaledb_information.hypertables
ORDER BY hypertable_name;

SELECT view_name
FROM timescaledb_information.continuous_aggregates
ORDER BY view_name;

SELECT application_name, hypertable_name, proc_name
FROM timescaledb_information.jobs
ORDER BY application_name;
```

Current expected behavior:

- Hypertables present
- `time_bucket()` works
- Continuous aggregates may be empty
- Policy jobs may be absent

## Host-Shell Alembic Cannot Reach `postgres`

Cause:

- Root `.env` may use the Docker hostname `postgres`, which only resolves inside Docker networking.

Options:

- Run Alembic inside the backend container
- Or use the published host port with a host-reachable `DATABASE_URL`

## Backend Restarted But Live Endpoints Still Show Old Behavior

Cause:

- The container was not restarted after Python code changes.

Fix:

```bash
docker compose restart backend
```

After restart, re-check:

```bash
curl http://127.0.0.1:8000/health/neon
curl http://127.0.0.1:8000/health/timescale
curl http://127.0.0.1:8000/api/v1/health
```
