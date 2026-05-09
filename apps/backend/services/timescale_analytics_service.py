from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import text

from database.session import analytics_read_session_scope

ALLOWED_BUCKETS = {
    "15 minutes": "15 minutes",
    "1 hour": "1 hour",
    "6 hours": "6 hours",
    "12 hours": "12 hours",
    "1 day": "1 day",
    "7 days": "7 days",
}


def _normalize_bucket(bucket_interval: str) -> str:
    candidate = str(bucket_interval or "1 day").strip().lower()
    for allowed in ALLOWED_BUCKETS.values():
        if candidate == allowed:
            return allowed
    return "1 day"


def _days_interval(days: int) -> str:
    safe_days = max(1, int(days))
    return f"{safe_days} days"


def _serialize_bucket_rows(rows: Iterable[Any], value_key: str = "avg_value") -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows:
        mapping = row._mapping
        payload.append(
            {
                "bucket_start": mapping["bucket_start"].isoformat() if mapping.get("bucket_start") else None,
                "avg_value": float(mapping[value_key]) if mapping.get(value_key) is not None else None,
                "min_value": float(mapping["min_value"]) if mapping.get("min_value") is not None else None,
                "max_value": float(mapping["max_value"]) if mapping.get("max_value") is not None else None,
                "sample_count": int(mapping["sample_count"] or 0),
            }
        )
    return payload


