from __future__ import annotations

from ..utils import clamp, priority_from_score, safe_dict, safe_list


class InterventionImpactEstimator:
    @staticmethod
    def estimate(signals: list[dict], adherence: dict, habits: dict) -> dict[str, dict]:
        adherence_score = float(safe_dict(adherence).get("adherence_score") or 0.6)
        drift_score = float(safe_dict(habits).get("drift_score") or 0.0)
        estimates: dict[str, dict] = {}

        for item in safe_list(signals):
            signal = safe_dict(item)
            domain = str(signal.get("domain") or "general")
            risk_score = float(signal.get("risk_score") or 0.0)
            persistence = float(signal.get("persistence_days") or 0.0)
            acceleration = float(signal.get("acceleration") or 0.0)
            base_impact = clamp(risk_score * 0.32 + persistence * 4.0 + acceleration * 25.0 - drift_score * 0.08)
            expected_impact = clamp(base_impact * (0.65 + adherence_score * 0.35))
            estimates[domain] = {
                "expected_impact": round(expected_impact, 4),
                "recovery_probability": round(clamp(100.0 - risk_score + expected_impact) / 100.0, 4),
                "priority": priority_from_score(expected_impact),
            }
        return estimates
