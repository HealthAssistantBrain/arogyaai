# Timescale Architecture

## Purpose

This document defines the Neon + TimescaleDB analytics layout introduced for Step 2 of the cloud migration.

## Database split

### Primary PostgreSQL / Supabase-adjacent app data

Keep these responsibilities on the current primary transactional database:

- users
- user_profile
- user_settings
- auth and session metadata
- report metadata
- notifications
- feedback
- clinical history
- storage references

### Neon + TimescaleDB analytics

Move these workloads to the analytics database:

- user_vitals
- wearable_metrics
- feature_snapshots
- risk_scores
- health_scores
- baseline_metrics
- shap_values
- analytics rollups and continuous aggregates

## Current table mapping

- `user_vitals`: canonical normalized vital stream
- `wearable_metrics`: raw wearable metric stream
- `feature_snapshots`: ML feature history
- `risk_scores`: prediction history / `prediction_history` equivalent
- `health_scores`: longitudinal health score history
- `baseline_metrics`: rolling baseline snapshots
- `shap_values`: prediction driver attribution history

## Hypertables

The analytics migration creates hypertables for:

- `user_vitals` on `timestamp`
- `wearable_metrics` on `timestamp`
- `feature_snapshots` on `calculated_at`
- `risk_scores` on `calculated_at`
- `health_scores` on `calculated_at`

## Regular analytics tables

These stay as regular PostgreSQL tables:

- `baseline_metrics`
- `recommendations`
- `shap_values`

Reason:

- `baseline_metrics` behaves like a rolling snapshot table, not a dense raw event stream.
- `recommendations` and `shap_values` are tied to prediction records and are smaller relational side tables.

## Index strategy

### Raw vital streams

- `user_vitals(user_id, type, timestamp)`
- `wearable_metrics(user_id, metric_type, timestamp)`
- `id + time` unique indexes for hypertable-safe ORM identity support

### Prediction and scoring history

- `risk_scores(user_id, risk_level, calculated_at)`
- `health_scores(user_id, calculated_at)`
- `feature_snapshots(user_id, calculated_at)`

### Snapshot and attribution tables

- `baseline_metrics(user_id, metric_name)`
- `shap_values(prediction_id, feature_name)`

## Compression and retention

Default policies in the analytics migration:

- `user_vitals`: compress after 30 days, retain for 365 days
- `wearable_metrics`: compress after 30 days, retain for 365 days
- `risk_scores`: compress after 45 days, retain for 730 days
- `health_scores`: compress after 45 days, retain for 730 days

Adjust these intervals only after confirming product retention requirements.

## License-Sensitive Features

The current Neon + Timescale environment supports:

- hypertables
- `time_bucket()`
- regular relational indexes

The current environment may not support:

- compression policies
- retention policies
- continuous aggregates

Those features are attempted as best-effort steps in Alembic, but they may be skipped when the active Timescale license rejects them. The analytics query layer continues to work because `TimescaleAnalyticsService` uses raw `time_bucket()` and window queries directly.

## Continuous aggregates

When the active Timescale license permits them, the analytics migration attempts to create:

- `user_vitals_daily_summary`
- `wearable_metrics_daily_summary`
- `health_scores_daily_summary`

If they are available, they are used for:

- daily summaries
- weekly averages
- sleep and SpO2 trends
- health score trend rollups

## Query optimization patterns

Use the `TimescaleAnalyticsService` for query patterns that benefit from bucketed or windowed analytics:

- daily summaries: `daily_summaries`
- weekly averages: `weekly_averages`
- rolling health score windows: `rolling_health_scores`
- sleep trends: `sleep_trends`
- SpO2 trends: `spo2_trends`
- anomaly windows: `anomaly_windows`
- ML feature windows: `feature_window`

## Realtime updates

Analytics-side triggers now emit `NOTIFY dashboard_updates` from Neon for:

- `user_vitals`
- `wearable_metrics`
- `feature_snapshots`
- `risk_scores`
- `health_scores`
- `shap_values`

The backend websocket listener now supports listening on both the primary database and the analytics database.

Trigger safety note:

- Analytics migration `20260508_0002` updates `notify_dashboard_updates()` to use `to_jsonb(...)` field access so writes to `health_scores`, `risk_scores`, and other non-vital tables do not fail on missing trigger record fields.

## Validation SQL

```sql
SELECT hypertable_name
FROM timescaledb_information.hypertables
ORDER BY hypertable_name;

SELECT view_name
FROM timescaledb_information.continuous_aggregates
ORDER BY view_name;
```

## References

- Timescale hypertables: https://docs.timescale.com/api/latest/hypertable/create_hypertable/
- Timescale time_bucket: https://docs.timescale.com/api/latest/hyperfunctions/time_bucket/
- Timescale continuous aggregates: https://docs.timescale.com/use-timescale/latest/continuous-aggregates/
- Timescale compression policy: https://docs.timescale.com/api/latest/compression/add_compression_policy/
- Timescale retention policy: https://docs.timescale.com/api/latest/data-retention/add_retention_policy/
