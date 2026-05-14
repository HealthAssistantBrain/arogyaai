from __future__ import annotations


class RecoveryEngine:
    @staticmethod
    def apply(state: dict, profile: dict, sleep_target: float, adherence: float, activity_load: float) -> None:
        capacity = float(profile["recovery_capacity"])
        restoration = max(0.0, min(1.0, (sleep_target / 8.0) * 0.45 + adherence * 0.3 + activity_load * 0.15 + capacity * 0.25))
        state["recovery_balance"] = max(0.0, min(1.0, state["recovery_balance"] * 0.76 + restoration * 0.24 - state["fatigue_load"] * 0.04))
