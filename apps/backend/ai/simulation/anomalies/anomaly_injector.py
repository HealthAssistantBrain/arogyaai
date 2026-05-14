from __future__ import annotations

from datetime import timedelta
from typing import Any

from .physiological_outliers import PLAUSIBLE_ANOMALIES
from .sensor_failure_simulator import SensorFailureSimulator
from .._shared import build_rng, clamp, log_simulation


class AnomalyInjector:
    @staticmethod
    def inject(points: list[dict[str, Any]], profile: dict, anomaly_budget: float = 0.12) -> None:
        rng = build_rng(profile["user_id"], profile["synthetic_profile"], "anomalies")
        anomaly_count = max(1, int(len(points) * anomaly_budget / 48))
        if not points:
            return

        for index in range(anomaly_count):
            point_index = rng.randint(12, max(12, len(points) - 12))
            point = points[min(point_index, len(points) - 1)]
            anomaly_name = rng.choice(list(PLAUSIBLE_ANOMALIES.keys()))
            if anomaly_name == "progressive_deterioration":
                for offset in range(6):
                    target_index = min(len(points) - 1, point_index + offset * 6)
                    target = points[target_index]
                    for metric, delta in PLAUSIBLE_ANOMALIES[anomaly_name].items():
                        if target.get(metric) is not None:
                            target[metric] = target[metric] + delta * ((offset + 1) / 6.0)
                    target["anomaly_score"] = clamp(target.get("anomaly_score", 0.0) + 0.22 + offset * 0.08, 0.0, 1.0)
                    target.setdefault("anomaly_labels", []).append(anomaly_name)
            else:
                for metric, delta in PLAUSIBLE_ANOMALIES[anomaly_name].items():
                    if point.get(metric) is not None:
                        point[metric] = point[metric] + delta
                point["anomaly_score"] = clamp(point.get("anomaly_score", 0.0) + 0.45, 0.0, 1.0)
                point.setdefault("anomaly_labels", []).append(anomaly_name)
            log_simulation("ANOMALY INJECTED", user_id=profile["user_id"], anomaly=anomaly_name, index=index)

        if profile["synthetic_profile"] in {"shift_worker", "stressed_professional"}:
            failure_start = points[min(len(points) - 1, 36)]["timestamp"] + timedelta(hours=0)
            SensorFailureSimulator.apply(points, ["hrv", "spo2"], failure_start, duration_hours=3)
