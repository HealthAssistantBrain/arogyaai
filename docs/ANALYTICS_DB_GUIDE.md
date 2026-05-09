# Analytics DB Guide

## Runtime model

ArogyaAI now supports three analytics routing modes.

```env
ANALYTICS_DB_MODE=primary
```

### `primary`

- analytics reads: primary PostgreSQL
- analytics writes: primary PostgreSQL
- use when Neon is not configured yet

### `dual_write`

- analytics reads: primary PostgreSQL
- analytics writes: primary PostgreSQL plus mirrored Neon write for core analytics tables
- use during backfill and validation

### `analytics`

- analytics reads: Neon
- analytics writes: Neon
- use after Neon data has been backfilled and validated

## Runtime components

### Database routing

`apps/backend/database/session.py` now provides:

- primary engine
- analytics engine
- analytics direct engine
- model-aware session routing for analytics tables
- helper session scopes for primary, analytics, and analytics-read access

### Core analytics write paths

The following services now understand dual-write cutover:

- `UserDataService.store_vitals`
- `UserDataService.store_wearable_metrics`
- `StoragePipelineService.store_feature_snapshot`
- `StoragePipelineService.store_baseline_metrics`
- `StoragePipelineService.store_risk_score`
- `StoragePipelineService.store_shap_values`
- `StoragePipelineService.store_health_score`
- `StoragePipelineService.store_health_insights`

### Analytics query layer

`apps/backend/services/timescale_analytics_service.py` provides bucketed and windowed analytics helpers for:

- vital time buckets
- wearable buckets
- weekly averages
- daily summaries
- rolling health scores
- sleep trends
- SpO2 trends
- anomaly windows
- feature windows

## Health and observability

New health endpoints:

- `GET /health/neon`
- `GET /api/v1/health/neon`
- `GET /health/timescale`
- `GET /api/v1/health/timescale`

These report:

- Neon connectivity
- Timescale extension status
- hypertable presence
- continuous aggregate presence

## Realtime dashboard path

The dashboard websocket listener now listens on:

- primary database `dashboard_updates` notifications
- analytics database `dashboard_updates` notifications when Neon analytics is enabled

This preserves realtime refresh behavior after vitals and scores are moved to Neon.

## Analytics table list

Tables treated as analytics-domain tables by runtime routing:

- `user_vitals`
- `wearable_metrics`
- `feature_snapshots`
- `risk_scores`
- `health_scores`
- `baseline_metrics`
- `recommendations`
- `shap_values`

## Rollback approach

To rollback application reads without dropping data:

1. Set `ANALYTICS_DB_MODE=primary`
2. Restart backend and workers
3. Confirm `/health/neon` is no longer required for runtime traffic
4. Keep Neon data intact for later replay or re-cutover

## Recommended rollout order

1. Run analytics migrations on Neon.
2. Backfill analytics tables.
3. Set `ANALYTICS_DB_MODE=dual_write`.
4. Validate row counts, hypertables, bucket queries, and dashboards.
5. Switch to `ANALYTICS_DB_MODE=analytics`.
6. Keep primary analytics tables as rollback fallback until the migration is fully accepted.
