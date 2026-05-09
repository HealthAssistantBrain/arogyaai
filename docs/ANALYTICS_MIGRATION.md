# Analytics Migration

## Purpose

This document covers the dedicated Alembic track for Neon + Timescale analytics objects introduced during Step 2.

## Migration Tracks

- Transactional schema: `apps/backend/alembic.ini`
- Analytics schema: `apps/backend/alembic_analytics.ini`

Keep these tracks separate. The transactional database remains the source of truth for auth, profile, onboarding, and operational APIs. The analytics database owns hypertables and mirrored prediction history.

## Applied Analytics Revisions

- `20260508_0001`
  Initializes the analytics schema, hypertables, indexes, and best-effort Timescale features.
- `20260508_0002`
  Fixes the analytics `notify_dashboard_updates()` trigger so mirrored writes on non-vital tables do not fail.

## Runbook

```bash
cd apps/backend
alembic -c alembic_analytics.ini upgrade head
```

Docker startup path:

```bash
RUN_ANALYTICS_MIGRATIONS=true docker compose up --build
```

## Validation

Check the revision:

```sql
SELECT version_num
FROM alembic_version_analytics;
```

Check hypertables:

```sql
SELECT hypertable_name
FROM timescaledb_information.hypertables
ORDER BY hypertable_name;
```

Check `time_bucket()`:

```sql
SELECT time_bucket(INTERVAL '1 day', NOW());
```

## Best-Effort Timescale Features

The migration attempts these features when the active Timescale license allows them:

- compression policies
- retention policies
- continuous aggregates

On the current Neon environment, those operations may be rejected under the active Timescale `apache` license. The migration intentionally contains savepoint-based best-effort execution so unsupported features do not abort the whole analytics deployment.

## Rollback

To step back one analytics revision:

```bash
cd apps/backend
alembic -c alembic_analytics.ini downgrade -1
```

To disable runtime use of Neon without removing the schema:

```env
ANALYTICS_DB_MODE=primary
```

Then restart the backend. This preserves rollback capability without deleting analytics data.