class TimescaleAnalyticsService:
    @staticmethod
    def vital_buckets(
        user_id: Any,
        vital_type: str,
        *,
        bucket_interval: str = "1 day",
        days: int = 30,
    ) -> list[dict[str, Any]]:
        bucket = _normalize_bucket(bucket_interval)
        lookback = _days_interval(days)
        sql = text(
            f"""
            SELECT
                time_bucket(INTERVAL '{bucket}', timestamp) AS bucket_start,
                AVG(value) AS avg_value,
                MIN(value) AS min_value,
                MAX(value) AS max_value,
                COUNT(*) AS sample_count
            FROM user_vitals
            WHERE user_id = :user_id
              AND "type" = :vital_type
              AND timestamp >= NOW() - INTERVAL '{lookback}'
            GROUP BY bucket_start
            ORDER BY bucket_start
            """
        )
        with analytics_read_session_scope() as db:
            rows = db.execute(sql, {"user_id": str(user_id), "vital_type": vital_type}).all()
        return _serialize_bucket_rows(rows)

    @staticmethod
    def wearable_buckets(
        user_id: Any,
        metric_type: str,
        *,
        bucket_interval: str = "1 day",
        days: int = 30,
    ) -> list[dict[str, Any]]:
        bucket = _normalize_bucket(bucket_interval)
        lookback = _days_interval(days)
        sql = text(
            f"""
            SELECT
                time_bucket(INTERVAL '{bucket}', timestamp) AS bucket_start,
                AVG(value) AS avg_value,
                MIN(value) AS min_value,
                MAX(value) AS max_value,
                COUNT(*) AS sample_count
            FROM wearable_metrics
            WHERE user_id = :user_id
              AND metric_type = :metric_type
              AND timestamp >= NOW() - INTERVAL '{lookback}'
            GROUP BY bucket_start
            ORDER BY bucket_start
            """
        )
        with analytics_read_session_scope() as db:
            rows = db.execute(sql, {"user_id": str(user_id), "metric_type": metric_type}).all()
        return _serialize_bucket_rows(rows)

    @staticmethod
    def weekly_averages(user_id: Any, vital_type: str, *, weeks: int = 8) -> list[dict[str, Any]]:
        return TimescaleAnalyticsService.vital_buckets(
            user_id,
            vital_type,
            bucket_interval="7 days",
            days=max(weeks, 1) * 7,
        )

    @staticmethod
    def daily_summaries(user_id: Any, vital_type: str, *, days: int = 30) -> list[dict[str, Any]]:
        return TimescaleAnalyticsService.vital_buckets(
            user_id,
            vital_type,
            bucket_interval="1 day",
            days=days,
        )

    @staticmethod
    def rolling_health_scores(user_id: Any, *, days: int = 30) -> list[dict[str, Any]]:
        lookback = _days_interval(days)
        sql = text(
            f"""
            SELECT
                calculated_at,
                score,
                AVG(score) OVER (
                    ORDER BY calculated_at
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) AS rolling_score_7
            FROM health_scores
            WHERE user_id = :user_id
              AND calculated_at >= NOW() - INTERVAL '{lookback}'
            ORDER BY calculated_at
            """
        )
        with analytics_read_session_scope() as db:
            rows = db.execute(sql, {"user_id": str(user_id)}).all()
        return [
            {
                "calculated_at": row._mapping["calculated_at"].isoformat() if row._mapping.get("calculated_at") else None,
                "score": float(row._mapping["score"]) if row._mapping.get("score") is not None else None,
                "rolling_score_7": (
                    float(row._mapping["rolling_score_7"])
                    if row._mapping.get("rolling_score_7") is not None
                    else None
                ),
            }
            for row in rows
        ]

    @staticmethod
    def sleep_trends(user_id: Any, *, days: int = 30) -> list[dict[str, Any]]:
        return TimescaleAnalyticsService.daily_summaries(user_id, "sleep", days=days)

    @staticmethod
    def spo2_trends(user_id: Any, *, days: int = 30) -> list[dict[str, Any]]:
        return TimescaleAnalyticsService.daily_summaries(user_id, "spo2", days=days)

    @staticmethod
    def feature_window(user_id: Any, *, hours: int = 72) -> list[dict[str, Any]]:
        safe_hours = max(1, int(hours))
        sql = text(
            f"""
            SELECT
                id,
                calculated_at,
                hr_mean_7d,
                steps_avg_7d,
                sleep_efficiency,
                confidence,
                feature_payload
            FROM feature_snapshots
            WHERE user_id = :user_id
              AND calculated_at >= NOW() - INTERVAL '{safe_hours} hours'
            ORDER BY calculated_at DESC
            LIMIT 250
            """
        )
        with analytics_read_session_scope() as db:
            rows = db.execute(sql, {"user_id": str(user_id)}).all()
        return [
            {
                "id": str(row._mapping["id"]),
                "calculated_at": row._mapping["calculated_at"].isoformat() if row._mapping.get("calculated_at") else None,
                "hr_mean_7d": float(row._mapping["hr_mean_7d"]) if row._mapping.get("hr_mean_7d") is not None else None,
                "steps_avg_7d": float(row._mapping["steps_avg_7d"]) if row._mapping.get("steps_avg_7d") is not None else None,
                "sleep_efficiency": (
                    float(row._mapping["sleep_efficiency"])
                    if row._mapping.get("sleep_efficiency") is not None
                    else None
                ),
                "confidence": float(row._mapping["confidence"]) if row._mapping.get("confidence") is not None else None,
                "feature_payload": row._mapping["feature_payload"] if isinstance(row._mapping.get("feature_payload"), dict) else {},
            }
            for row in rows
        ]

    @staticmethod
    def anomaly_windows(
        user_id: Any,
        *,
        vital_types: Iterable[str] | None = None,
        hours: int = 48,
        zscore_threshold: float = 2.0,
    ) -> list[dict[str, Any]]:
        safe_hours = max(1, int(hours))
        selected_types = list(vital_types or ["heart_rate", "spo2", "sleep"])
        sql = text(
            f"""
            WITH scored AS (
                SELECT
                    timestamp,
                    "type",
                    value,
                    AVG(value) OVER (
                        PARTITION BY "type"
                        ORDER BY timestamp
                        ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
                    ) AS rolling_avg,
                    STDDEV_SAMP(value) OVER (
                        PARTITION BY "type"
                        ORDER BY timestamp
                        ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
                    ) AS rolling_stddev
                FROM user_vitals
                WHERE user_id = :user_id
                  AND "type" = ANY(:vital_types)
                  AND timestamp >= NOW() - INTERVAL '{safe_hours} hours'
            )
            SELECT
                timestamp,
                "type",
                value,
                rolling_avg,
                rolling_stddev
            FROM scored
            WHERE rolling_stddev IS NOT NULL
              AND ABS(value - rolling_avg) >= :zscore_threshold * rolling_stddev
            ORDER BY timestamp DESC
            LIMIT 100
            """
        )
        with analytics_read_session_scope() as db:
            rows = db.execute(
                sql,
                {
                    "user_id": str(user_id),
                    "vital_types": selected_types,
                    "zscore_threshold": float(zscore_threshold),
                },
            ).all()
        return [
            {
                "timestamp": row._mapping["timestamp"].isoformat() if row._mapping.get("timestamp") else None,
                "type": row._mapping["type"],
                "value": float(row._mapping["value"]) if row._mapping.get("value") is not None else None,
                "rolling_avg": (
                    float(row._mapping["rolling_avg"])
                    if row._mapping.get("rolling_avg") is not None
                    else None
                ),
                "rolling_stddev": (
                    float(row._mapping["rolling_stddev"])
                    if row._mapping.get("rolling_stddev") is not None
                    else None
                ),
            }
            for row in rows
        ]
