from __future__ import annotations


class CardiovascularRiskProgression:
    @staticmethod
    def apply(state: dict, profile: dict, bp_load: float, stress_load: float, activity_load: float, sleep_debt: float) -> None:
        predisposition = float(profile["disease_risks"].get("cardiovascular", 0.0))
        state["cardio_load"] = max(
            0.0,
            min(1.0, state["cardio_load"] + bp_load * 0.018 + stress_load * 0.012 + sleep_debt * 0.01 + predisposition * 0.01 - activity_load * 0.01),
        )
