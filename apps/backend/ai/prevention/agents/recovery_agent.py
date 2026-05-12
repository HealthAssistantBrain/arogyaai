from __future__ import annotations

from ..utils import safe_dict, safe_list, safe_text


class RecoveryAgent:
    @staticmethod
    def evaluate(monitoring_state: dict, behavior_analysis: dict) -> dict:
        recovery_signal = next(
            (safe_dict(item) for item in safe_list(safe_dict(monitoring_state).get("signals")) if safe_text(safe_dict(item).get("domain")) == "recovery"),
            {},
        )
        return {
            "instability": float(recovery_signal.get("risk_score") or 0.0),
            "summary": safe_text(recovery_signal.get("summary") or safe_dict(behavior_analysis).get("summary")),
            "contributors": safe_list(safe_dict(behavior_analysis).get("contributors"))[:3],
        }
