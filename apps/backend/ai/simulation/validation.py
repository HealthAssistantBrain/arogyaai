from __future__ import annotations

from typing import Any

from ._shared import PHYSIOLOGICAL_LIMITS, clamp, log_simulation, safe_mean, slope


class MedicalRealismValidator:
    @staticmethod
    def validate(points: list[dict[str, Any]]) -> dict[str, Any]:
        impossible: list[dict[str, Any]] = []
        continuity_violations = 0
        correlation_score = 1.0

        for index, point in enumerate(points):
            for metric, limits in PHYSIOLOGICAL_LIMITS.items():
                value = point.get(metric)
                if value is None:
                    continue
                if not (limits[0] <= float(value) <= limits[1]):
                    impossible.append({"index": index, "metric": metric, "value": value})
            if index > 0 and point.get("heart_rate") is not None and points[index - 1].get("heart_rate") is not None:
                if abs(float(point["heart_rate"]) - float(points[index - 1]["heart_rate"])) > 42 and point.get("anomaly_score", 0.0) < 0.4:
                    continuity_violations += 1

        sleep = [float(point.get("sleep_hours", 0.0) or 0.0) for point in points if point.get("sleep_hours", 0.0) > 0]
        stress = [float(point.get("stress_index", 0.0) or 0.0) for point in points]
        hrv = [float(point.get("hrv", 0.0) or 0.0) for point in points]
        if sleep and stress and hrv:
            if slope(stress[-48:]) > 0 and slope(hrv[-48:]) > 0:
                correlation_score -= 0.25
            if safe_mean(sleep[-7:]) < 6.0 and safe_mean(hrv[-48:]) > safe_mean(hrv[:48] or hrv[-48:]):
                correlation_score -= 0.15

        realism_score = clamp(1.0 - continuity_violations * 0.03 - len(impossible) * 0.04 - (1.0 - correlation_score), 0.0, 1.0)
        payload = {
            "physiological_sanity": len(impossible) == 0,
            "impossible_values": impossible,
            "temporal_continuity_violations": continuity_violations,
            "correlation_validation": round(correlation_score, 4),
            "anomaly_realism": round(safe_mean([point.get("anomaly_score", 0.0) for point in points]), 4),
            "medical_realism_score": round(realism_score, 4),
        }
        log_simulation("PHYSIOLOGY VALIDATED", realism=payload["medical_realism_score"], issues=len(impossible))
        return payload
