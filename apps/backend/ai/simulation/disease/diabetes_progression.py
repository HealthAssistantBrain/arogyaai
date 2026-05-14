from __future__ import annotations


class DiabetesProgression:
    @staticmethod
    def apply(state: dict, profile: dict, sleep_debt: float, stress_load: float, adherence: float, activity_load: float) -> None:
        predisposition = float(profile["disease_risks"].get("diabetes", 0.0))
        state["metabolic_load"] = max(
            0.0,
            min(
                1.0,
                state["metabolic_load"] + 0.016 * predisposition + sleep_debt * 0.01 + stress_load * 0.008 - adherence * 0.008 - activity_load * 0.012,
            ),
        )
