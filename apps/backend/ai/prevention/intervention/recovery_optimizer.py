from __future__ import annotations

from ..utils import safe_dict


class RecoveryOptimizer:
    @staticmethod
    def optimize(monitoring_state: dict, habits: dict) -> dict:
        overall_risk = float(safe_dict(monitoring_state).get("overall_risk") or 0.0)
        drift_score = float(safe_dict(habits).get("drift_score") or 0.0)
        load_adjustment = "hold_steady"
        if overall_risk >= 75.0 or drift_score >= 60.0:
            load_adjustment = "reduce_strain"
        elif overall_risk >= 45.0:
            load_adjustment = "protect_recovery"

        return {
            "load_adjustment": load_adjustment,
            "sleep_focus": "high" if overall_risk >= 55.0 else "moderate",
            "review_window_hours": 12 if overall_risk >= 75.0 else 24 if overall_risk >= 45.0 else 48,
            "summary": (
                "Recovery optimization should take precedence over further strain."
                if load_adjustment == "reduce_strain"
                else "A recovery-protective routine is appropriate while the signal remains watchful."
            ),
        }
