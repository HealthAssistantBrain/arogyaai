# Neon Setup

Verified against Neon docs on 2026-05-08.

## Goal

Use Neon for ArogyaAI analytics and time-series workloads while keeping Supabase auth/storage and the current primary PostgreSQL workflow intact.

## 1. Create a Neon account

1. Go to https://neon.com and create or sign in to your account.
2. Create or select the organization that will own the ArogyaAI analytics project.

## 2. Create the Neon project

1. In the Neon Console, click `New Project`.
2. Name the project `arogyaai-analytics` or a similar environment-specific name.
3. Choose the PostgreSQL version you want for the environment.
   Use the same major version for staging and production when possible.
4. Choose the region closest to the FastAPI backend and Celery workers.
   Pick the same cloud/region family as your backend deployment when possible to reduce latency.
5. Finish project creation.

Notes:

- Neon docs currently describe new projects as creating default branches for `production` and `development`.
- If your organization template shows different branch names, keep one stable production branch and one non-production branch for staging or development.

## 3. Recommended branch strategy

- `production`: live analytics branch used by production backend.
- `staging`: child branch created from `production` for pre-release validation.
- `development`: branch used by developers or local shared testing.
- short-lived feature branches: optional for schema rehearsals and one-off backfill tests.

## 4. Recommended compute settings

- Production: autoscaling or fixed compute sized for sustained ingest and dashboard traffic.
- Staging: smaller autoscaling range than production.
- Development: smallest practical compute with scale-to-zero enabled if cold starts are acceptable.

Use Neon compute settings for the branch you actually connect to. Changing project defaults only affects newly created computes.

## 5. Enable TimescaleDB

Connect to the target branch and target database first, then run:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

Validate:

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('timescaledb', 'pgcrypto')
ORDER BY extname;
```

Expected result:

- `timescaledb` is present
- `pgcrypto` is present

Compatibility notes:

- Neon supports `timescaledb` as a supported extension.
- Neon is managed Postgres, so extension installation is limited to supported extensions.
- Use a direct connection for admin tasks that need session semantics, such as migrations or `LISTEN/NOTIFY`.

## 6. Get both connection strings

In the Neon Console:

1. Open the project.
2. Click `Connect`.
3. Select the branch, database, and role you want ArogyaAI to use.
4. Copy the pooled connection string.
5. Toggle or select the direct connection string and copy that too.

Use them like this:

- `NEON_DATABASE_URL`: pooled application connection string
- `NEON_DIRECT_URL`: direct admin connection string for Alembic and session-bound operations

Example:

```env
NEON_DATABASE_URL=postgresql+psycopg2://<role>:<password>@<endpoint>-pooler.<region>.aws.neon.tech/<database>?sslmode=require&channel_binding=require
NEON_DIRECT_URL=postgresql+psycopg2://<role>:<password>@<endpoint>.<region>.aws.neon.tech/<database>?sslmode=require&channel_binding=require
```

Important:

- The pooled hostname contains `-pooler`.
- Keep `sslmode=require`.
- The direct URL is preferred for analytics migrations and realtime database listeners.

## 7. Configure ArogyaAI environment variables

Update the root `.env` and, for local non-Docker backend runs, `apps/backend/.env`.

Minimum analytics variables:

```env
ANALYTICS_DB_MODE=dual_write
NEON_DATABASE_URL=
NEON_DIRECT_URL=
TIMESCALE_ENABLED=true
ANALYTICS_DB_READ_FALLBACK=true
RUN_ANALYTICS_MIGRATIONS=true
HEALTH_ANALYTICS_DB_TIMEOUT_SECONDS=12
HEALTH_TIMESCALE_TIMEOUT_SECONDS=12
```

Mode meanings:

- `primary`: use the current primary PostgreSQL database for analytics reads and writes.
- `dual_write`: keep analytics reads on the primary database, but mirror core analytics writes to Neon.
- `analytics`: send analytics reads and writes directly to Neon.

## 8. Run migrations

Primary database:

```bash
cd apps/backend
alembic upgrade head
```

Analytics database:

```bash
cd apps/backend
alembic -c alembic_analytics.ini upgrade head
```

Docker:

```bash
RUN_ANALYTICS_MIGRATIONS=true docker compose up --build
```

The backend entrypoint now supports a second migration pass for Neon when `RUN_ANALYTICS_MIGRATIONS=true`.

Current analytics migration head:

- `20260508_0002` fixes the shared analytics dashboard trigger so non-vital tables do not raise `record "old" has no field "type"` during mirrored writes.

## 9. Validate the Neon connection

Application checks:

```bash
curl http://localhost:8000/health/neon
curl http://localhost:8000/health/timescale
```

Database checks:

```sql
SELECT current_database(), current_user, version();

SELECT hypertable_name
FROM timescaledb_information.hypertables
WHERE hypertable_name IN (
  'wearable_metrics',
  'user_vitals',
  'feature_snapshots',
  'risk_scores',
  'health_scores'
)
ORDER BY hypertable_name;

SELECT view_name
FROM timescaledb_information.continuous_aggregates
ORDER BY view_name;
```

Managed Timescale note:

- The current Neon environment supports hypertables and `time_bucket()`.
- Compression policies, retention policies, and continuous aggregates may be rejected under the current Timescale `apache` license.
- The analytics migrations treat those features as best-effort so the schema install remains non-destructive and rollback-friendly.

## 10. Test hypertables

Insert a disposable test row for a known user UUID:

```sql
INSERT INTO user_vitals (
  user_id,
  "type",
  value,
  unit,
  timestamp,
  source
)
VALUES (
  '00000000-0000-0000-0000-000000000001',
  'HEART_RATE',
  72,
  'bpm',
  NOW(),
  'GOOGLE_FIT'
);
```

Run a bucket query:

```sql
SELECT
  time_bucket(INTERVAL '1 hour', timestamp) AS bucket_start,
  AVG(value) AS avg_value,
  COUNT(*) AS sample_count
FROM user_vitals
WHERE user_id = '00000000-0000-0000-0000-000000000001'
  AND "type" = 'HEART_RATE'
GROUP BY bucket_start
ORDER BY bucket_start DESC;
```

## References

- Neon connect docs: https://neon.com/docs/get-started-with-neon/connect-neon
- Neon connection pooling: https://neon.com/docs/connect/connection-pooling
- Neon project management: https://neon.com/docs/manage/projects
- Neon compute management: https://neon.com/docs/manage/endpoints/
- Neon Postgres extensions: https://neon.com/docs/extensions/extensions-intro
- Neon compatibility notes: https://neon.com/docs/reference/compatibility
