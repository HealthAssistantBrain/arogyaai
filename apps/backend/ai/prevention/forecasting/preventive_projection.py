from __future__ import annotations

from ..utils import clamp, safe_dict, safe_list


class PreventiveProjection:
    @staticmethod
    def project(monitoring_state: dict, intervention_plan: dict, adherence: dict) -> dict:
        current_risk = float(monitoring_state.get("overall_risk") or 0.0)
        priorities = safe_list(safe_dict(intervention_plan).get("priorities"))
        adherence_score = float(safe_dict(adherence).get("adherence_score") or 0.6)
        expected_impact = sum(float(safe_dict(item).get("expected_impact") or 0.0) for item in priorities[:3])
        stabilized_risk = clamp(current_risk - expected_impact * adherence_score)
        optimistic_risk = clamp(stabilized_risk - expected_impact * 0.35)
        summary = (
            "If the top preventive actions are followed consistently, the current trend has a realistic chance of stabilizing."
            if stabilized_risk < current_risk
            else "Preventive actions may soften the trend, but limited adherence makes the improvement window narrower."
        )
        return {
            "summary": summary,
            "stabilization_probability": round(clamp(100.0 - stabilized_risk) / 100.0, 4),
            "expected_risk_reduction": round(clamp(current_risk - stabilized_risk), 4),
            "best_case_risk": round(optimistic_risk, 4),
            "stabilized_risk": round(stabilized_risk, 4),
        }
