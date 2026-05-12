from __future__ import annotations

from ..utils import safe_dict, safe_list, safe_text


class FatigueAgent:
    @staticmethod
    def evaluate(monitoring_state: dict, deterioration_projection: dict) -> dict:
        signals = safe_list(safe_dict(monitoring_state).get("signals"))
        recovery = next((safe_dict(item) for item in signals if safe_text(safe_dict(item).get("domain")) == "recovery"), {})
        stress = next((safe_dict(item) for item in signals if safe_text(safe_dict(item).get("domain")) == "stress"), {})
        fatigue_risk = max(float(recovery.get("risk_score") or 0.0), float(stress.get("risk_score") or 0.0) * 0.9)
        return {
            "fatigue_risk": round(fatigue_risk, 4),
            "summary": (
                "Fatigue risk is building from the combination of recovery softness and sustained strain."
                if fatigue_risk >= 55.0
                else safe_text(safe_dict(deterioration_projection).get("summary"))
            ),
        }
