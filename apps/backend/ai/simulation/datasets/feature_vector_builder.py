from __future__ import annotations

from typing import Any

from .._shared import clamp, rolling, slope


class FeatureVectorBuilder:
    METRICS = ("heart_rate", "hrv", "spo2", "activity_steps", "stress_index", "glucose", "blood_pressure_systolic", "blood_pressure_diastolic", "recovery_index")

    @classmethod
    def build(cls, *, profile: dict, points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        vectors: list[dict[str, Any]] = []
        baselines = profile["baseline_metrics"]
        histories = {metric: [float(point.get(metric) or 0.0) for point in points] for metric in cls.METRICS}
        rolling_means = {metric: rolling(values, 24) for metric, values in histories.items()}
        rolling_short = {metric: rolling(values, 6) for metric, values in histories.items()}

        for index, point in enumerate(points):
            vector = {
                "user_id": profile["user_id"],
                "timestamp": point["timestamp"].isoformat(),
                "synthetic_profile": profile["synthetic_profile"],
                "hour_sin": round(__import__("math").sin((point["timestamp"].hour / 24.0) * __import__("math").tau), 6),
                "hour_cos": round(__import__("math").cos((point["timestamp"].hour / 24.0) * __import__("math").tau), 6),
                "day_of_week": point["timestamp"].weekday(),
                "trajectory_phase": point["trajectory_phase"],
                "anomaly_score": round(float(point.get("anomaly_score", 0.0)), 4),
                "risk_target": round(max(point["state"]["cardio_load"], point["state"]["metabolic_load"], point["state"]["fatigue_load"]), 4),
                "future_recovery_target": round(float(point.get("recovery_index", 0.0)) / 100.0, 4),
            }
            for metric in cls.METRICS:
                current = float(point.get(metric) or 0.0)
                baseline = float(baselines.get(metric, 0.0) or 0.0)
                vector[metric] = round(current, 4)
                vector[f"{metric}_delta"] = round(current - baseline, 4)
                vector[f"{metric}_mean_24h"] = round(rolling_means[metric][index], 4)
                vector[f"{metric}_mean_6h"] = round(rolling_short[metric][index], 4)
                vector[f"{metric}_trend_6h"] = round(slope(histories[metric][max(0, index - 5) : index + 1]), 4)
                vector[f"{metric}_normalized"] = round(clamp(current / max(baseline or 1.0, 1.0), 0.0, 3.0), 4)
            vectors.append(vector)
        return vectors
