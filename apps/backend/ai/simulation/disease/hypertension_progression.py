from __future__ import annotations


class HypertensionProgression:
    @staticmethod
    def apply(state: dict, profile: dict, stress_load: float, activity_load: float, adherence: float) -> None:
        predisposition = float(profile["disease_risks"].get("hypertension", 0.0))
        state["bp_load"] = max(
            0.0,
            min(1.0, state["bp_load"] + 0.018 * predisposition + stress_load * 0.012 - activity_load * 0.01 - adherence * 0.006),
        )
