from __future__ import annotations


class FatigueProgression:
    @staticmethod
    def apply(state: dict, profile: dict, sleep_debt: float, stress_load: float, illness_burden: float) -> None:
        predisposition = float(profile["disease_risks"].get("fatigue", 0.0))
        state["fatigue_load"] = max(
            0.0,
            min(1.0, state["fatigue_load"] + sleep_debt * 0.025 + stress_load * 0.012 + illness_burden * 0.03 + predisposition * 0.01),
        )
