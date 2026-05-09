# Migration Guide

## Goal

Move analytics and time-series workloads to Neon + TimescaleDB without breaking auth, onboarding, storage, or transactional flows.

## Scope

Move only analytics-domain tables:

- `user_vitals`
- `wearable_metrics`
- `feature_snapshots`
- `risk_scores`
- `health_scores`
- `baseline_metrics`
- `shap_values`
- related analytics rollups

Do not move:

- `users`
- `user_profile`
- auth or session tables
- notifications
- storage metadata
- onboarding core state

## Recommended rollout plan

### Phase 1. Prepare Neon

1. Create the Neon project.
2. Enable `timescaledb`.
3. Set `NEON_DATABASE_URL` and `NEON_DIRECT_URL`.
4. Run analytics migrations:

```bash
cd apps/backend
alembic -c alembic_analytics.ini upgrade head
```

### Phase 2. Backfill data

Backfill table by table, not all at once.

Recommended order:

1. `user_vitals`
2. `wearable_metrics`
3. `feature_snapshots`
4. `risk_scores`
5. `health_scores`
6. `baseline_metrics`
7. `shap_values`

Suggested approach:

- export each table from the current primary database
- import into Neon
- validate row counts before moving to the next table

Example with `pg_dump` and `psql`:

```bash
pg_dump --data-only --table=user_vitals "$DATABASE_URL" | psql "$NEON_DIRECT_URL"
pg_dump --data-only --table=wearable_metrics "$DATABASE_URL" | psql "$NEON_DIRECT_URL"
pg_dump --data-only --table=feature_snapshots "$DATABASE_URL" | psql "$NEON_DIRECT_URL"
pg_dump --data-only --table=risk_scores "$DATABASE_URL" | psql "$NEON_DIRECT_URL"
pg_dump --data-only --table=health_scores "$DATABASE_URL" | psql "$NEON_DIRECT_URL"
pg_dump --data-only --table=baseline_metrics "$DATABASE_URL" | psql "$NEON_DIRECT_URL"
pg_dump --data-only --table=shap_values "$DATABASE_URL" | psql "$NEON_DIRECT_URL"
```

If you need stricter control, use `COPY` table-by-table in maintenance windows instead of piping full dumps.

### Phase 3. Enable dual-write

Set:

```env
ANALYTICS_DB_MODE=dual_write
```

Then restart backend and workers.

Behavior:

- reads still come from the primary database
- core analytics writes are mirrored to Neon
- live product behavior stays stable while Neon catches new writes

### Phase 4. Validate Neon

Validation checklist:

- `/health/neon` returns `ok`
- `/health/timescale` shows the extension and hypertables
- row counts match for each migrated table
- `time_bucket` queries return data
- dashboards still render
- Google Fit ingest still writes vitals
- predictions still persist

Row count examples:

```sql
SELECT COUNT(*) FROM user_vitals;
SELECT COUNT(*) FROM wearable_metrics;
SELECT COUNT(*) FROM risk_scores;
SELECT COUNT(*) FROM health_scores;
```

### Phase 5. Cut over reads

Set:

```env
ANALYTICS_DB_MODE=analytics
```

Then restart backend and workers.

Behavior:

- analytics reads use Neon
- analytics writes use Neon
- primary transactional data remains unchanged

### Phase 6. Keep rollback window open

Do not drop legacy analytics tables immediately.

Keep the primary copies until:

- production validation is complete
- dashboards and ingest are stable
- prediction persistence is confirmed
- staging and production row growth is normal

## Rollback

If you need to revert quickly:

1. Set `ANALYTICS_DB_MODE=primary`
2. Restart backend and workers
3. Keep Neon data untouched
4. Investigate the mismatch or query issue
5. Re-enter `dual_write` after the fix

## Why this approach is safe

- no destructive primary-database migration is required for cutover
- reads switch only after validation
- writes can be mirrored during the transition
- rollback is an environment change, not a schema rebuild
