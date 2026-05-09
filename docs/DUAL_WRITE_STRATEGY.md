# Dual-Write Strategy

## Goal

`ANALYTICS_DB_MODE=dual_write` keeps the primary PostgreSQL database authoritative for operational reads while mirroring analytics writes to Neon.

## Read/Write Matrix

- `primary`
  Analytics reads: primary DB
  Analytics writes: primary DB
- `dual_write`
  Analytics reads: primary DB
  Analytics writes: primary DB + best-effort Neon mirror
- `analytics`
  Analytics reads: Neon
  Analytics writes: Neon

## Mirrored Tables

The current mirror path covers:

- `user_vitals`
- `wearable_metrics`
- `feature_snapshots`
- `risk_scores`
- `health_scores`
- `baseline_metrics`
- `shap_values`

`risk_scores` is the current `prediction_history` equivalent.

## Write Ordering

Primary-first ordering is intentional:

1. Write to the primary DB.
2. Commit the primary DB transaction.
3. Attempt the analytics mirror in a separate analytics session.
4. Log analytics mirror failures without rolling back the primary success.

This keeps operational APIs, onboarding, and auth-safe flows stable even if Neon is slow or temporarily unavailable.

## Failure Handling

- Mirror failures are logged with table-specific context.
- Recursive mirror writes are prevented by the internal `_mirror_to_analytics=False` guard.
- Reads remain on the primary DB in `dual_write` mode, so temporary Neon drift does not break dashboard/profile reads.

## Runtime Health

Use:

- `GET /health/neon`
- `GET /health/timescale`
- `GET /api/v1/health`

Recommended env defaults:

```env
HEALTH_ANALYTICS_DB_TIMEOUT_SECONDS=12
HEALTH_TIMESCALE_TIMEOUT_SECONDS=12
```

These higher thresholds help avoid false degradations on cold Neon connections.

## Rollback Path

If Neon analytics becomes unstable:

1. Set `ANALYTICS_DB_MODE=primary`
2. Restart the backend
3. Leave analytics migrations and data in place
4. Investigate Neon separately without blocking core product flows

This preserves backward compatibility and avoids destructive rollbacks.
