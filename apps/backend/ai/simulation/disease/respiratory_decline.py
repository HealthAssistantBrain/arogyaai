from __future__ import annotations


class RespiratoryDecline:
    @staticmethod
    def apply(state: dict, profile: dict, illness_burden: float, stress_load: float) -> None:
        predisposition = float(profile["disease_risks"].get("respiratory", 0.0))
        state["respiratory_load"] = max(
            0.0,
            min(1.0, state["respiratory_load"] + illness_burden * 0.03 + stress_load * 0.006 + predisposition * 0.012),
        )
